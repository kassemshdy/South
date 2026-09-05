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
