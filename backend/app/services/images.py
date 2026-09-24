"""Image ingestion: validate, normalize, resize, store.

Uploads are never trusted. A file is accepted only if Pillow can actually decode
it as one of the allowed formats — the client-supplied content type and filename
extension are hints, not evidence. Images are then re-encoded, which strips EXIF
(including GPS coordinates a shop owner did not intend to publish) and bounds the
stored size.
"""

from __future__ import annotations

import io
import logging
import re
import uuid
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import PayloadTooLargeError, UnsupportedMediaTypeError
from app.models.enums import ImageKind
from app.storage.base import StorageBackend, StoredFile

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


@dataclass(frozen=True)
class ImageVariant:
    """Target dimensions per image role."""

    max_width: int
    max_height: int
    quality: int


VARIANTS: dict[ImageKind, ImageVariant] = {
    ImageKind.LOGO: ImageVariant(600, 600, 85),
    ImageKind.COVER: ImageVariant(1600, 900, 82),
    ImageKind.GALLERY: ImageVariant(1400, 1400, 82),
    ImageKind.ITEM: ImageVariant(900, 900, 82),
}

#: A second, small copy for the places a photo is drawn small: directory and
#: product cards, the logo badge on a card. A business card draws its cover in
#: a strip about 380px wide and used to download the 1600px original for it --
#: roughly 330 KB a card, several megabytes for one page of results on a phone.
#: Bounded at about twice the largest size each is drawn, for sharp screens.
#: The gallery has none: it is only ever shown large.
THUMBNAILS: dict[ImageKind, ImageVariant] = {
    ImageKind.LOGO: ImageVariant(192, 192, 80),
    ImageKind.COVER: ImageVariant(720, 720, 78),
    ImageKind.ITEM: ImageVariant(640, 640, 78),
}

_THUMB_SUFFIX = ".thumb.jpg"
_THUMBNAILED_URL = re.compile(
    "/(?:" + "|".join(kind.value.lower() for kind in THUMBNAILS) + r")/[0-9a-f]{32}\.jpg$"
)


def thumbnail_key(key: str) -> str | None:
    """Where the small copy of the image stored at ``key`` lives.

    Derived rather than stored, so no column and no migration: every image
    the pipeline writes ends in ``.jpg``, and its thumbnail sits beside it.
    """
    if not key.endswith(".jpg") or key.endswith(_THUMB_SUFFIX):
        return None
    return key[: -len(".jpg")] + _THUMB_SUFFIX


def thumbnail_url(url: str | None) -> str | None:
    """The public URL of an image's small copy, or None if it cannot have one.

    Only for images this pipeline stored under a kind that has thumbnails:
    the URL ends in the key, ``<kind>/<random hex>.jpg``. Anything else --
    an external URL, a gallery image -- gets None, and the caller shows the
    full image.
    """
    if not url or _THUMBNAILED_URL.search(url) is None:
        return None
    return thumbnail_key(url)


def render_thumbnail(jpeg: bytes, kind: ImageKind) -> bytes | None:
    """The small copy of an already-normalised image, or None for a kind
    that has none."""
    variant = THUMBNAILS.get(kind)
    if variant is None:
        return None
    image = Image.open(io.BytesIO(jpeg)).convert("RGB")
    image.thumbnail((variant.max_width, variant.max_height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=variant.quality, optimize=True, progressive=True)
    return buffer.getvalue()


class ImageService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def process_and_store(
        self,
        *,
        data: bytes,
        content_type: str | None,
        owner_id: uuid.UUID,
        kind: ImageKind,
        prefix: str = "businesses",
    ) -> StoredFile:
        """Validate, re-encode and store one image.

        ``prefix``/``owner_id`` decide the storage path, so the same pipeline
        serves both ``businesses/<id>/...`` and ``talent/<id>/...`` without the
        caller reaching into the storage backend itself.
        """
        if len(data) > self._settings.max_upload_bytes:
            limit_mb = self._settings.max_upload_bytes / (1024 * 1024)
            raise PayloadTooLargeError(
                "image.too_large", params={"limit": f"{limit_mb:.0f}"}
            )
        if not data:
            raise UnsupportedMediaTypeError("image.empty")

        if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedMediaTypeError("image.unsupported_format")

        image = self._decode(data)
        variant = VARIANTS[kind]
        payload, width, height = self._render(image, variant)

        key = f"{prefix}/{owner_id}/{kind.value.lower()}/{uuid.uuid4().hex}.jpg"
        stored = self._storage.save(key=key, data=payload, content_type="image/jpeg")
        self._store_thumbnail(key, payload, kind)
        logger.info(
            "Stored image",
            extra={
                "owner_id": str(owner_id),
                "kind": kind.value,
                "storage_key": key,
                "size_bytes": len(payload),
            },
        )
        return StoredFile(
            key=stored.key,
            url=stored.url,
            size_bytes=len(payload),
            content_type="image/jpeg",
            width=width,
            height=height,
        )

    def delete(self, key: str | None) -> None:
        if key:
            self._storage.delete(key)
            thumb = thumbnail_key(key)
            if thumb is not None and self._storage.exists(thumb):
                self._storage.delete(thumb)

    def ensure_thumbnail(self, key: str | None, kind: ImageKind) -> bool:
        """Write the small copy of an image stored before thumbnails existed.

        True when one was written. Idempotent, so it is safe on every boot.
        """
        thumb = thumbnail_key(key) if key else None
        if key is None or thumb is None or kind not in THUMBNAILS:
            return False
        if self._storage.exists(thumb) or not self._storage.exists(key):
            return False
        return self._store_thumbnail(key, self._storage.read(key), kind)

    def _store_thumbnail(self, key: str, jpeg: bytes, kind: ImageKind) -> bool:
        thumb = thumbnail_key(key)
        payload = render_thumbnail(jpeg, kind)
        if thumb is None or payload is None:
            return False
        self._storage.save(key=thumb, data=payload, content_type="image/jpeg")
        return True

    def exists(self, key: str | None) -> bool:
        if not key:
            return False
        return self._storage.exists(key)

    # --- internals ---------------------------------------------------------

    def _decode(self, data: bytes) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()  # structural check; consumes the file object
            image = Image.open(io.BytesIO(data))
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise UnsupportedMediaTypeError("image.unreadable") from exc

        if image.format not in ALLOWED_FORMATS:
            raise UnsupportedMediaTypeError("image.unsupported_format")
        return image

    def _render(self, image: Image.Image, variant: ImageVariant) -> tuple[bytes, int, int]:
        # Flatten transparency onto white so PNG/WEBP logos do not turn black
        # once re-encoded as JPEG.
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        image.thumbnail((variant.max_width, variant.max_height), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=variant.quality, optimize=True, progressive=True)
        return buffer.getvalue(), image.width, image.height
