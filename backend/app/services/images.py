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


class ImageService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def process_and_store(
        self,
        *,
        data: bytes,
        content_type: str | None,
        business_id: uuid.UUID,
        kind: ImageKind,
    ) -> StoredFile:
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

        key = f"businesses/{business_id}/{kind.value.lower()}/{uuid.uuid4().hex}.jpg"
        stored = self._storage.save(key=key, data=payload, content_type="image/jpeg")
        logger.info(
            "Stored image",
            extra={
                "business_id": str(business_id),
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
