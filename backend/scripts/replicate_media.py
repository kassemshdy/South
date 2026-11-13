"""Copy the site's bucket to the off-site replicas (S3, Google Drive) once, at boot.

See ``app.services.media_replica``. Runs in the background from the start
command, because a first copy of every file takes longer than the
healthcheck allows, and never fails a deploy.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services import drive_replica, media_replica
from app.storage.factory import get_storage

logger = logging.getLogger("scripts.replicate_media")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)
    if settings.replica_s3_bucket:
        try:
            media_replica.replicate_if_first(settings, get_storage())
        except Exception:  # a wrong key or an unreachable bucket must not stop the site
            logger.exception("Replica copy failed")
    # The Google Drive copy, after the S3 one, by the same rule.
    if settings.gdrive_folder_id and settings.gdrive_service_account_json:
        try:
            drive_replica.replicate_if_first(settings, get_storage())
        except Exception:  # a wrong key or an unshared folder must not stop the site
            logger.exception("Google Drive copy failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
