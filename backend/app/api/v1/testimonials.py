"""Testimonials: a visitor submits, an administrator publishes or removes.

Three audiences, three routers, and the split is the disclosure boundary:

- the public routes only ever *write*. Reading a testimonial publicly happens
  through the listing's own page, which is served approved-only;
- the owner routes only *read*, and only what is already published: the
  owners decided (round 3) that the administrator's approval alone publishes
  one, so an owner neither approves nor hides;
- approving, rejecting and removing are an administrator's.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.serializers import admin_testimonial, owner_testimonial
from app.core.dependencies import (
    AdminUser,
    AppSettings,
    ClientIp,
    DbSession,
    OwnedBusiness,
    OwnTalentProfile,
)
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.models.enums import TalentKind, TestimonialStatus
from app.models.testimonial import Testimonial
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.testimonial import TestimonialRepository
from app.schemas.common import MessageResponse
from app.schemas.testimonial import (
    AdminTestimonialOut,
    FeaturedTestimonialOut,
    OwnerTestimonialOut,
    TestimonialOut,
    TestimonialSubmitIn,
)
from app.services.testimonial import TestimonialService

public_router = APIRouter(tags=["testimonials"])
owner_router = APIRouter(tags=["my-testimonials"])
admin_router = APIRouter(prefix="/admin", tags=["admin-testimonials"])


# --- Public ----------------------------------------------------------------


#: How many testimonials the home page shows.
FEATURED_LIMIT = 6


@public_router.get("/testimonials/featured", response_model=list[FeaturedTestimonialOut])
def featured_testimonials(db: DbSession) -> list[FeaturedTestimonialOut]:
    """The home page's testimonials: the six best published ones, one per
    listing, each with the listing it is about."""
    featured: list[FeaturedTestimonialOut] = []
    for testimonial in TestimonialRepository(db).featured(FEATURED_LIMIT):
        business, profile = testimonial.business, testimonial.talent_profile
        base = TestimonialOut.model_validate(testimonial).model_dump()
        if business is not None:
            featured.append(
                FeaturedTestimonialOut(
                    **base,
                    subject_kind="business",
                    subject_name=business.name,
                    subject_slug=business.slug,
                )
            )
        elif profile is not None:
            featured.append(
                FeaturedTestimonialOut(
                    **base,
                    subject_kind="talent",
                    subject_name=profile.display_name,
                    subject_slug=profile.slug,
                )
            )
    return featured


@public_router.post(
    "/businesses/{slug}/testimonials",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_testimonial(
    slug: Annotated[str, Path(max_length=200)],
    payload: TestimonialSubmitIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> MessageResponse:
    """Leave praise on an approved listing. Invisible until an administrator
    approves it.

    Answers with a message rather than the stored row: the sender has nothing
    to do with an id, and echoing one back would be the only way this
    endpoint could confirm anything about the board behind it.
    """
    business = BusinessRepository(db).get_by_slug(slug, public_only=True)
    if business is None:
        raise NotFoundError("business.not_public")

    TestimonialService(db, settings).submit(business, payload, client_ip=client_ip)
    return MessageResponse(message=translate("testimonial.pending"))


@public_router.post(
    "/talent/{slug}/testimonials",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_talent_testimonial(
    slug: Annotated[str, Path(max_length=200)],
    payload: TestimonialSubmitIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> MessageResponse:
    """The same, on an approved service profile.

    A service only: a job application is someone asking for work, and praise
    from anonymous strangers on it is not what the owners asked for.
    """
    profile = TalentRepository(db).get_by_slug(slug, public_only=True)
    if profile is None or profile.kind != TalentKind.SERVICE:
        raise NotFoundError("talent.not_public")

    TestimonialService(db, settings).submit(profile, payload, client_ip=client_ip)
    return MessageResponse(message=translate("testimonial.pending"))


# --- Owner -----------------------------------------------------------------


@owner_router.get(
    "/businesses/{business_id}/testimonials", response_model=list[OwnerTestimonialOut]
)
def list_my_testimonials(
    business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> list[OwnerTestimonialOut]:
    """What is published on the listing -- what any visitor reads.

    Nothing still awaiting review, or refused: an owner has nothing to decide
    about either, and handing them unread text aimed at them is what the
    review exists to prevent.
    """
    return [
        owner_testimonial(entry)
        for entry in TestimonialService(db, settings).public_for(business)
    ]


@owner_router.get("/my/talent/testimonials", response_model=list[OwnerTestimonialOut])
def list_my_talent_testimonials(
    profile: OwnTalentProfile, db: DbSession, settings: AppSettings
) -> list[OwnerTestimonialOut]:
    """The same for the account's service profile."""
    return [
        owner_testimonial(entry)
        for entry in TestimonialService(db, settings).public_for(profile)
    ]


# --- Admin -----------------------------------------------------------------


@admin_router.get("/testimonials", response_model=list[AdminTestimonialOut])
def list_testimonials(
    admin: AdminUser,
    db: DbSession,
    status: Annotated[TestimonialStatus | None, Query()] = None,
) -> list[AdminTestimonialOut]:
    """Every testimonial across the directory, newest first, in any state.
    An optional ``status`` narrows it to one moderation state."""
    entries = TestimonialRepository(db).all_recent(
        statuses=[status] if status is not None else None
    )
    return [admin_testimonial(entry) for entry in entries]


def _any_testimonial(db: DbSession, testimonial_id: uuid.UUID) -> Testimonial:
    testimonial = TestimonialRepository(db).get(testimonial_id)
    if testimonial is None:
        raise NotFoundError("testimonial.not_found")
    return testimonial


@admin_router.post(
    "/testimonials/{testimonial_id}/approve", response_model=AdminTestimonialOut
)
def approve_testimonial(
    testimonial_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> AdminTestimonialOut:
    """Publish it on the listing, and count its stars."""
    testimonial = _any_testimonial(db, testimonial_id)
    return admin_testimonial(TestimonialService(db, settings).approve(testimonial))


@admin_router.post(
    "/testimonials/{testimonial_id}/reject", response_model=AdminTestimonialOut
)
def reject_testimonial(
    testimonial_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> AdminTestimonialOut:
    """Refuse it, or take a published one down.

    Kept rather than deleted so the same text cannot be resubmitted and
    approved by accident; ``remove`` is still there for a real delete.
    """
    testimonial = _any_testimonial(db, testimonial_id)
    return admin_testimonial(TestimonialService(db, settings).reject(testimonial))


@admin_router.delete("/testimonials/{testimonial_id}", response_model=MessageResponse)
def remove_testimonial(
    testimonial_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> MessageResponse:
    """Delete outright."""
    testimonial = _any_testimonial(db, testimonial_id)
    TestimonialService(db, settings).remove(testimonial)
    return MessageResponse(message=translate("testimonial.removed"))
