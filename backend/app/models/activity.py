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

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import ActivityKind


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
    # Lower first; ties go to the newest. Superseded for the carousel by
    # CarouselSlide.position (the owners' ticket, 31 Oct 2026); kept so old
    # rows keep their place in any list that still reads it.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- The activities redesign (the owners' ticket, 31 Oct 2026) -------
    kind: Mapped[ActivityKind] = mapped_column(
        pg_enum(ActivityKind, "activity_kind"),
        nullable=False,
        default=ActivityKind.ACTIVITY,
        server_default=ActivityKind.ACTIVITY.value,
    )
    # A link out to wherever people sign up (a form, a WhatsApp chat).
    register_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # The button's text; the catalog's own when empty.
    register_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    show_calendar: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class CarouselSlide(Base):
    """One slide of the announcements carousel, on the home page and /activities.

    Either an activity's photograph (``activity_id``) or a custom slide with
    its own image, title and link -- a partner banner, a campaign. One table
    holds the order of both, so the two pages show the same slides in the
    same order. Lower ``position`` first.
    """

    __tablename__ = "carousel_slides"

    id: Mapped[uuid.UUID] = uuid_pk()
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    activity: Mapped[Activity | None] = relationship()
