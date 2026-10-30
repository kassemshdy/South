"""Development activities announced on the home page.

The owners' ticket (29 Oct 2026): a carousel of announcement photos on the
home page, each opening a page with the details and a way to add it to a
calendar, and the same activities on a page of their own in the menu. Like
a workshop it is written by an administrator only; unlike one it has no
sign-up and no draft step -- an administrator keeps it or archives it, and
an archived activity is gone from every public route.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, uuid_pk


class Activity(Base, TimestampMixin):
    __tablename__ = "activities"
    __table_args__ = (Index("ix_activities_archived_order", "is_archived", "sort_order"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Required before it is shown: the carousel is photographs. It is
    # uploaded after the activity is created, so an activity without one is
    # kept off the public routes rather than refused.
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    image_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)

    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Lower first; ties go to the newest.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
