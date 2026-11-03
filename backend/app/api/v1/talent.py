"""Public talent directory endpoints and the owner's own profile CRUD.

The owner routes carry no profile id: a talent profile is one-per-account, so
``OwnTalentProfile`` resolves it from the authenticated user and there is no
id a caller could substitute to reach someone else's profile.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response, status

from app.api.serializers import owner_talent, paginate, talent_detail, talent_summary
from app.core.cache import cached
from app.core.dependencies import (
    AppSettings,
    ClientIp,
    Crawler,
    CurrentUser,
    DbSession,
    ListingOwner,
    OwnTalentProfile,
    Viewer,
)
from app.core.downloads import content_disposition
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models.enums import (
    EducationLevel,
    TalentKind,
    TalentWorkType,
    VerificationDocumentKind,
    ViewSubject,
    WorkMode,
)
from app.repositories.geo import point_or_none
from app.repositories.talent import ExperienceBand, TalentRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.talent import (
    EmployerRequestIn,
    OwnerTalentOut,
    TalentCreateIn,
    TalentDetailOut,
    TalentSummaryOut,
    TalentUpdateIn,
)
from app.services.analytics import ViewCounterService
from app.services.employer_request import EmployerRequestService
from app.services.talent import TalentService
from app.services.talent_moderation import TalentModerationService
from app.services.testimonial import TestimonialService
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

public_router = APIRouter(tags=["talent"])
owner_router = APIRouter(tags=["my-talent"])


# --- Public ----------------------------------------------------------------


@public_router.get("/talent", response_model=PaginatedResponse[TalentSummaryOut])
def search_talent(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120, description="Free-text search query")] = None,
    skill: Annotated[str | None, Query(description="Talent skill slug")] = None,
    location: Annotated[str | None, Query(description="Location slug")] = None,
    kind: Annotated[
        TalentKind | None, Query(description="Services or job applications; both when absent")
    ] = None,
    work_mode: Annotated[
        WorkMode | None,
        Query(description="Remotely or in person; a profile that does both matches either"),
    ] = None,
    displaced: Annotated[
        bool, Query(description="Only owners who chose to show they are displaced")
    ] = False,
    # The candidate directory's filters (job seekers).
    experience: Annotated[ExperienceBand | None, Query()] = None,
    education: Annotated[EducationLevel | None, Query()] = None,
    work_type: Annotated[TalentWorkType | None, Query()] = None,
    available_now: Annotated[bool, Query()] = False,
    has_cv: Annotated[bool, Query()] = False,
    verified: Annotated[bool, Query()] = False,
    sort: Annotated[
        Literal["newest", "name", "oldest", "experience", "nearest", "rating", "best"], Query()
    ] = "newest",
    # The visitor's position, for "nearest" only -- see search_businesses.
    near_lat: Annotated[float | None, Query(ge=-90, le=90, alias="lat")] = None,
    near_lng: Annotated[float | None, Query(ge=-180, le=180, alias="lng")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[TalentSummaryOut]:
    """Search approved talent profiles. Never returns a non-approved profile."""
    results = TalentRepository(db).search_public(
        q=q,
        skill_slug=skill,
        location_slug=location,
        kind=kind,
        work_mode=work_mode,
        displaced=displaced,
        experience=experience,
        education=education,
        work_type=work_type,
        available_now=available_now,
        has_cv=has_cv,
        verified=verified,
        sort=sort,
        near=point_or_none(near_lat, near_lng),
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
def get_talent(
    slug: Annotated[str, Path(max_length=200)],
    db: DbSession,
    settings: AppSettings,
    viewer: Viewer,
    crawler: Crawler,
) -> TalentDetailOut:
    profile = TalentRepository(db).get_by_slug(slug, public_only=True)
    if profile is None:
        raise NotFoundError("talent.not_public")
    payload = cached(
        f"talent:{slug}",
        lambda: talent_detail(profile, TestimonialService(db, settings).public_for(profile)),
    )
    ViewCounterService(db).record(
        ViewSubject.TALENT, profile.id, owner_id=profile.owner_id, viewer=viewer, crawler=crawler
    )
    return payload


@public_router.post(
    "/talent/{slug}/employer-requests",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def place_employer_request(
    slug: Annotated[str, Path(max_length=200)],
    payload: EmployerRequestIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> MessageResponse:
    """An employer's contact request for an approved job seeker. Logged for
    the team, who pass it on; see app.services.employer_request."""
    profile = TalentRepository(db).get_by_slug(slug, public_only=True)
    if profile is None:
        raise NotFoundError("talent.not_public")
    EmployerRequestService(db, settings).place(profile, payload, client_ip=client_ip)
    return MessageResponse(message=translate("employer_request.received"))


@public_router.get("/talent/{slug}/cv")
def download_talent_cv(
    slug: Annotated[str, Path(max_length=200)], db: DbSession, settings: AppSettings
) -> Response:
    """An approved job seeker's CV, only when they allow the download.

    The file lives in private storage; this route is the one public way to
    it, and answers 404 alike for no CV, a CV kept private and no profile.
    """
    profile = TalentRepository(db).get_by_slug(slug, public_only=True)
    document = (
        profile.owner.document_of(VerificationDocumentKind.CV)
        if profile is not None
        and profile.owner is not None
        and profile.kind is TalentKind.JOB_SEEKER
        and profile.cv_public
        else None
    )
    if document is None:
        raise NotFoundError("talent.cv_not_found")
    data = VerificationDocumentService(get_storage(), settings).read_bytes(document)
    return Response(
        content=data,
        media_type=document.content_type,
        headers={
            "Content-Disposition": content_disposition(
                document.original_filename or f"{profile.slug if profile else 'cv'}.pdf"
            ),
            "Cache-Control": "private, no-store",
        },
    )


# --- Owner -----------------------------------------------------------------


@owner_router.get("/my/talent", response_model=OwnerTalentOut)
def get_my_talent(profile: OwnTalentProfile) -> OwnerTalentOut:
    """The caller's own profile, in any status."""
    return owner_talent(profile)


@owner_router.post(
    "/talent", response_model=OwnerTalentOut, status_code=status.HTTP_201_CREATED
)
def create_talent(
    payload: TalentCreateIn, user: ListingOwner, db: DbSession
) -> OwnerTalentOut:
    """Create the caller's talent profile. Refused for an administrator, for
    the reason recorded on `get_listing_owner`."""
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
