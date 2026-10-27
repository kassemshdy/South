"""Administrator moderation endpoints for talent profiles.

Every route here depends on ``AdminUser``; there is no code path that reaches a
moderation action without that check.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.serializers import admin_talent, paginate
from app.core.dependencies import AdminUser, DbSession
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile
from app.repositories.talent import TalentRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.moderation import AdminTalentOut, RejectIn, SuspendIn
from app.schemas.talent import TalentSkillChangeIn, TalentUpdateIn
from app.services.account import AccountDeletionService
from app.services.talent import TalentService
from app.services.talent_moderation import TalentModerationService
from app.storage.factory import get_storage

router = APIRouter(prefix="/admin", tags=["admin-talent"])


def _load(db: DbSession, profile_id: uuid.UUID) -> TalentProfile:
    profile = TalentRepository(db).get_for_admin(profile_id)
    if profile is None:
        raise NotFoundError("talent.not_found")
    return profile


@router.get("/talent", response_model=PaginatedResponse[AdminTalentOut])
def list_talent(
    db: DbSession,
    admin: AdminUser,
    status: Annotated[BusinessStatus | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[AdminTalentOut]:
    results = TalentRepository(db).list_for_admin(
        status=status, q=q, page=page, page_size=page_size
    )
    return paginate(results, admin_talent)


@router.get("/talent/pending", response_model=PaginatedResponse[AdminTalentOut])
def list_pending_talent(
    db: DbSession,
    admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[AdminTalentOut]:
    """The review queue, oldest submission first."""
    results = TalentRepository(db).list_for_admin(
        status=BusinessStatus.PENDING_REVIEW, page=page, page_size=page_size
    )
    return paginate(results, admin_talent)


@router.get("/talent/{profile_id}", response_model=AdminTalentOut)
def get_talent(profile_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminTalentOut:
    return admin_talent(_load(db, profile_id))


@router.post("/talent/{profile_id}/approve", response_model=AdminTalentOut)
def approve(profile_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminTalentOut:
    profile = TalentModerationService(db).approve(_load(db, profile_id), admin)
    return admin_talent(profile)


@router.post("/talent/{profile_id}/reject", response_model=AdminTalentOut)
def reject(
    profile_id: uuid.UUID, payload: RejectIn, db: DbSession, admin: AdminUser
) -> AdminTalentOut:
    profile = TalentModerationService(db).reject(_load(db, profile_id), admin, payload.reason)
    return admin_talent(profile)


@router.post("/talent/{profile_id}/suspend", response_model=AdminTalentOut)
def suspend(
    profile_id: uuid.UUID, payload: SuspendIn, db: DbSession, admin: AdminUser
) -> AdminTalentOut:
    profile = TalentModerationService(db).suspend(_load(db, profile_id), admin, payload.reason)
    return admin_talent(profile)


@router.post("/talent/{profile_id}/reactivate", response_model=AdminTalentOut)
def reactivate(profile_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminTalentOut:
    profile = TalentModerationService(db).reactivate(_load(db, profile_id), admin)
    return admin_talent(profile)


@router.post("/talent/{profile_id}/skill", response_model=AdminTalentOut)
def set_skill(
    profile_id: uuid.UUID, payload: TalentSkillChangeIn, db: DbSession, admin: AdminUser
) -> AdminTalentOut:
    """Correct the skill an applicant chose, on their behalf.

    Through the owner's own update path, so the skill is validated against
    the taxonomy and the search text is rebuilt exactly as when they edit it.
    """
    TalentService(db).update(
        _load(db, profile_id),
        TalentUpdateIn(skill_id=payload.skill_id, custom_skill_text=payload.custom_skill_text),
    )
    return admin_talent(_load(db, profile_id))


@router.delete("/talent/{profile_id}", response_model=MessageResponse)
def delete_talent(profile_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    """Remove the profile and its files for good -- see admin/businesses.py.
    The owner's account stays."""
    AccountDeletionService(db, get_storage()).delete_profile(_load(db, profile_id))
    return MessageResponse(message=translate("talent.deleted"))
