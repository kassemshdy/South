from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import ApplicationKind
from app.schemas.common import ORMModel


class DiscardedApplicationOut(ORMModel):
    """An application set aside because its number already had an account.

    Administrator-only: ``payload`` carries the applicant's identity exactly
    as they typed it, which is the same class of data ``OwnerIdentityOut``
    keeps off every public schema.
    """

    id: uuid.UUID
    kind: ApplicationKind
    login_phone: str
    existing_user_id: uuid.UUID | None = None
    payload: dict[str, Any]
    created_at: datetime
    dismissed_at: datetime | None = None


class AttachedApplicationOut(BaseModel):
    """A set-aside application, now a listing pending review on its account."""

    application: DiscardedApplicationOut
    kind: ApplicationKind
    listing_id: uuid.UUID

