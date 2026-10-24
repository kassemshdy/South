"""An archive of everything users save, posted to a Telegram chat.

The owners asked for it: every application with the applicant's details and
ID scan, every order, product, listing edit, review and request, as a running
record in a Telegram group they control. Inert without both
``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID``, like every other optional
integration here, so local development and the test suite never send.

**This is a deliberate disclosure, decided by the owners.** It copies
identity fields, customers' phone numbers and private documents (ID scans,
CVs, business papers) to Telegram's servers and to every device in that
chat. Two consequences they accepted:

- Deleting an account here deletes its rows and files (``AccountDeletionService``)
  but not the messages already posted. The chat is outside this application.
- Anyone added to the chat reads every ID scan ever posted to it. Who is in
  the group is the access control.

How it works: SQLAlchemy session hooks rather than a call in every route, so
a new feature is archived without anyone remembering to wire it in.

- ``get_db`` marks a request's session as archivable; scripts, migrations,
  the seeder and backups use other sessions and are never archived.
- The auth dependency records who the caller is on the session. A commit by
  an administrator is skipped -- the archive is of what *users* save.
- ``after_flush`` captures what changed while the values are still known;
  ``after_commit`` hands it to a worker thread; a rollback discards it. So
  only what actually reached the database is archived, and the request never
  waits on Telegram.
- The worker looks up context (which shop, which account), reads attached
  files from storage, and sends at a pace Telegram accepts, honouring its
  ``retry_after`` when it asks to slow down.

Never archived, whatever the model: password hashes and session counters
(``SKIPPED_COLUMNS``).
"""

from __future__ import annotations

import datetime as dt
import enum
import json
import logging
import queue
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.database.session import ARCHIVE_SESSION_FLAG as SESSION_ARCHIVE_FLAG

logger = logging.getLogger(__name__)
# httpx logs every request URL at INFO, and a bot API URL carries the token.
logging.getLogger("httpx").setLevel(logging.WARNING)

SESSION_ACTOR = "telegram_actor"
_PENDING = "telegram_pending"

# What users save. Admin-only tables (moderation, pages, articles, settings,
# taxonomy) and bookkeeping (rate limits, view counters) are left out.
ARCHIVED_TABLES = frozenset(
    {
        "users",
        "owner_verification_documents",
        "businesses",
        "business_images",
        "business_documents",
        "business_social_links",
        "business_items",
        "business_item_images",
        "talent_profiles",
        "talent_languages",
        "talent_skills",
        "talent_social_links",
        "talent_images",
        "orders",
        "order_lines",
        "service_requests",
        "testimonials",
        "feedback_tickets",
        "feedback_comments",
        "feedback_attachments",
        "discarded_applications",
        "partner_requests",
    }
)

SKIPPED_COLUMNS = frozenset(
    {
        "password_hash",
        "token_version",
        "must_change_password",
        "last_login_at",
        "created_at",
        "updated_at",
        "search_vector",
    }
)

# Columns holding a storage key: the file behind it is attached.
FILE_COLUMNS = frozenset(
    {
        "storage_key",
        "logo_storage_key",
        "cover_storage_key",
        "image_storage_key",
        "photo_storage_key",
    }
)

MAX_VALUE = 600
MAX_MESSAGE = 3900  # Telegram's limit is 4096 characters.
MAX_FILE_BYTES = 45 * 1024 * 1024  # sendDocument accepts up to 50 MB.
SEND_INTERVAL_SECONDS = 3.1  # About 20 messages a minute, a group's limit.
QUEUE_SIZE = 2000


@dataclass
class Change:
    action: str  # created / updated / deleted
    table: str
    row_id: str | None
    fields: dict[str, str] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)


@dataclass
class Batch:
    """One commit's worth of changes, posted as one message."""

    actor: str
    changes: list[Change]


