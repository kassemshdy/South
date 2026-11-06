"""An off-site copy of the bucket -- uploads and database backups -- in another bucket.

The owners' decision (6 Nov 2026): everything janoubona.net keeps in its
Railway bucket is also copied to an Amazon S3 bucket of theirs, so losing
Railway (the bucket, the account, or the project) does not lose the photos,
the private documents or the database backups.

It **only adds**. Each run lists both buckets and uploads the keys the replica
lacks; nothing in the replica is ever overwritten or deleted, and the site's
bucket is only read. So the replica also keeps database backups the site has
since pruned (``db_backup.KEEP``): how long they stay there is the replica
bucket's own lifecycle rule, set in AWS.

The replica holds ID scans, CVs and full database dumps, so it must be a
private bucket ("Block all public access" on). Nothing here can check that.

Inert without ``REPLICA_S3_BUCKET``. Runs once at boot in the background
(``scripts/replicate_media.py``) and then every ``REPLICA_INTERVAL_HOURS``
from the API, one worker at a time.
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from typing import Protocol

from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.storage.s3 import S3Storage

logger = logging.getLogger("app.services.media_replica")

#: ``pg_try_advisory_lock`` key, distinct from the backups' own.
_LOCK_KEY = 7_242_027


class _Source(Protocol):
    def keys(self) -> set[str]: ...
    def read(self, key: str) -> bytes: ...


class _Target(Protocol):
    def keys(self) -> set[str]: ...
    def save(self, *, key: str, data: bytes, content_type: str) -> object: ...


def replica_settings(settings: Settings) -> Settings | None:
    """Settings for the replica bucket, or None when none is configured."""
    if not settings.replica_s3_bucket:
        return None
    return settings.model_copy(
        update={
            "s3_bucket": settings.replica_s3_bucket,
            # None is AWS itself; set only for another S3-compatible store.
            "s3_endpoint_url": settings.replica_s3_endpoint_url,
            "s3_region": settings.replica_s3_region,
            "s3_access_key_id": settings.replica_s3_access_key_id,
            "s3_secret_access_key": settings.replica_s3_secret_access_key,
            "s3_addressing_style": "auto",
            "s3_public_base_url": None,
        }
    )


def replicate(source: _Source, target: _Target) -> tuple[int, int, int]:
    """(copied, already there, failed) over every key of ``source``."""
    present = target.keys()
    copied = already = failed = 0
    for key in sorted(source.keys()):
        if key.endswith("/"):
            continue
        if key in present:
            already += 1
            continue
        try:
            content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
            target.save(key=key, data=source.read(key), content_type=content_type)
            copied += 1
        except Exception:  # one bad file must not stop the rest
            failed += 1
            logger.exception("Could not copy a file to the replica", extra={"storage_key": key})
    return copied, already, failed


def replicate_configured(settings: Settings, storage: object) -> tuple[int, int, int] | None:
    """Copy the site's bucket to the replica; None when there is nothing to do."""
    replica = replica_settings(settings)
    if replica is None or not isinstance(storage, S3Storage):
        return None
    own = (settings.s3_bucket, settings.s3_endpoint_url)
    if (replica.s3_bucket, replica.s3_endpoint_url) == own:
        logger.warning("REPLICA_S3_BUCKET names the site's own bucket; nothing copied")
        return None
    counts = replicate(storage, S3Storage(replica))
    # In the message itself: the deploy log prints it, and it is how the copy
    # is checked -- every file copied or already there, none failed.
    logger.info(
        "Replica %s: %d copied, %d already there, %d failed",
        replica.s3_bucket,
        *counts,
    )
    return counts


def replicate_if_first(settings: Settings, storage: object) -> bool:
    """Replicate unless another worker already is; True when this one did."""
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            if not connection.execute(
                text("select pg_try_advisory_lock(:key)"), {"key": _LOCK_KEY}
            ).scalar():
                return False
            try:
                replicate_configured(settings, storage)
            finally:
                connection.execute(text("select pg_advisory_unlock(:key)"), {"key": _LOCK_KEY})
            return True
    finally:
        engine.dispose()


async def run_periodic(settings: Settings, storage: object, *, interval_hours: int) -> None:
    """Replicate every ``interval_hours`` for as long as the API runs."""
    while True:
        await asyncio.sleep(interval_hours * 3600)
        try:
            await asyncio.to_thread(replicate_if_first, settings, storage)
        except Exception:  # reported, and the next interval tries again
            logger.exception("Scheduled replica copy failed")
