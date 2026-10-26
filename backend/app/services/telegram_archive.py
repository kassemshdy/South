"""An archive of everything users save, posted to a Telegram chat.

The owners asked for it: a message for every application, order, product,
listing edit, review and request, in a Telegram chat they control. Each
message is three lines -- who saved it, their phone, and a link to the admin
screen where it is reviewed (the owners' decision, 26 Oct 2026, after the
full field dump proved too much to read) -- plus, for a business, its logo
as the photo and its Instagram and Facebook pages. Inert without both
``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID``, like every other optional
integration here, so local development and the test suite never send.

**This is a deliberate disclosure, decided by the owners.** It copies names
and phone numbers -- applicants', owners' and customers' -- and, only with
``TELEGRAM_SEND_FILES`` on, private documents (ID scans, CVs, business
papers) to Telegram's servers and to every device in that chat. Two
consequences they accepted:

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
- The worker looks up which shop a product photo belongs to, reads attached
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
MAX_FILE_BYTES = 45 * 1024 * 1024  # sendDocument accepts up to 50 MB.
SEND_INTERVAL_SECONDS = 3.1  # About 20 messages a minute, a group's limit.
QUEUE_SIZE = 2000


# Which listing or account a row belongs to, kept whether or not it changed,
# so the message can link to the screen where it is reviewed.
REF_COLUMNS = frozenset(
    {"business_id", "item_id", "profile_id", "talent_profile_id", "user_id", "owner_id"}
)

# Where a visitor's own name and phone are, when nobody is signed in.
NAME_COLUMNS = ("full_name", "display_name", "customer_name", "author_name")
PHONE_COLUMNS = ("phone_number", "customer_phone", "login_phone")


@dataclass
class Change:
    action: str  # created / updated / deleted
    table: str
    row_id: str | None
    fields: dict[str, str] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)
    refs: dict[str, str] = field(default_factory=dict)


@dataclass
class Batch:
    """One commit's worth of changes, posted as one message: who saved it,
    their phone, and a link to where an administrator reviews it."""

    name: str | None
    phone: str | None
    changes: list[Change]
    icon: str | None = None  # the backfill marks its messages ↩️


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
        value = getattr(obj, name, None)
        if name in REF_COLUMNS and value is not None:
            change.refs[name] = str(value)
        if action == "updated" and not state.attrs[name].history.has_changes():
            continue
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


def person(user: Any) -> tuple[str | None, str | None]:
    """Who is saving: their name and phone. Set by the auth dependency."""
    name = getattr(user, "full_name", None) or getattr(user, "display_name", None)
    phone = getattr(user, "phone_number", None) or getattr(user, "email", None)
    return name, phone


def _who(changes: list[Change]) -> tuple[str | None, str | None]:
    """A visitor's name and phone, from what they submitted."""
    name: str | None = None
    phone: str | None = None
    ordered = sorted(changes, key=lambda change: change.table != "users")
    for change in ordered:
        fields = change.fields
        names = NAME_COLUMNS + (("name",) if change.table == "partner_requests" else ())
        phones = PHONE_COLUMNS + (("phone",) if change.table == "partner_requests" else ())
        name = name or next((fields[key] for key in names if key in fields), None)
        phone = phone or next((fields[key] for key in phones if key in fields), None)
    return name, phone


def admin_path(change: Change, business_of_item: Callable[[str], str | None]) -> str | None:
    """The admin screen where this change is reviewed."""
    table, refs, row_id = change.table, change.refs, change.row_id
    if table in ("orders", "order_lines"):
        return "/admin/orders"
    if table == "testimonials":
        return "/admin/testimonials"
    if table == "partner_requests":
        return "/admin/partners"
    if table.startswith("feedback_"):
        return "/admin/feedback"
    if table == "discarded_applications":
        return "/admin/applications"
    business_id = row_id if table == "businesses" else refs.get("business_id")
    if business_id is None and "item_id" in refs:
        business_id = business_of_item(refs["item_id"])
    if business_id:
        return f"/admin/businesses/{business_id}"
    talent_id = (
        row_id
        if table == "talent_profiles"
        else refs.get("profile_id") or refs.get("talent_profile_id")
    )
    if talent_id:
        return f"/admin/talent/{talent_id}"
    user_id = row_id if table == "users" else refs.get("user_id") or refs.get("owner_id")
    return f"/admin/users/{user_id}" if user_id else None


# Most specific screen first: an application links to its listing, not to
# the account created with it.
_PATH_RANK = (
    "/admin/orders",
    "/admin/testimonials",
    "/admin/partners",
    "/admin/feedback",
    "/admin/applications",
    "/admin/businesses/",
    "/admin/talent/",
    "/admin/users/",
)


# What the message is about, most specific first: a new product's photo is a
# product, an application's account is a shop.
_KIND_ICONS = (
    (("orders", "order_lines"), "🛒"),
    (("testimonials",), "⭐"),
    (("business_items", "business_item_images"), "📦"),
    (("businesses", "business_images", "business_documents", "business_social_links"), "🏪"),
    (("service_requests",), "📩"),
    (
        (
            "talent_profiles",
            "talent_languages",
            "talent_skills",
            "talent_social_links",
            "talent_images",
        ),
        "🧑‍🔧",
    ),
    (("partner_requests",), "🤝"),
    (("feedback_tickets", "feedback_comments", "feedback_attachments"), "🎫"),
    (("discarded_applications",), "📥"),
    (("users", "owner_verification_documents"), "👤"),
)
_ACTION_ICONS = {"created": "🆕", "updated": "✏️", "deleted": "🗑"}


