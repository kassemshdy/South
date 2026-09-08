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

from fastapi import APIRouter, Path, status

from app.api.serializers import owner_testimonial
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession, OwnedBusiness
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.models.testimonial import Testimonial
from app.repositories.business import BusinessRepository
from app.repositories.testimonial import TestimonialRepository
from app.schemas.common import MessageResponse
from app.schemas.testimonial import OwnerTestimonialOut, TestimonialSubmitIn
from app.services.testimonial import TestimonialService

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
    """Every testimonial on the caller's listing, in any state."""
    return [
        owner_testimonial(entry)
        for entry in TestimonialService(db, settings).all_for(business)
    ]


def _owned_testimonial(
    db: DbSession, business: OwnedBusiness, testimonial_id: uuid.UUID
) -> Testimonial:
    testimonial = TestimonialRepository(db).owned(testimonial_id, business.id)
    if testimonial is None:
        # 404 rather than 403: this must not confirm that an id exists on
        # some other listing.
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


@admin_router.delete("/testimonials/{testimonial_id}", response_model=MessageResponse)
def remove_testimonial(
    testimonial_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> MessageResponse:
    """Delete outright. For abuse the owner cannot or will not deal with."""
    testimonial = TestimonialRepository(db).get(testimonial_id)
    if testimonial is None:
        raise NotFoundError("testimonial.not_found")
    TestimonialService(db, settings).remove(testimonial)
    return MessageResponse(message=translate("testimonial.removed"))
