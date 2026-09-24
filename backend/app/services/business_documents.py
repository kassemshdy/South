"""A business's official papers: validate, store, never expose a public URL.

The commercial register, a municipal licence, a health permit — whatever an
owner has, attached to the listing so a reviewer can see that the
establishment is real, not just that the applicant is.

**Optional, always.** A shop with no paperwork is still a shop, and plenty of
real businesses in the South have never been registered anywhere. Nothing
here is consulted by
:meth:`~app.services.business.BusinessService.missing_requirements`, so a
listing submits and publishes without a single document —
``tests/test_business_documents.py`` pins that, because "optional" is the
kind of property that quietly stops being true.

Validation is delegated to
:class:`~app.services.verification.VerificationDocumentService`: same formats,
same size cap, same refusal of anything whose real bytes are not a document.
A second sniffer here would be a second place for the two to drift apart.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError
from app.models.business import Business, BusinessDocument
from app.services.verification import DOCUMENT_EXTENSIONS, VerificationDocumentService
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

_FOLDER = "business-documents"

#: Private: read through the owner and admin routes, never the media mount.
STORAGE_FOLDERS = frozenset({_FOLDER})


class BusinessDocumentService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings
        self._validator = VerificationDocumentService(storage, settings)

    def store(
        self,
        *,
        db: Session,
        business: Business,
        data: bytes,
        original_filename: str | None,
        label: str | None = None,
    ) -> BusinessDocument:
        """Attach one paper to ``business``, refusing a bad file first.

        Validated before the count is checked so an owner who sends something
        unreadable is told that, rather than being told they are at the limit.
        """
        content_type = self._validator.validate(data)

        attached = int(
            db.execute(
                select(func.count())
                .select_from(BusinessDocument)
                .where(BusinessDocument.business_id == business.id)
            ).scalar_one()
        )
        if attached >= self._settings.max_business_documents:
            raise ValidationError(
                "business_document.limit",
                code="document_limit_reached",
                params={"max": self._settings.max_business_documents},
            )

        key = (
            f"{_FOLDER}/{business.id}/"
            f"{uuid.uuid4().hex}.{DOCUMENT_EXTENSIONS[content_type]}"
        )
        self._storage.save(key=key, data=data, content_type=content_type)

        document = BusinessDocument(
            storage_key=key,
            content_type=content_type,
            original_filename=original_filename[:255] if original_filename else None,
            label=label.strip()[:120] if label and label.strip() else None,
            size_bytes=len(data),
        )
        # Appended rather than db.add()ed so the loaded collection is correct
        # for the serializer that runs straight after the commit.
        business.documents.append(document)
        db.commit()
        db.refresh(document)
        logger.info(
            "Stored business document",
            extra={
                "business_id": str(business.id),
                "storage_key": key,
                "size_bytes": len(data),
            },
        )
        return document

    def delete(self, *, db: Session, business: Business, document_id: uuid.UUID) -> None:
        """Remove one paper, scoped to the business it belongs to.

        The ``business_id`` clause is the scoping rule, not decoration: a
        document id alone from the request would let an owner delete a
        document off somebody else's listing.
        """
        document = db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id == document_id,
                BusinessDocument.business_id == business.id,
            )
        ).scalar_one_or_none()
        if document is None:
            raise NotFoundError("business_document.not_found")

        self._storage.delete(document.storage_key)
        business.documents.remove(document)
        db.commit()

    def read_bytes(self, document: BusinessDocument) -> bytes:
        return self._storage.read(document.storage_key)
