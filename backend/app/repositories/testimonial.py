"""Testimonial data access.

Makes no authorization decision, as ever: ``for_business`` returns whatever
statuses it is asked for, and deciding that a visitor may only ever be shown
``APPROVED`` belongs to the service and the public schema.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.business import Business
from app.models.enums import TestimonialStatus
from app.models.talent import TalentProfile
from app.models.testimonial import Testimonial
from app.repositories.base import BaseRepository


class TestimonialRepository(BaseRepository[Testimonial]):
    model = Testimonial

    def for_subject(
        self,
        subject: Business | TalentProfile,
        *,
        statuses: Sequence[TestimonialStatus] | None = None,
    ) -> list[Testimonial]:
        """Newest first, on a business or a service profile.
        ``statuses=None`` means every status."""
        column = (
            Testimonial.business_id
            if isinstance(subject, Business)
            else Testimonial.talent_profile_id
        )
        stmt = select(Testimonial).where(column == subject.id)
        if statuses is not None:
            stmt = stmt.where(Testimonial.status.in_(list(statuses)))
        stmt = stmt.order_by(Testimonial.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def all_recent(
        self, *, statuses: Sequence[TestimonialStatus] | None = None
    ) -> list[Testimonial]:
        """Every testimonial in the directory, newest first, with its business
        eager-loaded so an admin listing needs no per-row query. ``statuses=None``
        means every status. No owner scoping: this is the platform view."""
        stmt = select(Testimonial).options(
            joinedload(Testimonial.business), joinedload(Testimonial.talent_profile)
        )
        if statuses is not None:
            stmt = stmt.where(Testimonial.status.in_(list(statuses)))
        stmt = stmt.order_by(Testimonial.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())