def _format(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        value = value.value
    elif isinstance(value, dt.date):
        value = value.isoformat()
    elif isinstance(value, Decimal | uuid.UUID):
        value = str(value)
    elif isinstance(value, dict | list):
        value = json.dumps(value, ensure_ascii=False, default=str)
    text = str(value).strip()
    if not text:
        return None
    return text if len(text) <= MAX_VALUE else text[:MAX_VALUE] + "…"


def capture(obj: Any, action: str) -> Change | None:
    table = getattr(obj, "__tablename__", None)
    if table not in ARCHIVED_TABLES:
        return None
    state = inspect(obj)
    change = Change(action=action, table=table, row_id=_format(getattr(obj, "id", None)))
    for attr in state.mapper.column_attrs:
        name = attr.key
        if name in SKIPPED_COLUMNS or name == "id":
            continue
        if action == "updated" and not state.attrs[name].history.has_changes():
            continue
        value = getattr(obj, name, None)
        if name in FILE_COLUMNS:
            if value and action != "deleted":
                change.files.append(str(value))
            continue
        if action == "deleted" and name not in ("title", "name", "full_name", "phone_number"):
            continue
        formatted = _format(value)
        if formatted is not None:
            change.fields[name] = formatted
    if action == "updated" and not change.fields and not change.files:
        return None
    return change


def describe_actor(user: Any) -> str:
    """Who is saving, as the message's first line. Set by the auth dependency."""
    parts = [getattr(user, "full_name", None) or getattr(user, "display_name", None)]
    parts.append(getattr(user, "phone_number", None) or getattr(user, "email", None))
    return " · ".join(str(p) for p in parts if p) or str(getattr(user, "id", ""))


# --- Session hooks -----------------------------------------------------------


def _after_flush(session: Session, _context: Any) -> None:
    if _archive is None or not session.info.get(SESSION_ARCHIVE_FLAG):
        return
    actor = session.info.get(SESSION_ACTOR)
    if actor is not None and actor[0] == "ADMIN":
        return
    pending: list[Change] = session.info.setdefault(_PENDING, [])
    for objects, action in (
        (session.new, "created"),
        (session.dirty, "updated"),
        (session.deleted, "deleted"),
    ):
        for obj in objects:
            change = capture(obj, action)
            if change is not None:
                pending.append(change)


def _after_commit(session: Session) -> None:
    pending = session.info.pop(_PENDING, None)
    if not pending or _archive is None:
        return
    actor = session.info.get(SESSION_ACTOR)
    _archive.submit(Batch(actor=actor[1] if actor else "visitor", changes=pending))


def _after_rollback(session: Session) -> None:
    session.info.pop(_PENDING, None)


# --- Sending -----------------------------------------------------------------

Lookup = Callable[[Change], list[str]]


class TelegramArchive:
    def __init__(
        self,
        *,
        token: str,
        chat_id: str,
        read_file: Callable[[str], bytes],
        lookup: Lookup | None = None,
        client: httpx.Client | None = None,
        interval: float = SEND_INTERVAL_SECONDS,
        autostart: bool = True,
        send_files: bool = False,
    ) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._chat_id = chat_id
        self._read_file = read_file
        # Text only unless TELEGRAM_SEND_FILES is on: the owners started with
        # details alone and may add the photos and ID scans later.
        self._send_files = send_files
        self._lookup = lookup
        self._client = client or httpx.Client(timeout=60)
        self._interval = interval
        # Off in tests, which call ``drain`` to send on their own thread.
        self._autostart = autostart
        self._queue: queue.Queue[Batch] = queue.Queue(maxsize=QUEUE_SIZE)
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def submit(self, batch: Batch) -> None:
        try:
            self._queue.put_nowait(batch)
        except queue.Full:
            logger.warning("telegram archive queue full; a batch was dropped")
            return
        if not self._autostart:
            return
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="telegram-archive", daemon=True
                )
                self._thread.start()

    def drain(self) -> None:
        """Send everything queued, on the calling thread. For tests."""
        while not self._queue.empty():
            self.send(self._queue.get_nowait())

    def _run(self) -> None:
        while True:
            batch = self._queue.get()
            try:
                self.send(batch)
            except Exception:  # never let one bad batch stop the archive
                logger.exception("telegram archive batch failed")

    def render(self, batch: Batch) -> str:
        lines = [f"👤 {batch.actor}"]
        for change in batch.changes:
            icon = {"created": "🆕", "updated": "✏️", "deleted": "🗑"}[change.action]
            lines.append("")
            lines.append(f"{icon} {change.table} {change.action}")
            if self._lookup is not None:
                lines.extend(self._lookup(change))
            lines.extend(f"{name}: {value}" for name, value in change.fields.items())
            if change.files and not self._send_files:
                lines.append(f"📎 {len(change.files)}")
        return "\n".join(lines)

    def send(self, batch: Batch) -> None:
        text = self.render(batch)
        for start in range(0, len(text), MAX_MESSAGE):
            chunk = text[start : start + MAX_MESSAGE]
            self._post("sendMessage", data={"chat_id": self._chat_id, "text": chunk})
        if not self._send_files:
            return
        for change in batch.changes:
            for key in change.files:
                try:
                    data = self._read_file(key)
                except Exception:
                    logger.warning("telegram archive could not read %s", key)
                    continue
                if len(data) > MAX_FILE_BYTES:
                    continue
                self._post(
                    "sendDocument",
                    data={
                        "chat_id": self._chat_id,
                        "caption": f"{change.table} · {batch.actor}"[:1000],
                    },
                    files={"document": (key.rsplit("/", 1)[-1], data)},
                )

    def _post(
        self, method: str, *, data: dict[str, str], files: dict[str, Any] | None = None
    ) -> None:
        for _attempt in range(5):
            response = self._client.post(f"{self._base}/{method}", data=data, files=files)
            if response.status_code == 429:
                retry = response.json().get("parameters", {}).get("retry_after", 5)
                time.sleep(float(retry) + 0.5)
                continue
            if response.status_code >= 400:
                # The body never contains the token; the URL would, so it is
                # not logged.
                logger.warning("telegram %s failed: %s", method, response.status_code)
            time.sleep(self._interval)
            return


