"""Testimonial data access.

Makes no authorization decision, as ever: ``for_business`` returns whatever
statuses it is asked for, and deciding that a visitor may only ever be shown
``APPROVED`` belongs to the service and the public schema.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.enums import TestimonialStatus
from app.models.testimonial import Testimonial
from app.repositories.base import BaseRepository


class TestimonialRepository(BaseRepository[Testimonial]):
    model = Testimonial

    def for_business(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[TestimonialStatus] | None = None,
    ) -> list[Testimonial]:
        """Newest first. ``statuses=None`` means every status."""
        stmt = select(Testimonial).where(Testimonial.business_id == business_id)
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
        stmt = select(Testimonial).options(joinedload(Testimonial.business))
        if statuses is not None:
            stmt = stmt.where(Testimonial.status.in_(list(statuses)))
        stmt = stmt.order_by(Testimonial.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def owned(
        self, testimonial_id: uuid.UUID, business_id: uuid.UUID
    ) -> Testimonial | None:
        """Scoped by business id, which is what stops an owner reaching
        another listing's testimonial by swapping the id in the URL."""
        return self.db.execute(
            select(Testimonial).where(
                Testimonial.id == testimonial_id,
                Testimonial.business_id == business_id,
            )
        ).scalar_one_or_none()

    def count_approved(self, business_id: uuid.UUID) -> int:
        return len(
            self.for_business(business_id, statuses=[TestimonialStatus.APPROVED])
        )
