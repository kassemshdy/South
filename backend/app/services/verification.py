"""Personal-document ingestion: validate, store, never expose a public URL.

Covers both documents an account can attach — the ID scan every owner uploads
and the CV a talent profile may add — told apart by
:class:`~app.models.enums.VerificationDocumentKind`.

Unlike image uploads, a document must survive unmodified — a resized/
re-encoded ID scan can become illegible, and a PDF cannot be decoded by
Pillow at all — so this does not build on :class:`~app.services.images.
ImageService`. The client-supplied content type is never trusted; real bytes
are sniffed against each format's magic number, the same distrust
``ImageService`` already applies to images.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import PayloadTooLargeError, UnsupportedMediaTypeError
from app.models.enums import VerificationDocumentKind
from app.models.user import User
from app.models.verification import OwnerVerificationDocument
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

_MAGIC_BYTES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
_EXTENSIONS = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}
# Separate prefixes so a bucket listing still says what a file is, and so an
# accidentally over-broad rule on one prefix cannot expose the other.
_FOLDERS = {
    VerificationDocumentKind.IDENTITY: "owner-verification",
    VerificationDocumentKind.CV: "owner-cv",
}


class VerificationDocumentService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def store(
        self,
        *,
        db: Session,
        user: User,
        data: bytes,
        original_filename: str | None,
        kind: VerificationDocumentKind = VerificationDocumentKind.IDENTITY,
    ) -> OwnerVerificationDocument:
        """Replace ``user``'s document of ``kind`` (one per owner) with ``data``."""
        if not data:
            raise UnsupportedMediaTypeError("verification.empty")
        if len(data) > self._settings.max_verification_doc_bytes:
            limit_mb = self._settings.max_verification_doc_bytes / (1024 * 1024)
            raise PayloadTooLargeError(
                "verification.too_large", params={"limit": f"{limit_mb:.0f}"}
            )

        content_type = self._sniff(data)

        existing = user.document_of(kind)
        if existing is not None:
            self._storage.delete(existing.storage_key)
            user.documents.remove(existing)
            db.flush()

        folder = _FOLDERS[kind]
        key = f"{folder}/{user.id}/{uuid.uuid4().hex}.{_EXTENSIONS[content_type]}"
        self._storage.save(key=key, data=data, content_type=content_type)

        document = OwnerVerificationDocument(
            kind=kind,
            storage_key=key,
            content_type=content_type,
            original_filename=original_filename[:255] if original_filename else None,
            size_bytes=len(data),
        )
        # Appended rather than db.add()ed so the loaded collection — and the
        # per-kind accessors reading it — stay correct after the commit.
        user.documents.append(document)
        db.commit()
        db.refresh(document)
        logger.info(
            "Stored owner document",
            extra={
                "user_id": str(user.id),
                "kind": kind.value,
                "storage_key": key,
                "size_bytes": len(data),
            },
        )
        return document

    def read_bytes(self, document: OwnerVerificationDocument) -> bytes:
        return self._storage.read(document.storage_key)

    # --- internals ---------------------------------------------------------

    def _sniff(self, data: bytes) -> str:
        for magic, content_type in _MAGIC_BYTES:
            if data.startswith(magic):
                return content_type
        raise UnsupportedMediaTypeError("verification.unsupported_format")
