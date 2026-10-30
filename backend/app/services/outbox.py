"""Pushes to third parties, queued with the edit that caused them.

When a shop with a connected Shopify store saves a product, a row is added
to ``integration_outbox`` *in the same flush* as the product row. Commit
the edit and the push is guaranteed to be attempted; roll it back and
nothing is sent. The worker (:func:`run_worker`, started from the app's
lifespan) drains the table with backoff.

Why a table and not the fire-and-forget thread ``telegram_archive`` uses:
a lost Telegram post costs nothing, a product silently out of step with
the store that sells it costs a sale or a complaint.

Enqueueing is a session hook rather than a call in every service, so every
path that changes a product -- the owner's editor, the image routes, an
administrator's delete -- is covered without anyone remembering to.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.business import Business, BusinessItem, BusinessItemImage
from app.models.integration import IntegrationOutbox

logger = logging.getLogger(__name__)

ITEM_UPSERT = "shopify.item.upsert"
ITEM_DELETE = "shopify.item.delete"

#: Attempts before an entry is given up on; the error stays on the row and
#: on the connection, for the owner's dashboard.
MAX_ATTEMPTS = 8
BATCH_SIZE = 20

_installed: set[int] = set()


def backoff(attempts: int) -> timedelta:
    """30s, 1m, 2m, 4m ... capped at an hour."""
    return timedelta(seconds=min(30 * 2 ** max(attempts - 1, 0), 3600))


def enqueue(
    db: Session, kind: str, business_id: uuid.UUID, payload: dict[str, Any]
) -> IntegrationOutbox:
    entry = IntegrationOutbox(
        kind=kind,
        business_id=business_id,
        payload=payload,
        attempts=0,
        next_attempt_at=datetime.now(UTC),
    )
    db.add(entry)
    return entry


def enqueue_full_sync(db: Session, business: Business) -> int:
    """Every product of the shop, e.g. right after it connects its store."""
    items = db.scalars(select(BusinessItem.id).where(BusinessItem.business_id == business.id))
    count = 0
    for item_id in items:
        enqueue(db, ITEM_UPSERT, business.id, {"item_id": str(item_id)})
        count += 1
    return count


def _connected(business: Business | None) -> bool:
    connection = business.shopify_connection if business is not None else None
    return connection is not None and connection.is_live


def _item_of(session: Session, image: BusinessItemImage) -> BusinessItem | None:
    if image.item is not None:
        return image.item
    return session.get(BusinessItem, image.item_id) if image.item_id else None


def _before_flush(session: Session, _context: object, _instances: object) -> None:
    upserts: dict[uuid.UUID, uuid.UUID] = {}
    with session.no_autoflush:
        for obj in (*session.new, *session.dirty):
            item: BusinessItem | None = None
            if isinstance(obj, BusinessItem):
                item = obj
            elif isinstance(obj, BusinessItemImage):
                item = _item_of(session, obj)
            if item is None or item in session.deleted:
                continue
            if obj in session.dirty and not session.is_modified(obj):
                continue
            if item.id is None:
                # A new item gets its id at flush; give it one now so the
                # outbox row can name it.
                item.id = uuid.uuid4()
            if _connected(item.business):
                upserts[item.id] = item.business_id
        for obj in session.deleted:
            if isinstance(obj, BusinessItemImage):
                parent = _item_of(session, obj)
                if (
                    parent is not None
                    and parent not in session.deleted
                    and _connected(parent.business)
                ):
                    upserts[parent.id] = parent.business_id
            if not isinstance(obj, BusinessItem):
                continue
            # A whole listing going (an account deleted, an administrator's
            # delete) takes its outbox rows with it; the products in the
            # store are the owner's and stay.
            if obj.business in session.deleted:
                continue
            link = obj.shopify_link
            if link is not None and _connected(obj.business):
                enqueue(
                    session,
                    ITEM_DELETE,
                    obj.business_id,
                    {"shopify_product_id": link.shopify_product_id},
                )
    for item_id, business_id in upserts.items():
        enqueue(session, ITEM_UPSERT, business_id, {"item_id": str(item_id)})


def install_hooks(session_factory: sessionmaker[Session]) -> None:
    """Register the hook once per session factory."""
    if id(session_factory) in _installed:
        return
    event.listen(session_factory, "before_flush", _before_flush)
    _installed.add(id(session_factory))


def uninstall_hooks(session_factory: sessionmaker[Session]) -> None:
    if id(session_factory) not in _installed:
        return
    event.remove(session_factory, "before_flush", _before_flush)
    _installed.discard(id(session_factory))


Handler = Callable[[Session, IntegrationOutbox], None]


def drain_once(session_factory: sessionmaker[Session], handlers: dict[str, Handler]) -> int:
    """Send what is due; return how many entries were finished.

    Each entry is handled in its own transaction, so one store that keeps
    failing never holds back another. ``SKIP LOCKED`` lets two API workers
    run this side by side without sending anything twice.
    """
    finished = 0
    now = datetime.now(UTC)
    with session_factory() as db:
        ids = list(
            db.scalars(
                select(IntegrationOutbox.id)
                .where(IntegrationOutbox.done_at.is_(None))
                .where(IntegrationOutbox.next_attempt_at <= now)
                .order_by(IntegrationOutbox.created_at)
                .limit(BATCH_SIZE)
            )
        )
    for entry_id in ids:
        with session_factory() as db:
            entry = db.scalars(
                select(IntegrationOutbox)
                .where(IntegrationOutbox.id == entry_id, IntegrationOutbox.done_at.is_(None))
                .with_for_update(skip_locked=True)
            ).first()
            if entry is None:
                continue
            handler = handlers.get(entry.kind)
            try:
                if handler is None:
                    raise RuntimeError(f"no handler for {entry.kind}")
                handler(db, entry)
            except Exception as exc:
                db.rollback()
                entry = db.get(IntegrationOutbox, entry_id)
                if entry is None:
                    continue
                entry.attempts += 1
                entry.last_error = str(exc)[:2000]
                if entry.attempts >= MAX_ATTEMPTS:
                    entry.done_at = datetime.now(UTC)
                    logger.error(
                        "Integration push given up",
                        extra={"kind": entry.kind, "business_id": str(entry.business_id)},
                    )
                else:
                    entry.next_attempt_at = datetime.now(UTC) + backoff(entry.attempts)
                    logger.warning(
                        "Integration push failed; will retry",
                        extra={"kind": entry.kind, "attempts": entry.attempts},
                    )
                db.commit()
                continue
            entry.done_at = datetime.now(UTC)
            entry.last_error = None
            db.commit()
            finished += 1
    return finished


async def run_worker(
    session_factory: sessionmaker[Session],
    handlers: dict[str, Handler],
    *,
    poll_seconds: int,
) -> None:
    """Drain the outbox forever; a failure is logged and the next pass retries."""
    while True:
        await asyncio.sleep(poll_seconds)
        try:
            await asyncio.to_thread(drain_once, session_factory, handlers)
        except Exception:
            logger.exception("Draining the integration outbox failed")
