from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, uuid_pk


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


class PhoneCode(Base):
    """A one-time code sent by SMS to prove someone holds a phone number.

    Used to sign up and to replace a forgotten password (the owners'
    decision, 9 Nov 2026). Only a keyed hash of the code is stored, so the
    database -- and the backups made of it -- never hold a usable code. A
    row is good for ``PHONE_CODE_TTL`` and ``PHONE_CODE_ATTEMPTS`` guesses,
    then it is dead; rows past their time are deleted as new ones are made.
    """

    __tablename__ = "phone_codes"
    __table_args__ = (Index("ix_phone_codes_phone_created", "phone", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
