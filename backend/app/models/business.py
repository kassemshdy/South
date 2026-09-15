from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import (
    BusinessStatus,
    Currency,
    ImageKind,
    ModerationActionType,
    OwnerRelation,
    SocialPlatform,
)

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.taxonomy import Category, Location
    from app.models.testimonial import Testimonial
    from app.models.user import User


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

    # --- Producer detail (public) ----------------------------------------
    # A goods producer is described by more than a trade name: the registered
    # establishment name can differ from the name it trades under, and what it
    # actually makes is what a buyer searches for. All three are published —
    # unlike the owner's identity, which lives on User and never is.
    institution_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # When the establishment was founded, or when it started producing. A date
    # rather than a year: a workshop that opened last spring should be able to
    # say so.
    founding_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    production_nature: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Years in this trade, which is not the same as the establishment's age:
    # someone who spent fifteen years at a bakery before opening their own
    # last year has both, and the buyer cares about the fifteen. Published
    # for that reason, alongside the founding date.
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Who is listing this (never published) ---------------------------
    # Owner, manager or employee. A reviewer's question -- is this person
    # entitled to list on behalf of this establishment -- so it reaches the
    # owner and an administrator and stops there, the same boundary the
    # account holder's identity fields keep. Per business rather than per
    # account: one person may own one place and manage another.
    owner_relation: Mapped[OwnerRelation | None] = mapped_column(
        pg_enum(OwnerRelation, "owner_relation"), nullable=True
    )

    # Public contact details — deliberately separate from the owner's login
    # phone, which is never published.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # An owner-recorded introduction, stored as the eleven-character YouTube
    # id rather than the link they pasted: the page composes the embed URL
    # from it, so no owner-supplied string is ever handed to a browser. See
    # ``app.core.urls.youtube_video_id``.
    youtube_video_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    address_text: Mapped[str | None] = mapped_column(String(400), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    maps_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[BusinessStatus] = mapped_column(
        pg_enum(BusinessStatus, "business_status"),
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
    testimonials: Mapped[list[Testimonial]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="Testimonial.created_at.desc()",
    )
    orders: Mapped[list[Order]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="Order.created_at.desc()",
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
        pg_enum(ImageKind, "image_kind"), default=ImageKind.GALLERY, nullable=False
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
        pg_enum(SocialPlatform, "social_platform"), nullable=False
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
        pg_enum(Currency, "currency"), default=Currency.USD, nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The fields below only ever apply to a physical good -- a service or menu
    # item simply leaves them unset, the same way a talent profile leaves
    # fields unset that don't describe its trade.
    good_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufactured_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    net_weight: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Arabic-normalized haystack for the independent products directory,
    # maintained by BusinessItemService the same way Business.search_text is.
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    business: Mapped[Business] = relationship(back_populates="items")
    images: Mapped[list[BusinessItemImage]] = relationship(
        back_populates="item",
        order_by="BusinessItemImage.sort_order",
        cascade="all, delete-orphan",
    )


class BusinessItemImage(Base):
    """Gallery image metadata for a product/service item; bytes live in object storage.

    An item's single ``image_url`` is its card thumbnail (see the existing
    upload-photo endpoint); this table is the additional gallery a buyer opens
    to see more of the actual good, mirroring ``BusinessImage``/``TalentImage``.
    """

    __tablename__ = "business_item_images"
    __table_args__ = (Index("ix_business_item_images_item_sort", "item_id", "sort_order"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped[BusinessItem] = relationship(back_populates="images")


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
        pg_enum(ModerationActionType, "moderation_action_type"), nullable=False
    )
    from_status: Mapped[BusinessStatus | None] = mapped_column(
        pg_enum(BusinessStatus, "business_status"), nullable=True
    )
    to_status: Mapped[BusinessStatus] = mapped_column(
        pg_enum(BusinessStatus, "business_status"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business: Mapped[Business] = relationship(back_populates="moderation_actions")
