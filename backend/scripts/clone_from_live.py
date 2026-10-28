"""Fill a develop deployment with a copy of the live site's data, once.

For ``api-develop`` only: it runs from the container's start command like
every other boot step, and does nothing at all unless ``CLONE_FROM_DATABASE_URL``
or ``CLONE_FROM_S3_BUCKET`` is set -- which they are on ``api-develop`` and
nowhere else. The live API runs the same image and never has them.

What it does, reading from live and writing only to this deployment:

- **The database**, when this deployment's is still empty: ``pg_dump`` of the
  live database (read-only), or -- from another Railway environment, which
  cannot reach it -- the newest backup the live API left in its bucket
  (``backups/db/``), restored with ``pg_restore`` into this one. Once the
  copy is in, later boots leave it alone; the migrations that follow bring
  it up to this branch's schema, in this database only.
- **The photographs**, every boot: what the live bucket has and this
  deployment's bucket lacks is copied across. Private folders -- ID scans,
  CVs, official papers, ticket attachments and the live database backups --
  are not copied: testing the site does not need them.

Two refusals stand between a typo and the live data: it will not run when the
source and destination databases are the same database, nor when the buckets
are the same bucket. Like the other boot steps, it never fails the boot.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import subprocess

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.services import business_documents, db_backup, feedback_attachments, verification
from app.storage.factory import get_storage
from app.storage.s3 import S3Storage

logger = logging.getLogger("scripts.clone_from_live")

SOURCE_DATABASE = "CLONE_FROM_DATABASE_URL"
SOURCE_BUCKET = {
    "s3_bucket": "CLONE_FROM_S3_BUCKET",
    "s3_endpoint_url": "CLONE_FROM_S3_ENDPOINT_URL",
    "s3_region": "CLONE_FROM_S3_REGION",
    "s3_access_key_id": "CLONE_FROM_S3_ACCESS_KEY_ID",
    "s3_secret_access_key": "CLONE_FROM_S3_SECRET_ACCESS_KEY",
    # The live bucket predates virtual-hosted URLs and may need path style.
    "s3_addressing_style": "CLONE_FROM_S3_ADDRESSING_STYLE",
}

#: Never copied: the same folders ``/media`` refuses (see ``app.main``).
PRIVATE_FOLDERS = (
    verification.STORAGE_FOLDERS
    | business_documents.STORAGE_FOLDERS
    | feedback_attachments.STORAGE_FOLDERS
    | db_backup.STORAGE_FOLDERS
)


def same_database(a: str, b: str) -> bool:
    first, second = make_url(a), make_url(b)
    return (first.host, first.port or 5432, first.database) == (
        second.host,
        second.port or 5432,
        second.database,
    )


def has_schema(database_url: str) -> bool:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return inspect(connection).has_table("alembic_version")
    finally:
        engine.dispose()


def clone_database(source: str, target: str) -> bool:
    """True when the copy was made; False when there was nothing to do."""
    if same_database(source, target):
        logger.error("Refusing to clone: the source and destination are the same database")
        return False
    if not db_backup.database_is_empty(target):
        logger.info("Develop database already holds data; not copying it again")
        return False
    return restore(db_backup.dump(source), target)


def restore_latest_backup(source: S3Storage, target: str) -> bool:
    """The newest ``backups/db/`` dump in the live bucket, restored here."""
    if not db_backup.database_is_empty(target):
        logger.info("Develop database already holds data; not copying it again")
        return False
    stored = source.keys()
    dumps = sorted(key for key in stored if key.startswith("backups/db/"))
    if not dumps:
        logger.error("No database backup in the live bucket to copy")
        return False
    logger.info("Restoring the live backup %s", dumps[-1])
    return restore(source.read(dumps[-1]), target)


def restore(archive: bytes, target: str) -> bool:
    target_url, password = db_backup.libpq_url(target)
    env = {"PATH": os.environ.get("PATH", "")}
    if password:
        env["PGPASSWORD"] = password
    result = subprocess.run(
        ["pg_restore", "--no-owner", "--no-acl", "-d", target_url],
        input=archive,
        capture_output=True,
        timeout=900,
        env=env,
        check=False,
    )
    # pg_restore exits 1 for warnings it got past (an extension comment it may
    # not set, say); the schema version table is what says the copy is usable.
    if result.returncode != 0:
        logger.warning(
            "pg_restore reported problems: %s", result.stderr.decode(errors="replace")[-2000:]
        )
    if not has_schema(target):
        logger.error("The copy did not restore the schema; the develop database is unchanged")
        return False
    logger.info("Live database copied into the develop database (%d bytes)", len(archive))
    return True


def source_bucket_settings(settings: Settings) -> Settings | None:
    values = {field: os.environ.get(name) for field, name in SOURCE_BUCKET.items()}
    if not values["s3_bucket"]:
        return None
    values["s3_addressing_style"] = values["s3_addressing_style"] or "auto"
    return settings.model_copy(update=values)


def clone_media(source: S3Storage, target: S3Storage) -> tuple[int, int, int]:
    """(copied, already there, failed) over the live bucket's public files."""
    present = target.keys()
    copied = already = failed = 0
    for key in sorted(source.keys()):
        if key.split("/", 1)[0] in PRIVATE_FOLDERS:
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
            logger.exception("Could not copy a file", extra={"storage_key": key})
    return copied, already, failed


def main() -> int:
    settings = get_settings()
    source_db = os.environ.get(SOURCE_DATABASE)
    source_settings = source_bucket_settings(settings)
    if not source_db and source_settings is None:
        return 0
    configure_logging(settings.log_level, json_output=False)
    if source_settings is not None and (
        source_settings.s3_bucket,
        source_settings.s3_endpoint_url,
    ) == (settings.s3_bucket, settings.s3_endpoint_url):
        logger.error("Refusing to clone: the source and destination are the same bucket")
        return 0

    try:
        if source_db:
            clone_database(source_db, settings.database_url)
        elif source_settings is not None:
            restore_latest_backup(S3Storage(source_settings), settings.database_url)
    except Exception:
        logger.exception("Could not copy the live database")

    try:
        target = get_storage()
        if source_settings is None or not isinstance(target, S3Storage):
            return 0
        copied, already, failed = clone_media(S3Storage(source_settings), target)
        logger.info(
            "Live photographs copied: %d copied, %d already there, %d failed",
            copied,
            already,
            failed,
        )
    except Exception:
        logger.exception("Could not copy the live photographs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
