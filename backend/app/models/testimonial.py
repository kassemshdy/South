"""Testimonials on a business or a service profile, published by the platform.

A visitor writes praise and an administrator decides whether it appears;
the listing's owner can read what is published but neither approves nor
hides it. That is the owners' decision (round 3): it used to take the
owner's approval as well, which made a testimonial owner-selected praise.

Two things carry over from that design and are still load-bearing:

- the author is not verified -- submission is anonymous, so a testimonial
  is a visitor's word that the platform has read, never a verified review;
- open public reviews in a small region carry real social risk, which is why
  nothing is published without a person having read it first.

Follows the feedback/ticketing slice, which is the existing pattern here for
moderated user-submitted content.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import TestimonialStatus

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.talent import TalentProfile


class Testimonial(Base, TimestampMixin):
    __tablename__ = "testimonials"
    __table_args__ = (
        # The public read is always (this business, approved); the owner's is
        # (this business, any status). One index serves both.
        Index("ix_testimonials_business_status", "business_id", "status"),
        Index("ix_testimonials_talent_profile_id", "talent_profile_id", "status"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_testimonials_rating_range"),
        # About exactly one listing: a business or a service profile.
        CheckConstraint(
            "num_nonnulls(business_id, talent_profile_id) = 1",
            name="ck_testimonials_one_subject",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    talent_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=True
    )
    # Whatever the visitor typed. Not a user id: submission is anonymous, so
    # there is no account behind this and the column must not imply one.
    author_name: Mapped[str] = mapped_column(String(80), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # One to five stars, optional, asked for by the owners beside the text.
    # Counted into the business's average only once published -- see
    # TestimonialService._refresh_rating.
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[TestimonialStatus] = mapped_column(
        pg_enum(TestimonialStatus, "testimonial_status"),
        nullable=False,
        default=TestimonialStatus.PENDING_REVIEW,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    business: Mapped[Business | None] = relationship(back_populates="testimonials")
    talent_profile: Mapped[TalentProfile | None] = relationship(
        back_populates="testimonials"
    )
