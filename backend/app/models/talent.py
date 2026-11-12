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
    ContactChannel,
    Currency,
    EducationLevel,
    EmployerRequestStatus,
    EmploymentType,
    ImageKind,
    LanguageProficiency,
    ModerationActionType,
    SocialPlatform,
    TalentAvailability,
    TalentKind,
    TalentWorkType,
    WorkMode,
)

if TYPE_CHECKING:
    from app.models.service_request import ServiceRequest
    from app.models.taxonomy import Location
    from app.models.testimonial import Testimonial
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
    # The trade in the person's own words, one level below the chosen skill:
    # a teacher picks "teacher" from the taxonomy and names the subject they
    # teach here. Distinct from ``custom_skill_text``, which stands in for the
    # skill name itself when the skill is "other", and from
    # ``specialization``, which is what a degree was in.
    skill_specialty: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Where the owner pinned themselves on the map -- public, shown on the
    # profile page and used for nearest-first, as a business's pin is. A pin
    # on the town is enough.
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    # The name shown publicly, which need not be the account's display_name:
    # someone may work under a professional name.
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Public contact details — deliberately separate from the account's login
    # phone, which is never published.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Whether the numbers above are shown to visitors. The owners asked that
    # everyone listing give a number, and choose whether the public sees it:
    # hidden, it still reaches the team and the dashboard, and a visitor
    # contacts the owner through a message on the site instead.
    phone_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Which of the above the page leads with. See ContactChannel: it orders
    # the contact block rather than narrowing it.
    preferred_contact: Mapped[ContactChannel | None] = mapped_column(
        pg_enum(ContactChannel, "contact_channel"), nullable=True
    )

    # An owner-recorded introduction, stored as the eleven-character YouTube
    # id rather than the link they pasted: the page composes the embed URL
    # from it, so no owner-supplied string is ever handed to a browser. See
    # ``app.core.urls.youtube_video_id``.
    youtube_video_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # The wide image across the top of the profile page, as a business has
    # (the owners' ticket, 29 Oct 2026). Required before review, like the photo.
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- Professional detail (published) ---------------------------------
    # These describe the work, so they belong on the public profile —
    # serialized from TalentDetailOut down.
    highest_degree: Mapped[str | None] = mapped_column(String(160), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    university: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Years spent earning that degree/training, not years worked -- see
    # years_experience above for the work-history count.
    education_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graduation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    study_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    professional_training: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    services_offered: Mapped[str | None] = mapped_column(Text, nullable=True)
    hobbies: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        pg_enum(EmploymentType, "employment_type"), nullable=True
    )
    # Derived from work_mode whenever that is set (see TalentService), and
    # kept so nothing that reads it changes.
    remote_capable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Remotely, in person or both. Required of a service at review; a job
    # application is not asked.
    work_mode: Mapped[WorkMode | None] = mapped_column(
        pg_enum(WorkMode, "work_mode"), nullable=True
    )
    # The stars on this profile's published testimonials, as a business
    # carries them. Written only by TestimonialService.
    rating_average: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    rating_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Identity — legal name, birth year, gender, marital status and the two
    # civil-record places — lives on :class:`~app.models.user.User`, not
    # here: it describes the person behind the account, who may own
    # businesses too, so one account holds exactly one copy of it.

    # Services or job applications: the directory this profile is listed in,
    # chosen by its owner. Every profile from before the split is a service,
    # which is what the single directory offered.
    kind: Mapped[TalentKind] = mapped_column(
        pg_enum(TalentKind, "talent_kind"),
        nullable=False,
        default=TalentKind.SERVICE,
        server_default=TalentKind.SERVICE.value,
        index=True,
    )

    # --- Job seekers (kind JOB_SEEKER) ----------------------------------
    # The job asked for, in the person's words: the card's subtitle.
    desired_title: Mapped[str | None] = mapped_column(String(60), nullable=True)
    availability: Mapped[TalentAvailability] = mapped_column(
        pg_enum(TalentAvailability, "talent_availability"),
        nullable=False,
        default=TalentAvailability.NOW,
        server_default=TalentAvailability.NOW.value,
    )
    # The highest level reached, for the directory's education filter.
    education_level: Mapped[EducationLevel | None] = mapped_column(
        pg_enum(EducationLevel, "education_level"), nullable=True
    )
    # With ``photo_hidden`` on, the photo is shown to nobody but staff: the
    # public sees initials, and no public payload or URL may carry it.
    photo_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # A CV is private storage (``PRIVATE_MEDIA_FOLDERS``); ``cv_public`` only
    # decides whether the public page offers the download.
    cv_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cv_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # A private note to the team, never published in any public schema.
    team_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Last time the person said they were still looking; drives the stale
    # filter. Null means never asked.
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    # Optional, and published: the person chose to list them, the same as a
    # shop's. The CEO's answer on adding them was "optional".
    social_links: Mapped[list[TalentSocialLink]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentSocialLink.platform",
    )
    work_types: Mapped[list[TalentWorkTypeRow]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    work_areas: Mapped[list[TalentWorkArea]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    # A service provider's services, each with its own price (the services
    # redesign, 3 Nov 2026). ``services_offered`` stays as free text for
    # anything that is not a priced line.
    service_offers: Mapped[list[TalentServiceOffer]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentServiceOffer.sort_order",
    )
    # Questions a visitor would ask, answered by the provider (services
    # redesign, 3 Nov 2026).
    faqs: Mapped[list[TalentFaq]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentFaq.sort_order",
    )
    work_videos: Mapped[list[TalentVideo]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentVideo.sort_order",
    )
    experiences: Mapped[list[TalentExperience]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentExperience.sort_order",
    )
    education: Mapped[list[TalentEducation]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentEducation.sort_order",
    )
    courses: Mapped[list[TalentCourse]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TalentCourse.sort_order",
    )
    employer_requests: Mapped[list[EmployerRequest]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="EmployerRequest.created_at.desc()",
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
    testimonials: Mapped[list[Testimonial]] = relationship(
        back_populates="talent_profile",
        cascade="all, delete-orphan",
        order_by="Testimonial.created_at.desc()",
    )

    @property
    def is_public(self) -> bool:
        return self.status is BusinessStatus.APPROVED

    @property
    def public_photo_url(self) -> str | None:
        """The photo a visitor may see: none when the person hid it. Every
        public payload, page tag and sitemap reads the photo through here."""
        return None if self.photo_hidden else self.photo_url


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


class TalentWorkTypeRow(Base):
    """One kind of work a job seeker will take (several allowed)."""

    __tablename__ = "talent_work_types"
    __table_args__ = (UniqueConstraint("profile_id", "work_type", name="uq_talent_work_type"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_type: Mapped[TalentWorkType] = mapped_column(
        pg_enum(TalentWorkType, "talent_work_type"), nullable=False
    )

    profile: Mapped[TalentProfile] = relationship(back_populates="work_types")


class TalentWorkArea(Base):
    """A town or district a job seeker can work in."""

    __tablename__ = "talent_work_areas"
    __table_args__ = (UniqueConstraint("profile_id", "location_id", name="uq_talent_work_area"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    profile: Mapped[TalentProfile] = relationship(back_populates="work_areas")
    location: Mapped[Location] = relationship()


class TalentExperience(Base):
    """One job in a person's history; the profile renders them as a timeline."""

    __tablename__ = "talent_experiences"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    employer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    town: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # True means "until now"; ``end_date`` is then ignored.
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="experiences")


class TalentEducation(Base):
    """One degree or qualification."""

    __tablename__ = "talent_education"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    degree: Mapped[str | None] = mapped_column(String(160), nullable=True)
    field: Mapped[str | None] = mapped_column(String(160), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(200), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="education")


class TalentServiceOffer(Base):
    """One service a provider offers, with its price.

    A price is optional, a single figure (``price_to`` empty) or a range;
    ``price_unit`` is the provider's own words for what it is per ("per
    hour", "per session"). Public: it is what a visitor compares.
    """

    __tablename__ = "talent_service_offers"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price_from: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_to: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Currency] = mapped_column(
        pg_enum(Currency, "currency"), default=Currency.USD, nullable=False
    )
    price_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # A photo of the service, shown like a product card (12 Nov 2026).
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    profile: Mapped[TalentProfile] = relationship(back_populates="service_offers")


class TalentFaq(Base):
    """One question and its answer on a provider's profile. Public."""

    __tablename__ = "talent_faqs"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(String(200), nullable=False)
    answer: Mapped[str] = mapped_column(String(1000), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="faqs")


class TalentVideo(Base):
    """A link to a video of a services provider's work (12 Nov 2026).

    Only the platform and a key of a pinned shape are stored; the link and
    the embed address are rebuilt from them (``app.core.work_videos``).
    """

    __tablename__ = "talent_videos"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="work_videos")


class TalentCourse(Base):
    """A course or training the person completed."""

    __tablename__ = "talent_courses"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="courses")


class EmployerRequest(Base):
    """An employer's contact form for a candidate, kept as the admin's log.

    Private: the employer's details are theirs, and the log also gives the
    platform its count of placements (status ``HIRED``).
    """

    __tablename__ = "employer_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EmployerRequestStatus] = mapped_column(
        pg_enum(EmployerRequestStatus, "employer_request_status"),
        nullable=False,
        default=EmployerRequestStatus.NEW,
        server_default=EmployerRequestStatus.NEW.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped[TalentProfile] = relationship(back_populates="employer_requests")


class TalentSocialLink(Base):
    """One of the person's social accounts; one row per platform.

    The same shape as ``BusinessSocialLink`` and normalised by the same
    function, so a link typed as a bare handle is stored as a full URL.
    """

    __tablename__ = "talent_social_links"
    __table_args__ = (
        UniqueConstraint("profile_id", "platform", name="uq_talent_social_platform"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[SocialPlatform] = mapped_column(
        pg_enum(SocialPlatform, "social_platform"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="social_links")


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
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])
