"""Write the card-sized copy of every photo stored before thumbnails existed.

New uploads get their thumbnail as they are stored; this covers what was
already on the disk. It runs from the container's start command, after the
seed, so it reaches the volume the photos are actually on (see the deploy
notes in ``AGENTS.md``), and it is idempotent: a photo that already has its
thumbnail is skipped, so every boot after the first does almost nothing.

It never fails a deploy. A photo it cannot read is logged and left alone --
its card simply keeps showing the full image, exactly as before.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import session_scope
from app.models.business import Business, BusinessItem
from app.models.enums import ImageKind
from app.models.talent import TalentProfile
from app.services.images import ImageService
from app.storage.factory import get_storage

logger = logging.getLogger("scripts.backfill_thumbnails")


def backfill() -> tuple[int, int]:
    """(written, failed)."""
    settings = get_settings()
    images = ImageService(get_storage(), settings)
    written = failed = 0

    with session_scope() as db:
        keys: list[tuple[str | None, ImageKind]] = []
        for logo, cover in db.execute(
            select(Business.logo_storage_key, Business.cover_storage_key)
        ):
            keys += [(logo, ImageKind.LOGO), (cover, ImageKind.COVER)]
        for (key,) in db.execute(select(BusinessItem.image_storage_key)):
            keys.append((key, ImageKind.ITEM))
        # A talent profile's photo is stored as a LOGO: see talent_images.
        for (key,) in db.execute(select(TalentProfile.photo_storage_key)):
            keys.append((key, ImageKind.LOGO))

    for key, kind in keys:
        try:
            if images.ensure_thumbnail(key, kind):
                written += 1
        except Exception:  # one bad file must not stop the rest
            failed += 1
            logger.exception("Could not write a thumbnail", extra={"storage_key": key})
    return written, failed


def main() -> int:
    configure_logging(get_settings().log_level, json_output=False)
    written, failed = backfill()
    logger.info("Thumbnails backfilled", extra={"written": written, "failed": failed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
