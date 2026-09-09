"""Service request data access.

No authorization decisions here: ``for_profile`` returns what it is asked
for, and establishing that the caller owns that profile is the dependency's
job -- and an easy one, because a talent profile is one-per-account and
``OwnTalentProfile`` resolves it from the token rather than from the path.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.service_request import ServiceRequest
from app.repositories.base import BaseRepository


class ServiceRequestRepository(BaseRepository[ServiceRequest]):
    model = ServiceRequest

    def for_profile(self, profile_id: uuid.UUID) -> list[ServiceRequest]:
        """Newest first."""
        stmt = (
            select(ServiceRequest)
            .where(ServiceRequest.profile_id == profile_id)
            .order_by(ServiceRequest.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def owned(self, request_id: uuid.UUID, profile_id: uuid.UUID) -> ServiceRequest | None:
        """Scoped by profile id, which is what stops one provider reaching
        another's request by swapping the id in the URL."""
        stmt = select(ServiceRequest).where(
            ServiceRequest.id == request_id, ServiceRequest.profile_id == profile_id
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()
