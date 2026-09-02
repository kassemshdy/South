from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.auth import OtpRequest
from app.repositories.base import BaseRepository


class OtpRepository(BaseRepository[OtpRequest]):
    model = OtpRequest

    def latest_active_for_phone(self, phone_number: str) -> OtpRequest | None:
        """Most recent unconsumed, unexpired challenge for this number."""
        return self.db.execute(
            select(OtpRequest)
            .where(
                OtpRequest.phone_number == phone_number,
                OtpRequest.consumed_at.is_(None),
                OtpRequest.expires_at > datetime.now(UTC),
            )
            .order_by(OtpRequest.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def invalidate_active_for_phone(self, phone_number: str) -> None:
        """Consume outstanding challenges so only the newest code works."""
        now = datetime.now(UTC)
        requests = (
            self.db.execute(
                select(OtpRequest).where(
                    OtpRequest.phone_number == phone_number,
                    OtpRequest.consumed_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        for request in requests:
            request.consumed_at = now
        self.db.flush()
