from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalDiskStorage
from app.storage.s3 import S3Storage


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    return LocalDiskStorage(settings.storage_local_dir, settings.storage_public_prefix)
