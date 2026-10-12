from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TestimonialStatus
from app.schemas.common import ORMModel


class TestimonialSubmitIn(BaseModel):
    """What a visitor may send.

    No contact details: a contact field would make this a lead form for the
    sender rather than praise for the listing. The optional star rating is
    the owners' decision; only published testimonials count toward the
    average -- see TestimonialService.
    """

    author_name: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=10, max_length=1000)
    rating: int | None = Field(default=None, ge=1, le=5)


class TestimonialOut(ORMModel):
    """What a visitor sees. Carries no status and no timestamps beyond the
    date, because a public reader has no business in the moderation state."""

    id: uuid.UUID
    author_name: str
    body: str
    rating: int | None = None
    created_at: datetime


class OwnerTestimonialOut(TestimonialOut):
    """Adds the moderation state. An owner is only ever shown published ones,
    but the same shape serves the administrator below."""

    status: TestimonialStatus
    approved_at: datetime | None = None


class AdminTestimonialOut(OwnerTestimonialOut):
    """The platform's view: the moderation state plus the listing each
    testimonial belongs to -- a business or a service profile, exactly one of
    the two -- so an administrator can survey every submission across the
    directory from one place.

    Carries only the listing's public identity (name and slug) -- never the
    owner's, which stays on ``users`` and out of any public-shaped payload."""

    business_id: uuid.UUID | None = None
    business_name: str | None = None
    business_slug: str | None = None
    talent_id: uuid.UUID | None = None
    talent_name: str | None = None
    talent_slug: str | None = None
