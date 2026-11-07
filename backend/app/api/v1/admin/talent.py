"""Administrator moderation endpoints for talent profiles.

Every route here depends on ``AdminUser``; there is no code path that reaches a
moderation action without that check.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.api.serializers import admin_talent, paginate
from app.api.v1.talent_images import COVER_KIND, PHOTO_KIND, store_talent_image
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.core.i18n import translate
from app.core.uploads import read_at_most
from app.models.enums import BusinessStatus, EmployerRequestStatus, ImageKind
from app.models.talent import EmployerRequest, TalentProfile
from app.repositories.talent import TalentRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.moderation import AdminTalentOut, PlaceChangeIn, RejectIn, SuspendIn
from app.schemas.talent import (
    ConvertedOut,
    ConvertToBusinessIn,
    EmployerRequestOut,
    EmployerRequestStatusIn,
    TalentSkillChangeIn,
    TalentUpdateIn,
)
from app.services import staff_notices
from app.services.account import AccountDeletionService
from app.services.employer_request import EmployerRequestService
from app.services.talent import TalentService
from app.services.talent_conversion import TalentConversionService
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
    """The review queue, newest submission first."""
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
    staff_notices.moderated(
        approved=True,
        listing="service",
        name=profile.display_name,
        admin=admin,
        reason=None,
        path=f"/admin/talent/{profile.id}",
    )
    return admin_talent(profile)


@router.post("/talent/{profile_id}/reject", response_model=AdminTalentOut)
def reject(
    profile_id: uuid.UUID, payload: RejectIn, db: DbSession, admin: AdminUser
) -> AdminTalentOut:
    profile = TalentModerationService(db).reject(_load(db, profile_id), admin, payload.reason)
    staff_notices.moderated(
        approved=False,
        listing="service",
        name=profile.display_name,
        admin=admin,
        reason=payload.reason,
        path=f"/admin/talent/{profile.id}",
    )
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


@router.post("/talent/{profile_id}/place", response_model=AdminTalentOut)
def set_place(
    profile_id: uuid.UUID, payload: PlaceChangeIn, db: DbSession, admin: AdminUser
) -> AdminTalentOut:
    """Correct a service profile's town and map pin, as for a shop."""
    TalentService(db).update(
        _load(db, profile_id),
        TalentUpdateIn(
            location_id=payload.location_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
        ),
    )
    return admin_talent(_load(db, profile_id))


@router.post("/talent/{profile_id}/images", response_model=AdminTalentOut)
def upload_profile_image(
    profile_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    admin: AdminUser,
    file: Annotated[UploadFile, File(description="Image file")],
    kind: Annotated[ImageKind, Form()] = ImageKind.LOGO,
) -> AdminTalentOut:
    """A photo or cover for a profile that went live without one, as a
    business's logo and cover can be added from its review page. Photo and
    cover only: the portfolio stays the owner's."""
    if kind not in (PHOTO_KIND, COVER_KIND):
        raise ValidationError("image.invalid_kind", code="invalid_image_kind")
    data = read_at_most(file.file, settings.max_upload_bytes)
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()
    profile = _load(db, profile_id)
    store_talent_image(
        db, settings, profile, kind=kind, data=data, content_type=file.content_type
    )
    db.commit()
    return admin_talent(_load(db, profile_id))


@router.post("/talent/{profile_id}/convert-to-business", response_model=ConvertedOut)
def convert_to_business(
    profile_id: uuid.UUID, payload: ConvertToBusinessIn, db: DbSession, admin: AdminUser
) -> ConvertedOut:
    """Move a profile that sells goods into a shop -- see TalentConversionService."""
    business = TalentConversionService(db).to_business(
        _load(db, profile_id), payload.category_id
    )
    return ConvertedOut(business_id=business.id)


@router.delete("/talent/{profile_id}", response_model=MessageResponse)
def delete_talent(profile_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    """Remove the profile and its files for good -- see admin/businesses.py.
    The owner's account stays."""
    AccountDeletionService(db, get_storage()).delete_profile(_load(db, profile_id))
    return MessageResponse(message=translate("talent.deleted"))


# --- Employer requests -------------------------------------------------------


def _employer_request_out(request: EmployerRequest) -> EmployerRequestOut:
    profile = request.profile
    return EmployerRequestOut(
        id=request.id,
        profile_id=request.profile_id,
        candidate_name=profile.display_name if profile else None,
        candidate_slug=profile.slug if profile else None,
        # The candidate's own number whatever they show the public: the team
        # relays the request to them.
        candidate_whatsapp=(profile.whatsapp or profile.phone) if profile else None,
        employer_name=request.employer_name,
        phone=request.phone,
        company=request.company,
        job_title=request.job_title,
        message=request.message,
        status=request.status,
        created_at=request.created_at,
    )


@router.get("/employer-requests", response_model=list[EmployerRequestOut])
def list_employer_requests(
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
    status: Annotated[EmployerRequestStatus | None, Query()] = None,
) -> list[EmployerRequestOut]:
    """Every employer's request for a candidate, newest first."""
    return [
        _employer_request_out(request)
        for request in EmployerRequestService(db, settings).list_all(status)
    ]


@router.post("/employer-requests/{request_id}/status", response_model=EmployerRequestOut)
def set_employer_request_status(
    request_id: uuid.UUID,
    payload: EmployerRequestStatusIn,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> EmployerRequestOut:
    request = EmployerRequestService(db, settings).set_status(request_id, payload.status)
    return _employer_request_out(request)
