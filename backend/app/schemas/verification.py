from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class VerificationDocumentOut(ORMModel):
    """Metadata only — never a URL. Bytes are fetched through the
    admin-gated download endpoint, not linked directly."""

    id: uuid.UUID
    content_type: str
    original_filename: str | None
    size_bytes: int | None
    created_at: datetime


class BusinessDocumentOut(ORMModel):
    """One of a listing's official papers, as metadata only.

    Same rule as the class above and for the same reason: no ``url`` field, so
    there is nothing to link and nothing to leak. A commercial register names
    the owner and the establishment's address, which the identity boundary
    keeps off every public payload. This class is reachable only from
    ``OwnerBusinessOut`` — never from ``BusinessDetailOut`` — and
    ``tests/test_business_documents.py`` pins that.
    """

    id: uuid.UUID
    content_type: str
    original_filename: str | None
    label: str | None
    size_bytes: int | None
    created_at: datetime
