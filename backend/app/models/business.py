from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk
from app.models.enums import (
    BusinessStatus,
    Currency,
    ImageKind,
    ModerationActionType,
    SocialPlatform,
)

if TYPE_CHECKING:
    from app.models.taxonomy import Category, Location
    from app.models.user import User


def _enum(python_enum: type, name: str) -> SAEnum:
    return SAEnum(
        python_enum, name=name, values_callable=lambda e: [m.value for m in e]
    )


class Business(Base, TimestampMixin):
    """A business listing and its moderation state."""

    __tablename__ = "businesses"
    __table_args__ = (
        Index("ix_businesses_status_created_at", "status", "created_at"),
        Index("ix_businesses_status_approved_at", "status", "approved_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Set only when category is the seeded "other" row (slug "other"); the
    # owner's own words for a category that doesn't fit the fixed list.
    custom_category_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Public contact details — deliberately separate from the owner's login
    # phone, which is never published.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    address_text: Mapped[str | None] = mapped_column(String(400), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    maps_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[BusinessStatus] = mapped_column(
        _enum(BusinessStatus, "business_status"),
        default=BusinessStatus.DRAFT,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Arabic-normalized haystack maintained by BusinessService on every write.
    # Keeping it denormalized lets a trigram index serve substring search.
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    owner: Mapped[User] = relationship(back_populates="businesses", foreign_keys=[owner_id])
    approver: Mapped[User | None] = relationship(foreign_keys=[approved_by])
    category: Mapped[Category | None] = relationship(back_populates="businesses")
    location: Mapped[Location | None] = relationship(back_populates="businesses")

    images: Mapped[list[BusinessImage]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="BusinessImage.sort_order",
    )
    social_links: Mapped[list[BusinessSocialLink]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    items: Mapped[list[BusinessItem]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="BusinessItem.sort_order",
    )
    moderation_actions: Mapped[list[ModerationAction]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="ModerationAction.created_at",
    )

    @property
    def is_public(self) -> bool:
        return self.status is BusinessStatus.APPROVED


class BusinessImage(Base):
    """Metadata for an image; the bytes live in object storage."""

    __tablename__ = "business_images"
    __table_args__ = (
        Index("ix_business_images_business_kind_sort", "business_id", "kind", "sort_order"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[ImageKind] = mapped_column(
        _enum(ImageKind, "image_kind"), default=ImageKind.GALLERY, nullable=False
    )
    caption: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business: Mapped[Business] = relationship(back_populates="images")


class BusinessSocialLink(Base, TimestampMixin):
    __tablename__ = "business_social_links"
    __table_args__ = (
        UniqueConstraint("business_id", "platform", name="uq_business_social_platform"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[SocialPlatform] = mapped_column(
        _enum(SocialPlatform, "social_platform"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    business: Mapped[Business] = relationship(back_populates="social_links")


class BusinessItem(Base, TimestampMixin):
    """A product, service or menu item — one concept, three presentations."""

    __tablename__ = "business_items"
    __table_args__ = (Index("ix_business_items_business_sort", "business_id", "sort_order"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Currency] = mapped_column(
        _enum(Currency, "currency"), default=Currency.USD, nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Arabic-normalized haystack for the independent products directory,
    # maintained by BusinessItemService the same way Business.search_text is.
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    business: Mapped[Business] = relationship(back_populates="items")


class ModerationAction(Base):
    """Append-only audit trail of every moderation decision."""

    __tablename__ = "moderation_actions"

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Null when the actor is the owner (a SUBMIT action).
    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[ModerationActionType] = mapped_column(
        _enum(ModerationActionType, "moderation_action_type"), nullable=False
    )
    from_status: Mapped[BusinessStatus | None] = mapped_column(
        _enum(BusinessStatus, "business_status"), nullable=True
    )
    to_status: Mapped[BusinessStatus] = mapped_column(
        _enum(BusinessStatus, "business_status"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business: Mapped[Business] = relationship(back_populates="moderation_actions")
