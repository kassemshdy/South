"""Feedback attachment ingestion: validate, store, never trust the client.

A bug screenshot needs to stay pixel-faithful — re-encoding it the way
:class:`~app.services.images.ImageService` does for a business's photos would
blur exactly the UI text a screenshot exists to show — so this stores bytes
as received, the same choice
:class:`~app.services.verification.VerificationDocumentService` makes for
identity documents. Real bytes are sniffed against each format's magic
number; the client-supplied content type is a hint, not evidence.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import PayloadTooLargeError, UnsupportedMediaTypeError, ValidationError
from app.models.enums import FeedbackAttachmentKind
from app.models.feedback import FeedbackAttachment, FeedbackTicket
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_DOCUMENT_CONTENT_TYPES = {"application/pdf"}
_FOLDER = "feedback"

#: Private: a ticket's attachments are read through the board's own routes.
STORAGE_FOLDERS = frozenset({_FOLDER})

_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


def _sniff(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    raise UnsupportedMediaTypeError("feedback.unsupported_attachment_format")


class FeedbackAttachmentService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def store(
        self,
        *,
        db: Session,
        ticket: FeedbackTicket,
        data: bytes,
        kind: FeedbackAttachmentKind,
        original_filename: str | None,
    ) -> FeedbackAttachment:
        if not data:
            raise UnsupportedMediaTypeError("feedback.attachment_empty")
        if len(data) > self._settings.max_feedback_attachment_bytes:
            limit_mb = self._settings.max_feedback_attachment_bytes / (1024 * 1024)
            raise PayloadTooLargeError(
                "feedback.attachment_too_large", params={"limit": f"{limit_mb:.0f}"}
            )
        if len(ticket.attachments) >= self._settings.max_feedback_attachments_per_ticket:
            raise ValidationError(
                "feedback.attachment_limit",
                code="attachment_limit_reached",
                params={"max": self._settings.max_feedback_attachments_per_ticket},
            )

        content_type = _sniff(data)
        allowed = (
            _DOCUMENT_CONTENT_TYPES
            if kind is FeedbackAttachmentKind.DOCUMENT
            else _IMAGE_CONTENT_TYPES
        )
        if content_type not in allowed:
            raise UnsupportedMediaTypeError("feedback.attachment_kind_mismatch")

        key = f"{_FOLDER}/{ticket.id}/{uuid.uuid4().hex}.{_EXTENSIONS[content_type]}"
        self._storage.save(key=key, data=data, content_type=content_type)

        attachment = FeedbackAttachment(
            ticket_id=ticket.id,
            storage_key=key,
            content_type=content_type,
            kind=kind,
            original_filename=original_filename[:255] if original_filename else None,
            size_bytes=len(data),
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        logger.info(
            "Stored feedback attachment",
            extra={"ticket_id": str(ticket.id), "storage_key": key, "size_bytes": len(data)},
        )
        return attachment

    def delete(self, db: Session, attachment: FeedbackAttachment) -> None:
        self._storage.delete(attachment.storage_key)
        db.delete(attachment)
        db.commit()

    def read_bytes(self, attachment: FeedbackAttachment) -> bytes:
        return self._storage.read(attachment.storage_key)
