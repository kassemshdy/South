"""Testimonials: a visitor submits, the owner decides, an admin can remove.

Three audiences, three routers, and the split is the disclosure boundary:

- the public route only ever *writes*. Reading a testimonial publicly happens
  through the business profile, which is served approved-only;
- the owner routes are scoped by ``OwnedBusiness`` and then again by business
  id inside the repository, so an id swapped in the URL reaches nothing;
- removal is an administrator's, because the owner controls display while the
  platform keeps the last word on abuse.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.serializers import admin_testimonial, owner_testimonial
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession, OwnedBusiness
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.models.enums import TestimonialStatus
from app.models.testimonial import Testimonial
from app.repositories.business import BusinessRepository
from app.repositories.testimonial import TestimonialRepository
from app.schemas.common import MessageResponse
from app.schemas.testimonial import (
    AdminTestimonialOut,
    OwnerTestimonialOut,
    TestimonialSubmitIn,
)
from app.services.testimonial import OWNER_VISIBLE_STATUSES, TestimonialService

public_router = APIRouter(tags=["testimonials"])
owner_router = APIRouter(tags=["my-testimonials"])
admin_router = APIRouter(prefix="/admin", tags=["admin-testimonials"])


# --- Public ----------------------------------------------------------------


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
    """Leave praise on an approved listing. Invisible until the owner agrees.

    Answers with a message rather than the stored row: the sender has nothing
    to do with an id, and echoing one back would be the only way this
    endpoint could confirm anything about the board behind it.
    """
    business = BusinessRepository(db).get_by_slug(slug, public_only=True)
    if business is None:
        raise NotFoundError("business.not_public")

    TestimonialService(db, settings).submit(business, payload, client_ip=client_ip)
    return MessageResponse(message=translate("testimonial.pending"))


# --- Owner -----------------------------------------------------------------


@owner_router.get(
    "/businesses/{business_id}/testimonials", response_model=list[OwnerTestimonialOut]
)
def list_my_testimonials(
    business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> list[OwnerTestimonialOut]:
    """Every testimonial the platform has cleared, in any owner state.

    Not every testimonial on the listing: text still awaiting review, or
    refused, is not shown here. An owner asked to moderate abuse has already
    read it, which is what the platform gate exists to avoid.
    """
    return [
        owner_testimonial(entry)
        for entry in TestimonialService(db, settings).owner_for(business)
    ]


def _owned_testimonial(
    db: DbSession, business: OwnedBusiness, testimonial_id: uuid.UUID
) -> Testimonial:
    testimonial = TestimonialRepository(db).owned(
        testimonial_id, business.id, statuses=list(OWNER_VISIBLE_STATUSES)
    )
    if testimonial is None:
        # 404 rather than 403: this must not confirm that an id exists on
        # some other listing — nor that one exists here awaiting review or
        # already refused, which an owner has no business acting on.
        raise NotFoundError("testimonial.not_found")
    return testimonial


@owner_router.post(
    "/businesses/{business_id}/testimonials/{testimonial_id}/approve",
    response_model=OwnerTestimonialOut,
)
def approve_testimonial(
    testimonial_id: uuid.UUID,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
) -> OwnerTestimonialOut:
    """Publish it. The only route by which a testimonial becomes visible."""
    testimonial = _owned_testimonial(db, business, testimonial_id)
    return owner_testimonial(TestimonialService(db, settings).approve(testimonial))


@owner_router.post(
    "/businesses/{business_id}/testimonials/{testimonial_id}/hide",
    response_model=OwnerTestimonialOut,
)
def hide_testimonial(
    testimonial_id: uuid.UUID,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
) -> OwnerTestimonialOut:
    """Take it down again, without deleting it."""
    testimonial = _owned_testimonial(db, business, testimonial_id)
    return owner_testimonial(TestimonialService(db, settings).hide(testimonial))


# --- Admin -----------------------------------------------------------------


@admin_router.get("/testimonials", response_model=list[AdminTestimonialOut])
def list_testimonials(
    admin: AdminUser,
    db: DbSession,
    status: Annotated[TestimonialStatus | None, Query()] = None,
) -> list[AdminTestimonialOut]:
    """Every testimonial across the directory, newest first, in any state.

    The owner controls what is *displayed*; this is the platform keeping sight
    of what was *submitted* -- so a pending or hidden testimonial an owner has
    not acted on is still visible here, which is the whole point of the view.
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
    "/testimonials/{testimonial_id}/clear", response_model=AdminTestimonialOut
)
def clear_testimonial(
    testimonial_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> AdminTestimonialOut:
    """Pass the platform gate: hand it to the owner to decide on.

    Not a publish. The owner still chooses whether it appears, which is what
    keeps a testimonial selected praise rather than a review.
    """
    testimonial = _any_testimonial(db, testimonial_id)
    return admin_testimonial(TestimonialService(db, settings).clear(testimonial))


@admin_router.post(
    "/testimonials/{testimonial_id}/reject", response_model=AdminTestimonialOut
)
def reject_testimonial(
    testimonial_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> AdminTestimonialOut:
    """Refuse it. It never reaches the owner or the listing.

    Kept rather than deleted so the same text cannot be resubmitted and
    cleared by accident; ``remove`` is still there for a real delete.
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
    """Delete outright. For abuse the owner cannot or will not deal with."""
    testimonial = _any_testimonial(db, testimonial_id)
    TestimonialService(db, settings).remove(testimonial)
    return MessageResponse(message=translate("testimonial.removed"))
