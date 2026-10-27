"""Send what already existed before the Telegram archive started.

The archive posts saves as they happen; this posts the history, one
business at a time: the owner's account with their identity and ID scans,
the listing with its papers and photos, its products, reviews and orders,
and the owner's talent profile if they have one.

Run from the API container's start command when ``TELEGRAM_BACKFILL`` is
set, because that is the only place with the database, the stored files and
the bot token together:

- ``1`` (or any number N): the first N businesses not yet sent, oldest first
- a business slug: that business
- ``all``: every business not yet sent

Each business sent is recorded as a ``tgb:<id>`` row in ``site_settings``
(a key the public settings route never reads), so a redeploy with the
variable still set sends nothing twice. Inert without the bot variables.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models.business import Business
from app.models.order import Order
from app.models.site_setting import SiteSetting
from app.models.talent import TalentProfile
from app.models.testimonial import Testimonial
from app.models.verification import OwnerVerificationDocument
from app.services import telegram_archive
from app.services.telegram_archive import Batch, Change, TelegramArchive, person
from app.storage.factory import get_storage

logger = logging.getLogger("telegram_backfill")

MARKER = "tgb:"


def _changes(objects: Iterable[Any]) -> list[Change]:
    found = (telegram_archive.capture(obj, "created") for obj in objects)
    return [change for change in found if change is not None]


def business_batch(db: Session, business: Business) -> Batch:
    owner = business.owner
    objects: list[Any] = [owner]
    objects += db.execute(
        select(OwnerVerificationDocument).where(OwnerVerificationDocument.user_id == owner.id)
    ).scalars()
    objects.append(business)
    objects += business.documents
    objects += business.images
    for item in business.items:
        objects.append(item)
        objects += item.images
    objects += db.execute(
        select(Testimonial).where(Testimonial.business_id == business.id)
    ).scalars()
    for order in db.execute(select(Order).where(Order.business_id == business.id)).scalars():
        objects.append(order)
        objects += order.lines
    talent = db.execute(
        select(TalentProfile).where(TalentProfile.owner_id == owner.id)
    ).scalar_one_or_none()
    if talent is not None:
        objects.append(talent)
        objects += talent.images
    name, phone = person(owner)
    return Batch(name=name, phone=phone, changes=_changes(objects), past=True)


def _targets(db: Session, wanted: str) -> list[Business]:
    sent = {
        key.removeprefix(MARKER)
        for key in db.execute(
            select(SiteSetting.key).where(SiteSetting.key.startswith(MARKER))
        ).scalars()
    }
    if wanted != "all" and not wanted.isdigit():
        business = db.execute(select(Business).where(Business.slug == wanted)).scalar_one_or_none()
        return [business] if business is not None and str(business.id) not in sent else []
    pending = [
        business
        for business in db.execute(select(Business).order_by(Business.created_at)).scalars()
        if str(business.id) not in sent
    ]
    return pending if wanted == "all" else pending[: int(wanted)]


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    wanted = os.environ.get("TELEGRAM_BACKFILL", "").strip()
    if not wanted:
        return 0
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        logger.info("TELEGRAM_BACKFILL is set but the bot variables are not; nothing sent")
        return 0

    archive = TelegramArchive(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        read_file=lambda key: get_storage().read(key),
        lookup=telegram_archive.context_lookup(SessionLocal),
        shop=telegram_archive.shop_lookup(SessionLocal),
        base_url=settings.public_base_url,
        autostart=False,
        send_files=settings.telegram_send_files,
    )
    with SessionLocal() as db:
        targets = _targets(db, wanted)
        logger.info("Telegram backfill: %d business(es) to send", len(targets))
        for business in targets:
            try:
                archive.send(business_batch(db, business))
            except Exception:
                logger.exception("Telegram backfill failed for business %s", business.id)
                continue
            db.add(SiteSetting(key=f"{MARKER}{business.id}", value="sent"))
            db.commit()
            logger.info("Telegram backfill: sent business %s", business.id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

