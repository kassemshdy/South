"""Public talent directory endpoints and the owner's own profile CRUD.

The owner routes carry no profile id: a talent profile is one-per-account, so
``OwnTalentProfile`` resolves it from the authenticated user and there is no
id a caller could substitute to reach someone else's profile.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, status

from app.api.serializers import owner_talent, paginate, talent_detail, talent_summary
from app.core.dependencies import CurrentUser, DbSession, OwnTalentProfile
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.repositories.talent import TalentRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.talent import (
    OwnerTalentOut,
    TalentCreateIn,
    TalentDetailOut,
    TalentSummaryOut,
    TalentUpdateIn,
)
from app.services.talent import TalentService
from app.services.talent_moderation import TalentModerationService

public_router = APIRouter(tags=["talent"])
owner_router = APIRouter(tags=["my-talent"])


# --- Public ----------------------------------------------------------------


@public_router.get("/talent", response_model=PaginatedResponse[TalentSummaryOut])
def search_talent(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120, description="Free-text search query")] = None,
    skill: Annotated[str | None, Query(description="Talent skill slug")] = None,
    location: Annotated[str | None, Query(description="Location slug")] = None,
    sort: Annotated[Literal["newest", "name", "oldest"], Query()] = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[TalentSummaryOut]:
    """Search approved talent profiles. Never returns a non-approved profile."""
    results = TalentRepository(db).search_public(
        q=q,
        skill_slug=skill,
        location_slug=location,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return paginate(results, talent_summary)


@public_router.get("/talent/latest", response_model=list[TalentSummaryOut])
def latest_talent(
    db: DbSession, limit: Annotated[int, Query(ge=1, le=24)] = 8
) -> list[TalentSummaryOut]:
    """Recently approved profiles for the homepage."""
    return [
        talent_summary(profile)
        for profile in TalentRepository(db).recently_approved(limit)
    ]


@public_router.get("/talent/{slug}", response_model=TalentDetailOut)
def get_talent(slug: Annotated[str, Path(max_length=200)], db: DbSession) -> TalentDetailOut:
    profile = TalentRepository(db).get_by_slug(slug, public_only=True)
    if profile is None:
        raise NotFoundError("talent.not_public")
    return talent_detail(profile)


# --- Owner -----------------------------------------------------------------


@owner_router.get("/my/talent", response_model=OwnerTalentOut)
def get_my_talent(profile: OwnTalentProfile) -> OwnerTalentOut:
    """The caller's own profile, in any status."""
    return owner_talent(profile)


@owner_router.post(
    "/talent", response_model=OwnerTalentOut, status_code=status.HTTP_201_CREATED
)
def create_talent(
    payload: TalentCreateIn, user: CurrentUser, db: DbSession
) -> OwnerTalentOut:
    profile = TalentService(db).create(user, payload)
    return owner_talent(profile)


@owner_router.put("/my/talent", response_model=OwnerTalentOut)
def update_talent(
    payload: TalentUpdateIn, profile: OwnTalentProfile, db: DbSession
) -> OwnerTalentOut:
    updated = TalentService(db).update(profile, payload)
    return owner_talent(updated)


@owner_router.delete("/my/talent", response_model=MessageResponse)
def delete_talent(profile: OwnTalentProfile, db: DbSession) -> MessageResponse:
    TalentService(db).delete(profile)
    return MessageResponse(message=translate("talent.deleted"))


@owner_router.post("/my/talent/submit", response_model=OwnerTalentOut)
def submit_talent(
    profile: OwnTalentProfile, user: CurrentUser, db: DbSession
) -> OwnerTalentOut:
    """Send a draft (or a corrected rejection) for administrator review."""
    service = TalentService(db)
    service.assert_ready_for_review(profile)
    updated = TalentModerationService(db).submit_for_review(profile, user)
    return owner_talent(updated)


@owner_router.get("/my/talent/readiness", response_model=list[str])
def talent_readiness(profile: OwnTalentProfile, db: DbSession) -> list[str]:
    """Fields still missing before the profile can be submitted."""
    return TalentService(db).missing_requirements(profile)
