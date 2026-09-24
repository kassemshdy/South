"""Applications that arrived for a phone number that already has an account."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, pg_enum, uuid_pk
from app.models.enums import ApplicationKind


class DiscardedApplication(Base):
    """An application the public form answered but did not act on.

    The registration routes still answer a number that already has an
    account with the same sentence as any other application, and still
    create nothing on that account -- both of those are what stop the form
    from being a way to ask which numbers are registered, or to put a listing
    inside a stranger's dashboard. What changed, at the CEO's request, is
    that the application is no longer thrown away: it is kept here, where
    only an administrator can read it, so a real owner applying a second
    time is not silently lost.

    Three things are deliberately absent. The ID scan is never stored -- a
    document attached to somebody else's number is exactly what the
    registration rules refuse to keep. Nothing links this row to a listing.
    And the caller's address is not recorded; the rate limiter already has
    what it needs.
    """

    __tablename__ = "discarded_applications"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[ApplicationKind] = mapped_column(
        pg_enum(ApplicationKind, "application_kind"), nullable=False
    )
    login_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # The account that number already belongs to. Null once that account is
    # deleted; the application itself stays readable.
    existing_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # What the applicant sent, minus the captcha token: identity and the
    # listing as typed. Admin-only, like the identity it carries.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
