from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, uuid_pk


class OtpRequest(Base):
    """A one-time password challenge.

    The code itself is never stored: only a salted hash, so a database leak
    cannot be replayed into account takeovers.
    """

    __tablename__ = "otp_requests"
    __table_args__ = (Index("ix_otp_requests_phone_created", "phone_number", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    request_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RateLimitEvent(Base):
    """One row per rate-limited action.

    Backing the limiter with the database (rather than process memory) means
    limits still hold when the API runs several workers or replicas. The
    RateLimiter protocol lets this be swapped for Redis without touching
    callers.
    """

    __tablename__ = "rate_limit_events"
    __table_args__ = (
        Index("ix_rate_limit_events_lookup", "bucket", "identifier", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
