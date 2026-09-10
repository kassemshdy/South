"""Talent profiles: an individual's public listing, moderated like a business.

A talent profile is deliberately *not* a Business. A business is an entity an
owner can hold several of; a talent profile is the person themselves, so it is
one-per-account (``owner_id`` is unique) and carries no branch, address or
opening hours. What it does share with a business is the moderation lifecycle —
the same ``BusinessStatus`` values and the same "approved-only is public" rule —
so :class:`~app.services.talent_moderation.TalentModerationService` can mirror
the business one transition for transition.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import (
    BusinessStatus,
    ImageKind,
    LanguageProficiency,
    ModerationActionType,
)

if TYPE_CHECKING:
    from app.models.service_request import ServiceRequest
    from app.models.taxonomy import Location
    from app.models.user import User


class TalentSkill(Base, TimestampMixin):
    """Admin-managed skill taxonomy — the talent equivalent of Category.

    Kept separate from ``categories`` rather than reused: a grocery is a kind of
    shop, not a thing a person can be hired for, and mixing the two would make
    both filter lists wrong.
    """

    __tablename__ = "talent_skills"

    id: Mapped[uuid.UUID] = uuid_pk()
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    profiles: Mapped[list[TalentProfile]] = relationship(back_populates="skill")


class TalentProfile(Base, TimestampMixin):
    """One person's public profile and its moderation state."""

    __tablename__ = "talent_profiles"
    __table_args__ = (
        Index("ix_talent_profiles_status_created_at", "status", "created_at"),
        Index("ix_talent_profiles_status_approved_at", "status", "approved_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # Unique, not merely indexed: one profile per account. A person is not a
    # portfolio of personas, and the dashboard's "my profile" route depends on
    # there being exactly one row to resolve.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("talent_skills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Set only when skill is the seeded "other" row (slug "other"); the
    # person's own words for work that doesn't fit the fixed list.
    custom_skill_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # The name shown publicly, which need not be the account's display_name:
    # someone may work under a professional name.
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    headline: Mapped[str | None] = mapped_column(String(300), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Public contact details — deliberately separate from the account's login
    # phone, which is never published.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- Professional detail (published) ---------------------------------
    # These describe the work, so they belong on the public profile —
    # serialized from TalentDetailOut down.
    highest_degree: Mapped[str | None] = mapped_column(String(160), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    university: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    services_offered: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Identity — legal name, birth year, gender, marital status and the two
    # civil-record places — lives on :class:`~app.models.user.User`, not
    # here: it describes the person behind the account, who may own
    # businesses too, so one account holds exactly one copy of it.

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

    # Arabic-normalized haystack maintained by TalentService on every write,
    # same as Business.search_text.
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    owner: Mapped[User] = relationship(back_populates="talent_profile", foreign_keys=[owner_id])
    approver: Mapped[User | None] = relationship(foreign_keys=[approved_by])
    skill: Mapped[TalentSkill | None] = relationship(back_populates="profiles")
    location: Mapped[Location | None] = relationship(back_populates="talent_profiles")

    images: Mapped[list[TalentImage]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentImage.sort_order",
    )
    languages: Mapped[list[TalentLanguage]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentLanguage.sort_order",
    )
    moderation_actions: Mapped[list[TalentModerationAction]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentModerationAction.created_at",
    )
    service_requests: Mapped[list[ServiceRequest]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ServiceRequest.created_at.desc()",
    )

    @property
    def is_public(self) -> bool:
        return self.status is BusinessStatus.APPROVED


class TalentLanguage(Base):
    """A language the person works in, with how well they speak it.

    A child table rather than a text column because "languages and level of
    fluency" is two values per row — the same shape TalentImage and
    SocialLink already use — and the directory will eventually want to
    filter on the pair.
    """

    __tablename__ = "talent_languages"
    __table_args__ = (Index("ix_talent_languages_profile_sort", "profile_id", "sort_order"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    proficiency: Mapped[LanguageProficiency] = mapped_column(
        pg_enum(LanguageProficiency, "language_proficiency"),
        default=LanguageProficiency.GOOD,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="languages")


class TalentImage(Base):
    """Portfolio image metadata; the bytes live in object storage."""

    __tablename__ = "talent_images"
    __table_args__ = (
        Index("ix_talent_images_profile_kind_sort", "profile_id", "kind", "sort_order"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
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

    profile: Mapped[TalentProfile] = relationship(back_populates="images")


class TalentModerationAction(Base):
    """Append-only audit trail of every talent moderation decision."""

    __tablename__ = "talent_moderation_actions"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Null when the actor is the profile's owner (a SUBMIT action).
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

    profile: Mapped[TalentProfile] = relationship(back_populates="moderation_actions")
