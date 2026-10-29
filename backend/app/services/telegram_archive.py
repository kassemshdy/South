"""An archive of everything users save, posted to a Telegram chat.

The owners asked for it: a message for every application, order, product,
listing edit, review and request, in a Telegram chat they control. Each
message is three lines -- who saved it, their phone, and a link to the admin
screen where it is reviewed (the owners' decision, 26 Oct 2026, after the
full field dump proved too much to read) -- plus, for a business, its logo
as the photo and its Instagram and Facebook pages. Only what is created is
posted; edits and deletions are not. Inert without both
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
import html
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
from app.core.i18n import translate
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
        "contact_messages",
        "story_images",
        "workshop_registrations",
        "job_applications",
        "job_openings",
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
        "id_document_storage_key",
    }
)

#: Bot API ``link_preview_options``, form-encoded as JSON.
NO_LINK_PREVIEW = '{"is_disabled": true}'

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
    past: bool = False  # sent by the backfill, not as it happened


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
        own = change.table in ("partner_requests", "contact_messages")
        names = NAME_COLUMNS + (("name",) if own else ())
        phones = PHONE_COLUMNS + (("phone", "email") if own else ())
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
    if table == "contact_messages":
        return "/admin/contact-messages"
    if table.startswith("feedback_"):
        return "/admin/feedback"
    if table == "discarded_applications":
        return "/admin/applications"
    if table == "story_images":
        return "/admin/stories"
    if table == "workshop_registrations":
        return "/admin/workshops"
    if table in ("job_applications", "job_openings"):
        return "/admin/job-openings"
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
    "/admin/contact-messages",
    "/admin/feedback",
    "/admin/applications",
    "/admin/stories",
    "/admin/job-openings",
    "/admin/workshops",
    "/admin/businesses/",
    "/admin/talent/",
    "/admin/users/",
)


# What the message is about, read from the rows the commit created, most
# specific first: an application's account belongs to its shop.
_KINDS = (
    (("orders", "order_lines"), "order"),
    (("testimonials",), "review"),
    (("business_items",), "product"),
    (("business_item_images",), "product_media"),
    (("businesses",), "shop"),
    (("business_images", "business_documents", "business_social_links"), "shop_media"),
    (("service_requests",), "service_request"),
    (("talent_profiles",), "service"),
    (
        ("talent_languages", "talent_skills", "talent_social_links", "talent_images"),
        "service_media",
    ),
    (("partner_requests",), "partner"),
    (("contact_messages",), "contact"),
    (("feedback_tickets", "feedback_comments", "feedback_attachments"), "ticket"),
    (("discarded_applications",), "set_aside"),
    (("story_images",), "story"),
    (("workshop_registrations",), "workshop_signup"),
    (("job_applications",), "job_application"),
    (("job_openings",), "job_offer"),
    (("users", "owner_verification_documents"), "account"),
)

MAX_DETAIL = 300

#: The lines whose value is in bold: the shop, the product, a review's text.
BOLD_LABELS = frozenset({"shop", "product", "text"})


def _html(value: str) -> str:
    """Escaped for Telegram's HTML mode: only these three characters matter."""
    return html.escape(value, quote=False)


def _kind(changes: list[Change]) -> str:
    created = {change.table for change in changes if change.action == "created"}
    return next((kind for tables, kind in _KINDS if created.intersection(tables)), "other")


def _t(key: str) -> str:
    # The chat is read in Arabic, whatever locale the request that saved
    # the row was in.
    return translate(key, locale="ar")


def _first(changes: list[Change], table: str, *names: str) -> str | None:
    for change in changes:
        if change.table == table:
            for name in names:
                value = change.fields.get(name)
                if value:
                    return value if len(value) <= MAX_DETAIL else value[:MAX_DETAIL] + "…"
    return None


def _details(kind: str, changes: list[Change]) -> list[tuple[str, str | None]]:
    """The few fields that say what was added, by label key."""
    if kind == "product":
        price = _first(changes, "business_items", "price")
        currency = _first(changes, "business_items", "currency")
        return [
            ("product", _first(changes, "business_items", "title")),
            ("price", f"{price} {currency or ''}".strip() if price else None),
        ]
    if kind == "order":
        items = [
            f"{c.fields.get('title', '')} × {c.fields.get('quantity', '1')}"
            for c in changes
            if c.table == "order_lines"
        ]
        return [
            ("items", " | ".join(items) or None),
            ("note", _first(changes, "orders", "note")),
        ]
    if kind == "review":
        rating = _first(changes, "testimonials", "rating")
        return [
            ("rating", f"{rating}/5" if rating else None),
            ("text", _first(changes, "testimonials", "body")),
        ]
    if kind == "shop":
        return [("description", _first(changes, "businesses", "short_description"))]
    if kind == "service":
        return [("service", _first(changes, "talent_profiles", "display_name"))]
    if kind == "service_request":
        return [("details", _first(changes, "service_requests", "details"))]
    if kind == "partner":
        return [
            ("occupation", _first(changes, "partner_requests", "occupation")),
            ("residence", _first(changes, "partner_requests", "residence")),
            ("offer", _first(changes, "partner_requests", "offer")),
        ]
    if kind == "contact":
        topic = _first(changes, "contact_messages", "topic")
        return [
            ("topic", _t(f"contact.topic.{topic}") if topic else None),
            ("text", _first(changes, "contact_messages", "message")),
            ("page", _first(changes, "contact_messages", "page_path")),
        ]
    if kind == "story":
        return [("text", _first(changes, "story_images", "caption"))]
    if kind == "ticket":
        return [
            ("title", _first(changes, "feedback_tickets", "title")),
            (
                "text",
                _first(changes, "feedback_tickets", "description")
                or _first(changes, "feedback_comments", "body"),
            ),
        ]
    return []


