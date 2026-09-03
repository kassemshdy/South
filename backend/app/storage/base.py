"""Storage seam.

The application stores only image *metadata* in PostgreSQL; bytes go to a
storage backend behind this protocol, so local disk, S3-compatible object
storage (AWS, Cloudflare R2, Backblaze, MinIO) or a CDN can be swapped by
configuration alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StoredFile:
    key: str
    url: str
    size_bytes: int
    content_type: str
    width: int | None = None
    height: int | None = None


@runtime_checkable
class StorageBackend(Protocol):
    name: str

    def save(self, *, key: str, data: bytes, content_type: str) -> StoredFile:
        """Persist ``data`` at ``key`` and return its public URL."""
        ...

    def delete(self, key: str) -> None:
        """Remove an object. Must not raise when the key is already gone."""
        ...

    def url_for(self, key: str) -> str:
        ...

    def exists(self, key: str) -> bool:
        """Whether ``key`` currently has bytes behind it."""
        ...