def _icons(changes: list[Change]) -> str:
    """What happened (new, edited, deleted) and what it is about."""
    actions = {change.action for change in changes}
    action = next((a for a in ("created", "deleted", "updated") if a in actions), "updated")
    tables = {change.table for change in changes}
    kind = next((icon for group, icon in _KIND_ICONS if tables.intersection(group)), "")
    return _ACTION_ICONS[action] + kind


def _rank(path: str) -> int:
    return next(i for i, prefix in enumerate(_PATH_RANK) if path.startswith(prefix))


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
    name, phone = (actor[1], actor[2]) if actor else _who(pending)
    _archive.submit(Batch(name=name, phone=phone, changes=pending))


def _after_rollback(session: Session) -> None:
    session.info.pop(_PENDING, None)


# --- Sending -----------------------------------------------------------------

# A product photo knows its product, not its shop: the lookup finds the shop.
Lookup = Callable[[str], str | None]


@dataclass
class Shop:
    """What the message shows of a business besides the link: its logo,
    sent as the photo, and its Instagram and Facebook pages."""

    logo_key: str | None = None
    links: list[str] = field(default_factory=list)


ShopLookup = Callable[[str], Shop | None]

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # sendPhoto's limit.
SHOP_PREFIX = "/admin/businesses/"


@dataclass
class Message:
    text: str
    logo_key: str | None = None


class TelegramArchive:
    def __init__(
        self,
        *,
        token: str,
        chat_id: str,
        read_file: Callable[[str], bytes],
        lookup: Lookup | None = None,
        shop: ShopLookup | None = None,
        base_url: str = "",
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
        self._shop = shop
        self._base_url = base_url.rstrip("/")
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

    def render(self, batch: Batch) -> Message | None:
        """Name, phone and a review link; for a business, also its logo and
        its Instagram and Facebook pages. Nothing else: the owners found the
        full field dump too much to read, and the details are on the site,
        behind the administrator's sign-in.

        None for a commit that names nobody: an application is saved in
        more than one commit, and only the first carries the applicant."""
        name, phone = batch.name, batch.phone
        if not (name or phone):
            name, phone = _who(batch.changes)
        if not (name or phone):
            return None
        lookup = self._lookup or (lambda _item_id: None)
        paths = [p for p in (admin_path(c, lookup) for c in batch.changes) if p]
        path = min(paths, key=_rank) if paths else None
        icon = (batch.icon or "") + _icons(batch.changes)
        lines = [f"{icon} {name or '-'}"]
        if phone:
            lines.append(f"📞 {phone}")
        if path:
            lines.append(f"🔗 {self._base_url}{path}")
        shop = None
        if path and path.startswith(SHOP_PREFIX) and self._shop is not None:
            shop = self._shop(path.removeprefix(SHOP_PREFIX))
        if shop is not None:
            lines.extend(shop.links)
        return Message("\n".join(lines), shop.logo_key if shop else None)

    def send(self, batch: Batch) -> None:
        message = self.render(batch)
        if message is not None:
            self._send_message(message)
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
                        "caption": f"{change.table} · {batch.name or batch.phone or ''}"[:1000],
                    },
                    files={"document": (key.rsplit("/", 1)[-1], data)},
                )

    def _send_message(self, message: Message) -> None:
        """With the shop's logo as the photo when it has one; text alone if
        the logo cannot be read or is too large for a photo."""
        key = message.logo_key
        logo = None
        if key:
            try:
                logo = self._read_file(key)
            except Exception:
                logger.warning("telegram archive could not read %s", key)
        if key and logo is not None and len(logo) <= MAX_PHOTO_BYTES:
            self._post(
                "sendPhoto",
                data={"chat_id": self._chat_id, "caption": message.text},
                files={"photo": (key.rsplit("/", 1)[-1], logo)},
            )
            return
        self._post("sendMessage", data={"chat_id": self._chat_id, "text": message.text})

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
    """Which shop a product belongs to, read in the worker so the request
    never pays for it."""
    from app.models.business import BusinessItem

    def lookup(item_id: str) -> str | None:
        try:
            with session_factory() as db:
                item = db.get(BusinessItem, uuid.UUID(item_id))
                return str(item.business_id) if item is not None else None
        except Exception:
            logger.warning("telegram archive context lookup failed", exc_info=True)
            return None

    return lookup


def shop_lookup(session_factory: sessionmaker[Session]) -> ShopLookup:
    """A business's logo and its Instagram and Facebook pages."""
    from sqlalchemy import select

    from app.models.business import Business, BusinessSocialLink
    from app.models.enums import SocialPlatform

    icons = {SocialPlatform.INSTAGRAM: "📷", SocialPlatform.FACEBOOK: "📘"}

    def lookup(business_id: str) -> Shop | None:
        try:
            with session_factory() as db:
                business = db.get(Business, uuid.UUID(business_id))
                if business is None:
                    return None
                links = db.execute(
                    select(BusinessSocialLink)
                    .where(BusinessSocialLink.business_id == business.id)
                    .where(BusinessSocialLink.platform.in_(list(icons)))
                    .order_by(BusinessSocialLink.platform)
                ).scalars()
                return Shop(
                    logo_key=business.logo_storage_key,
                    links=[f"{icons[link.platform]} {link.url}" for link in links],
                )
        except Exception:
            logger.warning("telegram archive shop lookup failed", exc_info=True)
            return None

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
            shop=shop_lookup(session_factory),
            base_url=settings.public_base_url,
            send_files=settings.telegram_send_files,
        )
    )
