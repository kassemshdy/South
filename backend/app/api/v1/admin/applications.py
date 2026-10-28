"""Applications that arrived for a number that already has an account.

The public form answers them like any other and acts on none of them; this
is where an administrator reads them instead. See ``DiscardedApplication``.

An administrator who has made sure the application is the account holder's
own -- a second listing from the same person, typically a shop after a
services profile -- can add it to that account (the owners' decision,
28 Oct 2026). It lands pending review, like any application, and the
account's identity is left as it is: a person decided, so the form is still
no way for a stranger to put something in someone else's dashboard.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.dependencies import AdminUser, DbSession
from app.core.errors import ConflictError, NotFoundError
from app.models.application import DiscardedApplication
from app.models.enums import ApplicationKind, BusinessStatus, UserRole
from app.models.user import User
from app.repositories.talent import TalentRepository
from app.schemas.application import AttachedApplicationOut, DiscardedApplicationOut
from app.schemas.registration import BusinessRegistrationIn, TalentRegistrationIn
from app.services.business import BusinessService
from app.services.talent import TalentService

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


@router.post(
    "/discarded-applications/{application_id}/attach",
    response_model=AttachedApplicationOut,
)
def attach_discarded_application(
    application_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> AttachedApplicationOut:
    """Add a set-aside application to the account its number belongs to.

    Validated as the public form validates it, created pending review, and
    the application marked handled in the same transaction.
    """
    row = db.get(DiscardedApplication, application_id)
    if row is None:
        raise NotFoundError("application.not_found")
    if row.dismissed_at is not None:
        raise ConflictError("application.already_handled", code="application_handled")
    owner = db.get(User, row.existing_user_id) if row.existing_user_id else None
    if owner is None or owner.role != UserRole.OWNER:
        raise ConflictError("application.no_owner_account", code="application_no_account")

    listing_id: uuid.UUID
    if row.kind == ApplicationKind.BUSINESS:
        business = BusinessService(db).create(
            owner, BusinessRegistrationIn.model_validate(row.payload).business
        )
        business.status = BusinessStatus.PENDING_REVIEW
        listing_id = business.id
    else:
        talent = TalentRegistrationIn.model_validate(row.payload).talent
        if TalentRepository(db).get_for_owner(owner.id) is not None:
            raise ConflictError("application.talent_exists", code="talent_profile_exists")
        profile = TalentService(db).create(owner, talent)
        profile.status = BusinessStatus.PENDING_REVIEW
        listing_id = profile.id

    row.dismissed_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return AttachedApplicationOut(
        application=DiscardedApplicationOut.model_validate(row),
        kind=row.kind,
        listing_id=listing_id,
    )

