"""Copy the files on the media volume into the bucket, once.

Moving uploads from the Railway volume to a bucket means the files already on
the volume have to arrive in the bucket before anything reads them from there.
This runs from the container's start command while both are attached, and it
is idempotent: the bucket is listed once and only the files it lacks are
uploaded, so every boot after the first copies nothing.

Every file on the volume goes, private folders included -- the bucket is
private and ``/media`` refuses those folders whichever backend serves it, so
they are copied exactly as protected as they were.

It never fails a deploy. With the local backend selected, or no volume, it
does nothing; a file it cannot copy is logged and left on the volume.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.storage.factory import get_storage
from app.storage.s3 import S3Storage

logger = logging.getLogger("scripts.copy_media_to_bucket")


def copy(root: Path, storage: S3Storage) -> tuple[int, int]:
    """(copied, failed) for every file under ``root`` the bucket lacks."""
    copied, _already, failed = copy_counts(root, storage)
    return copied, failed


def copy_counts(root: Path, storage: S3Storage) -> tuple[int, int, int]:
    """(copied, already in the bucket, failed) over every file under ``root``."""
    present = storage.keys()
    copied = already = failed = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        key = path.relative_to(root).as_posix()
        if key in present:
            already += 1
            continue
        try:
            content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
            storage.save(key=key, data=path.read_bytes(), content_type=content_type)
            copied += 1
        except Exception:  # one bad file must not stop the rest
            failed += 1
            logger.exception("Could not copy a file to the bucket", extra={"storage_key": key})
    return copied, already, failed


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)
    root = Path(settings.storage_local_dir)
    if settings.storage_backend != "s3" or not root.is_dir():
        return 0
    storage = get_storage()
    if not isinstance(storage, S3Storage):
        return 0
    copied, already, failed = copy_counts(root, storage)
    # In the message itself, not only as extras: the deploy log prints the
    # message, and these three numbers are how the move is verified -- every
    # file on the volume is either copied or already there, and none failed.
    logger.info(
        "Media copied to the bucket: %d copied, %d already there, %d failed, %d on the volume",
        copied,
        already,
        failed,
        copied + already + failed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