def context_lookup(session_factory: sessionmaker[Session]) -> Lookup:
    """Which shop or account a row belongs to, read in the worker so the
    request never pays for it."""
    from app.models.business import Business, BusinessItem
    from app.models.talent import TalentProfile
    from app.models.user import User

    def lookup(change: Change) -> list[str]:
        lines: list[str] = []
        try:
            with session_factory() as db:
                business_id = change.fields.get("business_id")
                if change.table == "businesses":
                    business_id = change.row_id
                item_id = change.fields.get("item_id")
                if item_id and change.table == "business_item_images":
                    item = db.get(BusinessItem, uuid.UUID(item_id))
                    if item is not None:
                        lines.append(f"📦 {item.title}")
                        business_id = str(item.business_id)
                if business_id:
                    business = db.get(Business, uuid.UUID(business_id))
                    if business is not None:
                        lines.append(f"🏪 {business.name} ({business.slug})")
                talent_id = change.fields.get("profile_id") or change.fields.get(
                    "talent_profile_id"
                )
                if change.table == "talent_profiles":
                    talent_id = change.row_id
                if talent_id:
                    talent = db.get(TalentProfile, uuid.UUID(talent_id))
                    if talent is not None:
                        lines.append(f"🧑‍🔧 {talent.display_name}")
                user_id = change.fields.get("owner_id") or change.fields.get("user_id")
                if user_id:
                    user = db.get(User, uuid.UUID(user_id))
                    if user is not None:
                        lines.append(f"🙍 {describe_actor(user)}")
        except Exception:
            logger.warning("telegram archive context lookup failed", exc_info=True)
        return lines

    return lookup


_archive: TelegramArchive | None = None
_installed: set[int] = set()


def install_hooks(session_factory: sessionmaker[Session]) -> None:
    """Register the session hooks once per session factory."""
    if id(session_factory) in _installed:
        return
    event.listen(session_factory, "after_flush", _after_flush)
    event.listen(session_factory, "after_commit", _after_commit)
    event.listen(session_factory, "after_rollback", _after_rollback)
    _installed.add(id(session_factory))


def set_archive(archive: TelegramArchive | None) -> None:
    global _archive
    _archive = archive


def configure(settings: Settings, session_factory: sessionmaker[Session]) -> None:
    """Start archiving if, and only if, both variables are set."""
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        return
    from app.storage.factory import get_storage

    install_hooks(session_factory)
    set_archive(
        TelegramArchive(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            read_file=lambda key: get_storage().read(key),
            lookup=context_lookup(session_factory),
            send_files=settings.telegram_send_files,
        )
    )
