"""Back the database up to the bucket, or raise the alarm if it was wiped.

Runs from the API container's start command before migrations (``--reason
boot``), so every deploy keeps a copy of the database exactly as it was before
the deploy touched it, and from a daily cron (``--reason daily``).

Never fails a deploy: a backup that cannot be taken is logged and reported to
Sentry, and the site still starts. An empty database beside existing uploads
is reported as fatal -- see ``app.services.db_backup``.
"""

from __future__ import annotations

import argparse
import logging

import sentry_sdk

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.observability import configure_error_tracking
from app.services import db_backup
from app.storage.factory import get_storage

logger = logging.getLogger("scripts.backup_db")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reason", default="manual", choices=("boot", "daily", "manual"))
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)
    configure_error_tracking(settings)
    storage = get_storage()

    try:
        if db_backup.database_is_empty(settings.database_url):
            listed = getattr(storage, "keys", None)
            if callable(listed) and db_backup.looks_wiped(listed()):
                message = (
                    "DATABASE IS EMPTY BUT UPLOADS EXIST: the database was probably "
                    "wiped. Restore the newest backups/db/ dump (docs/RESTORE.md) "
                    "before anyone enters data."
                )
                logger.critical(message)
                sentry_sdk.capture_message(message, level="fatal")
                sentry_sdk.flush(timeout=5)
            else:
                logger.info("Database is empty and nothing was ever uploaded: a new site")
            return 0

        db_backup.back_up(settings.database_url, storage, reason=args.reason)
    except Exception:  # a failed backup must never stop the site from starting
        logger.exception("Database backup failed")
        sentry_sdk.capture_exception()
        sentry_sdk.flush(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
