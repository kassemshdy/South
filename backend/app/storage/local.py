"""Local-disk storage.

Used for development, and perfectly serviceable in production on a VPS or a
Railway service with a mounted volume, where the API serves ``/media`` directly.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.errors import ValidationError
from app.storage.base import StoredFile

logger = logging.getLogger(__name__)


class LocalDiskStorage:
    name = "local"

    def __init__(self, root_dir: str, public_prefix: str) -> None:
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._prefix = public_prefix.rstrip("/")

    def _path_for(self, key: str) -> Path:
        # Resolve and confirm containment so a crafted key can never escape the
        # media root via ".." segments.
        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise ValidationError("image.invalid_storage_key", code="invalid_storage_key")
        return candidate

    def save(self, *, key: str, data: bytes, content_type: str) -> StoredFile:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredFile(
            key=key, url=self.url_for(key), size_bytes=len(data), content_type=content_type
        )

    def delete(self, key: str) -> None:
        try:
            self._path_for(key).unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to delete local media file", extra={"storage_key": key})

    def url_for(self, key: str) -> str:
        return f"{self._prefix}/{key.lstrip('/')}"