def _business_id(
    changes: list[Change], business_of_item: Callable[[str], str | None]
) -> str | None:
    for change in changes:
        if change.table == "businesses":
            return change.row_id
        if "business_id" in change.refs:
            return change.refs["business_id"]
    for change in changes:
        if "item_id" in change.refs:
            return business_of_item(change.refs["item_id"])
    return None


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
    # Only a commit that adds something is posted (an application, shop,
    # product, order, review), not an edit or a deletion -- the owners'
    # decision, 26 Oct 2026. The edits in the same commit stay: an
    # application fills in the new account's name after creating it.
    if not any(change.action == "created" for change in pending):
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
    """What the message shows of the business a save belongs to: its name,
    category and town, its logo (sent as the photo), and its Instagram and
    Facebook pages."""

    name: str | None = None
    category: str | None = None
    town: str | None = None
    logo_key: str | None = None
    instagram: str | None = None
    facebook: str | None = None


ShopLookup = Callable[[str], Shop | None]

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # sendPhoto's limit.


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
        """What was added, by whom, with its key details and a review link;
        a shop's logo is the photo. Labelled lines in Arabic, from the
        catalog, rather than icons -- the owners' request, 27 Oct 2026. Not
        every field: the full dump was too much to read, and the rest is on
        the site behind the administrator's sign-in.

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
        business_id = _business_id(batch.changes, lookup)
        shop = self._shop(business_id) if business_id and self._shop else None

        kind = _kind(batch.changes)
        title = _t(f"telegram.kind.{kind}")
        if batch.past:
            title = f"{title} ({_t('telegram.past')})"
        rows: list[tuple[str, str | None]] = [("name", name), ("phone", phone)]
        if shop is not None:
            place = " · ".join(p for p in (shop.category, shop.town) if p) or None
            rows += [("shop", shop.name), ("category", place)]
        rows += _details(kind, batch.changes)
        if shop is not None:
            rows += [("instagram", shop.instagram), ("facebook", shop.facebook)]
        if path:
            rows.append(("link", f"{self._base_url}{path}"))
        # Sent as HTML: the title, the shop, the product and a review's text
        # in bold (the owners' request, 28 Oct 2026), and everything else --
        # much of it typed by visitors -- escaped so it cannot add markup.
        lines = [f"<b>{_html(title)}</b>"] + [
            f"{_html(_t(f'telegram.label.{label}'))}: "
            + (f"<b>{_html(value)}</b>" if label in BOLD_LABELS else _html(value))
            for label, value in rows
            if value
        ]
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
                data={"chat_id": self._chat_id, "caption": message.text, "parse_mode": "HTML"},
                files={"photo": (key.rsplit("/", 1)[-1], logo)},
            )
            return
        self._post(
            "sendMessage",
            data={
                "chat_id": self._chat_id,
                "text": message.text,
                "parse_mode": "HTML",
                # Every message ends with an admin link; Telegram's preview of
                # it is the site's own share card, the same on every message
                # (the owners asked for it gone, 29 Oct 2026).
                "link_preview_options": NO_LINK_PREVIEW,
            },
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
    """A business's name, category, town, logo and social pages."""
    from sqlalchemy import select

    from app.models.business import Business, BusinessSocialLink
    from app.models.enums import SocialPlatform

    def lookup(business_id: str) -> Shop | None:
        try:
            with session_factory() as db:
                business = db.get(Business, uuid.UUID(business_id))
                if business is None:
                    return None
                links = {
                    link.platform: link.url
                    for link in db.execute(
                        select(BusinessSocialLink).where(
                            BusinessSocialLink.business_id == business.id
                        )
                    ).scalars()
                }
                return Shop(
                    name=business.name,
                    category=business.category.name_ar if business.category else None,
                    town=business.location.name_ar if business.location else None,
                    logo_key=business.logo_storage_key,
                    instagram=links.get(SocialPlatform.INSTAGRAM),
                    facebook=links.get(SocialPlatform.FACEBOOK),
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
