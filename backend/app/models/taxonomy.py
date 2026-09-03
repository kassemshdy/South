from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk
from app.models.enums import LocationType

if TYPE_CHECKING:
    from app.models.business import Business


class Category(Base, TimestampMixin):
    """Admin-managed business category. Never hardcoded in the frontend."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    businesses: Mapped[list[Business]] = relationship(back_populates="category")


class Location(Base, TimestampMixin):
    """Geographic node in a governorate → district → town tree."""

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    type: Mapped[LocationType] = mapped_column(
        SAEnum(
            LocationType,
            name="location_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    parent: Mapped[Location | None] = relationship(
        remote_side="Location.id", back_populates="children"
    )
    children: Mapped[list[Location]] = relationship(back_populates="parent")
    businesses: Mapped[list[Business]] = relationship(back_populates="location")

