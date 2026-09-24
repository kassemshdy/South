"""Applications that arrived for a number that already has an account.

The public form answers them like any other and acts on none of them; this
is where an administrator reads them instead. See ``DiscardedApplication``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.dependencies import AdminUser, DbSession
from app.core.errors import NotFoundError
from app.models.application import DiscardedApplication
from app.schemas.application import DiscardedApplicationOut

router = APIRouter(prefix="/admin", tags=["admin-applications"])

# Enough to work through by hand; an administrator dismisses as they go.
LIST_LIMIT = 200


@router.get("/discarded-applications", response_model=list[DiscardedApplicationOut])
def list_discarded_applications(
    db: DbSession,
    admin: AdminUser,
    include_dismissed: Annotated[bool, Query()] = False,
) -> list[DiscardedApplicationOut]:
    stmt = select(DiscardedApplication)
    if not include_dismissed:
        stmt = stmt.where(DiscardedApplication.dismissed_at.is_(None))
    rows = db.execute(
        stmt.order_by(DiscardedApplication.created_at.desc()).limit(LIST_LIMIT)
    ).scalars()
    return [DiscardedApplicationOut.model_validate(row) for row in rows]


@router.post(
    "/discarded-applications/{application_id}/dismiss",
    response_model=DiscardedApplicationOut,
)
def dismiss_discarded_application(
    application_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> DiscardedApplicationOut:
    row = db.get(DiscardedApplication, application_id)
    if row is None:
        raise NotFoundError("application.not_found")
    if row.dismissed_at is None:
        row.dismissed_at = datetime.now(UTC)
        db.commit()
        db.refresh(row)
    return DiscardedApplicationOut.model_validate(row)
