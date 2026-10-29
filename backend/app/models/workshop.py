"""Workshops run by the platform, and the people who sign up for them.

The owners' request (29 Oct 2026): training for the South's sellers and
people, shown beside the products and articles it relates to. Like an
article, a workshop is written by an administrator only, with a draft and
published switch and an optional category and town it is about; the
product and article pages show the upcoming ones that match.

A sign-up carries a stranger's name and phone number, so like a partner
request it is read by administrators only: no public route reads it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import Currency, WorkshopMode

if TYPE_CHECKING:
    from app.models.taxonomy import Category, Location


class Workshop(Base, TimestampMixin):
    __tablename__ = "workshops"
    __table_args__ = (Index("ix_workshops_published_starts", "is_published", "starts_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trainer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[WorkshopMode] = mapped_column(
        pg_enum(WorkshopMode, "workshop_mode"), nullable=False, default=WorkshopMode.IN_PERSON
    )
    # Where, in person: the venue as written, in a town from the list.
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # No price means free.
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Currency] = mapped_column(
        pg_enum(Currency, "currency"), nullable=False, default=Currency.USD
    )

    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # What it relates to: the product and article pages in this category or
    # town show it. Cleared, not cascaded, when either is deleted.
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[Category | None] = relationship(lazy="joined")
    location: Mapped[Location | None] = relationship(lazy="joined")

    registrations: Mapped[list[WorkshopRegistration]] = relationship(
        back_populates="workshop", cascade="all, delete-orphan", passive_deletes=True
    )


class WorkshopRegistration(Base, TimestampMixin):
    __tablename__ = "workshop_registrations"

    id: Mapped[uuid.UUID] = uuid_pk()
    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)

    workshop: Mapped[Workshop] = relationship(back_populates="registrations")
