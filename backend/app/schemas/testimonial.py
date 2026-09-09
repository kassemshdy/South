from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TestimonialStatus
from app.schemas.common import ORMModel


class TestimonialSubmitIn(BaseModel):
    """What a visitor may send.

    No contact details and no rating. A contact field would make this a lead
    form for the sender rather than praise for the listing, and a rating
    would turn owner-selected text into a score -- which is the review system
    this deliberately is not.
    """

    author_name: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=10, max_length=1000)


class TestimonialOut(ORMModel):
    """What a visitor sees. Carries no status and no timestamps beyond the
    date, because a public reader has no business in the moderation state."""

    id: uuid.UUID
    author_name: str
    body: str
    created_at: datetime


class OwnerTestimonialOut(TestimonialOut):
    """The owner's view: adds the state they are being asked to decide."""

    status: TestimonialStatus
    approved_at: datetime | None = None
