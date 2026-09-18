"""Testimonials, cleared by the platform and then chosen by the owner.

A visitor writes praise; an administrator checks it is not abuse, and the
owner then decides whether it appears. That trade is
deliberate: open public reviews on a community directory in a small region
carry real social risk -- one angry review about a village shop is a
different thing from one about a chain -- and a moderation load nobody has
volunteered for.

**This is not a review system and must not be presented as one.** An owner
approves what is displayed, so a testimonial is *selected* praise, never
independent evidence. Two consequences follow, and both are load-bearing:

- the author is not verified, because verifying them would imply an
  independence the feature does not have -- an owner can write and approve
  their own testimonial whatever the auth model, so verification buys the
  appearance of trust rather than trust;
- every surface that renders one has to say it is owner-selected.

Follows the feedback/ticketing slice, which is the existing pattern here for
moderated user-submitted content.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import TestimonialStatus

if TYPE_CHECKING:
    from app.models.business import Business


class Testimonial(Base, TimestampMixin):
    __tablename__ = "testimonials"
    __table_args__ = (
        # The public read is always (this business, approved); the owner's is
        # (this business, any status). One index serves both.
        Index("ix_testimonials_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Whatever the visitor typed. Not a user id: submission is anonymous, so
    # there is no account behind this and the column must not imply one.
    author_name: Mapped[str] = mapped_column(String(80), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TestimonialStatus] = mapped_column(
        pg_enum(TestimonialStatus, "testimonial_status"),
        nullable=False,
        default=TestimonialStatus.PENDING_REVIEW,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    business: Mapped[Business] = relationship(back_populates="testimonials")
