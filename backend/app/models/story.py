"""Photo stories: the round circles at the top of the home page.

An owner posts a photograph for their shop or their service profile; an
administrator approves it; it is then shown for ``STORY_LIFETIME`` from the
moment of approval and disappears (the owners' decisions, 28 Oct 2026).
Counting from approval rather than upload means a photo that waited in the
queue overnight still gets its full day.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, uuid_pk

STORY_LIFETIME = timedelta(hours=24)

STORY_PENDING = "PENDING_REVIEW"
STORY_APPROVED = "APPROVED"
STORY_REJECTED = "REJECTED"
STORY_STATUSES = (STORY_PENDING, STORY_APPROVED, STORY_REJECTED)


class StoryImage(Base, TimestampMixin):
    __tablename__ = "story_images"
    __table_args__ = (
        # A story belongs to exactly one listing: a shop or a service profile.
        CheckConstraint(
            "(business_id IS NULL) <> (talent_profile_id IS NULL)", name="one_listing"
        ),
        CheckConstraint(
            "status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')", name="known_status"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    talent_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    image_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STORY_PENDING)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
