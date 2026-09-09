"""Public directory endpoints and the owner's business CRUD."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, status

from app.api.serializers import business_detail, business_summary, owner_business, paginate
from app.core.dependencies import (
    AppSettings,
    CurrentUser,
    DbSession,
    OwnedBusiness,
    Viewer,
)
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models.enums import ViewSubject
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.schemas.business import (
    BusinessCreateIn,
    BusinessDetailOut,
    BusinessSummaryOut,
    BusinessUpdateIn,
    OwnerBusinessOut,
)
from app.schemas.common import MessageResponse, PaginatedResponse, PublicStatsOut
from app.services.analytics import ViewCounterService
from app.services.business import BusinessService
from app.services.moderation import ModerationService
from app.services.testimonial import TestimonialService

public_router = APIRouter(tags=["businesses"])
owner_router = APIRouter(tags=["my-businesses"])


# --- Public ----------------------------------------------------------------


@public_router.get("/businesses", response_model=PaginatedResponse[BusinessSummaryOut])
def search_businesses(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120, description="Free-text search query")] = None,
    category: Annotated[str | None, Query(description="Category slug")] = None,
    location: Annotated[str | None, Query(description="Location slug")] = None,
    sort: Annotated[Literal["newest", "name", "oldest"], Query()] = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[BusinessSummaryOut]:
    """Search approved businesses. Filters combine; never returns a non-approved listing."""
    results = BusinessRepository(db).search_public(
        q=q,
        category_slug=category,
        location_slug=location,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return paginate(results, business_summary)


@public_router.get("/businesses/latest", response_model=list[BusinessSummaryOut])
def latest_businesses(
    db: DbSession, limit: Annotated[int, Query(ge=1, le=24)] = 8
) -> list[BusinessSummaryOut]:
    """Recently approved listings for the homepage."""
    return [
        business_summary(business)
        for business in BusinessRepository(db).recently_approved(limit)
    ]


@public_router.get("/businesses/stats", response_model=PublicStatsOut)
def public_stats(db: DbSession) -> PublicStatsOut:
    """Homepage stats strip: approved-only counts, safe for an anonymous visitor."""
    repo = BusinessRepository(db)
    return PublicStatsOut(
        total_businesses=repo.public_business_count(),
        total_towns=repo.public_town_count(),
        total_talents=TalentRepository(db).public_profile_count(),
    )


@public_router.get("/businesses/{slug}", response_model=BusinessDetailOut)
def get_business(
    slug: Annotated[str, Path(max_length=200)],
    db: DbSession,
    viewer: Viewer,
    settings: AppSettings,
) -> BusinessDetailOut:
    business = BusinessRepository(db).get_by_slug(slug, public_only=True)
    if business is None:
        raise NotFoundError("business.not_public")
    # Serialised before the counter is touched, so nothing about counting a
    # view can change or delay what the visitor gets back.
    # Approved only, and fetched through the service rather than read off the
    # relationship -- see business_detail's docstring.
    payload = business_detail(business, TestimonialService(db, settings).public_for(business))
    ViewCounterService(db).record(
        ViewSubject.BUSINESS,
        business.id,
        owner_id=business.owner_id,
        viewer=viewer,
    )
    return payload


# --- Owner -----------------------------------------------------------------


@owner_router.get("/my/businesses", response_model=list[OwnerBusinessOut])
def list_my_businesses(user: CurrentUser, db: DbSession) -> list[OwnerBusinessOut]:
    """Every listing owned by the caller, in any status."""
    return [
        owner_business(business)
        for business in BusinessRepository(db).list_for_owner(user.id)
    ]


@owner_router.post(
    "/businesses", response_model=OwnerBusinessOut, status_code=status.HTTP_201_CREATED
)
def create_business(
    payload: BusinessCreateIn, user: CurrentUser, db: DbSession
) -> OwnerBusinessOut:
    business = BusinessService(db).create(user, payload)
    return owner_business(business)


@owner_router.get("/businesses/{business_id}/manage", response_model=OwnerBusinessOut)
def get_my_business(business: OwnedBusiness) -> OwnerBusinessOut:
    return owner_business(business)


@owner_router.put("/businesses/{business_id}", response_model=OwnerBusinessOut)
def update_business(
    payload: BusinessUpdateIn, business: OwnedBusiness, db: DbSession
) -> OwnerBusinessOut:
    updated = BusinessService(db).update(business, payload)
    return owner_business(updated)


@owner_router.delete("/businesses/{business_id}", response_model=MessageResponse)
def delete_business(business: OwnedBusiness, db: DbSession) -> MessageResponse:
    BusinessService(db).delete(business)
    return MessageResponse(message=translate("business.deleted"))


@owner_router.post("/businesses/{business_id}/submit", response_model=OwnerBusinessOut)
def submit_business(
    business: OwnedBusiness, user: CurrentUser, db: DbSession
) -> OwnerBusinessOut:
    """Send a draft (or a corrected rejection) for administrator review."""
    service = BusinessService(db)
    service.assert_ready_for_review(business)
    updated = ModerationService(db).submit_for_review(business, user)
    return owner_business(updated)


@owner_router.get("/businesses/{business_id}/readiness", response_model=list[str])
def submission_readiness(business: OwnedBusiness, db: DbSession) -> list[str]:
    """Fields still missing before the listing can be submitted."""
    return BusinessService(db).missing_requirements(business)
