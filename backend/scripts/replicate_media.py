"""Copy the site's bucket to the off-site replica once, at boot.

See ``app.services.media_replica``. Runs in the background from the start
command, because a first copy of every file takes longer than the
healthcheck allows, and never fails a deploy.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services import media_replica
from app.storage.factory import get_storage

logger = logging.getLogger("scripts.replicate_media")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)
    if not settings.replica_s3_bucket:
        return 0
    try:
        media_replica.replicate_if_first(settings, get_storage())
    except Exception:  # a wrong key or an unreachable bucket must not stop the site
        logger.exception("Replica copy failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
