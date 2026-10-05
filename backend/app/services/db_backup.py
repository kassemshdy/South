"""Database backups to the bucket, and the alarm for a database that was wiped.

On October 4, 2026 the production database lived in a container with no disk.
It was redeployed, came back empty, and the API quietly rebuilt an empty
schema on top of it: a month of listings, accounts and articles were gone and
nothing said so for a day. Two things here exist so that cannot happen
silently again:

- **A copy of the database in the bucket**, taken before every deploy changes
  anything and once a day. It is a ``pg_dump`` custom-format archive, so one
  file restores the whole database (see docs/RESTORE.md). The bucket is
  separate from the database service, so losing one does not lose the other.
- **An alarm when the API starts against an empty database while uploads
  exist.** Photos in the bucket and no tables means the data was lost, not
  that the site is new; that is reported to Sentry as fatal and logged loudly,
  before anything is seeded on top.

Backups go to a private folder that ``/media`` refuses, exactly like ID scans
and CVs: a database dump holds every account's identity.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text

from app.storage.base import StorageBackend

logger = logging.getLogger("app.services.db_backup")

#: The bucket folder backups live in. Exported so ``/media`` refuses it.
FOLDER = "backups"
STORAGE_FOLDERS = frozenset({FOLDER})
_PREFIX = f"{FOLDER}/db/"

#: How many copies to keep. One a day plus one per deploy: sixty is roughly a
#: month of both, and a dump of this database is a few megabytes.
KEEP = 60

#: Folders whose files mean the site has been used, so an empty database
#: beside them is a loss rather than a fresh start.
_CONTENT_FOLDERS = ("businesses/", "talent/", "articles/", "pages/")


def libpq_url(database_url: str) -> str:
    """The SQLAlchemy URL as ``pg_dump`` reads it: no ``+driver`` suffix."""
    scheme, rest = database_url.split("://", 1)
    return f"{scheme.split('+', 1)[0]}://{rest}"


def backup_key(now: datetime, reason: str) -> str:
    """Sortable by name: the newest backup is the last key in order."""
    return f"{_PREFIX}{now.strftime('%Y%m%dT%H%M%SZ')}-{reason}.dump"


def database_is_empty(database_url: str) -> bool:
    """True when the schema was never created: no migration has ever run."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return not inspect(connection).has_table("alembic_version")
    finally:
        engine.dispose()


def looks_wiped(stored_keys: Iterable[str]) -> bool:
    """Uploads or earlier backups exist, so this database once held data."""
    return any(key.startswith((*_CONTENT_FOLDERS, _PREFIX)) for key in stored_keys)


Runner = Callable[..., "subprocess.CompletedProcess[bytes]"]


def dump(database_url: str, run: Runner = subprocess.run) -> bytes:
    """The whole database as one ``pg_dump`` custom-format archive."""
    result = run(
        ["pg_dump", "--format=custom", "--no-owner", "--no-acl", libpq_url(database_url)],
        capture_output=True,
        check=True,
        timeout=600,
    )
    return result.stdout


def prune(storage: StorageBackend, keys: Iterable[str], keep: int = KEEP) -> int:
    """Delete all but the newest ``keep`` backups; returns how many went."""
    backups = sorted(key for key in keys if key.startswith(_PREFIX))
    stale = backups[:-keep] if len(backups) > keep else []
    for key in stale:
        storage.delete(key)
    return len(stale)


#: An arbitrary, fixed key for ``pg_try_advisory_lock``: the API runs several
#: workers, and only the one that takes this lock backs up.
_LOCK_KEY = 7_242_026


def back_up_if_first(database_url: str, storage: StorageBackend, *, reason: str) -> bool:
    """Back up unless another worker already is; True when this one did."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            locked = connection.execute(
                text("select pg_try_advisory_lock(:key)"), {"key": _LOCK_KEY}
            ).scalar()
            if not locked:
                return False
            try:
                back_up(database_url, storage, reason=reason)
            finally:
                connection.execute(text("select pg_advisory_unlock(:key)"), {"key": _LOCK_KEY})
            return True
    finally:
        engine.dispose()


async def run_periodic_backups(
    database_url: str, storage: StorageBackend, *, interval_hours: int
) -> None:
    """Back the database up every ``interval_hours``, for as long as the API runs.

    The first copy is taken one interval after start: the boot step has just
    taken one. A failure is reported and the loop carries on -- a missed
    night must not end the backups for good.
    """
    while True:
        await asyncio.sleep(interval_hours * 3600)
        try:
            await asyncio.to_thread(
                back_up_if_first, database_url, storage, reason="daily"
            )
        except Exception:  # reported, and the next interval tries again
            logger.exception("Scheduled database backup failed")


def back_up(
    database_url: str,
    storage: StorageBackend,
    *,
    reason: str,
    now: datetime | None = None,
    run: Runner = subprocess.run,
) -> str:
    """Dump the database into the bucket and prune old copies; returns the key."""
    key = backup_key(now or datetime.now(UTC), reason)
    data = dump(database_url, run=run)
    storage.save(key=key, data=data, content_type="application/octet-stream")
    listed = getattr(storage, "keys", None)
    removed = prune(storage, listed()) if callable(listed) else 0
    logger.info(
        "Database backed up: %s, %d bytes, %d old backups removed", key, len(data), removed
    )
    return key
