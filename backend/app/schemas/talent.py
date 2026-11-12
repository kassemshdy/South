from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from app.core.i18n import translate
from app.core.phone import normalize_optional_phone
from app.core.pins import check_pin
from app.models.enums import (
    BusinessStatus,
    ContactChannel,
    Currency,
    EducationLevel,
    EmployerRequestStatus,
    EmploymentType,
    ImageKind,
    LanguageProficiency,
    TalentAvailability,
    TalentKind,
    TalentWorkType,
    WorkMode,
)
from app.schemas.business import SocialLinkIn, SocialLinkOut
from app.schemas.common import ORMModel
from app.schemas.taxonomy import LocationOut
from app.schemas.testimonial import TestimonialOut
from app.services.images import thumbnail_url

OptionalPhone = Annotated[str | None, Field(default=None, max_length=25)]


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class TalentSkillOut(ORMModel):
    id: uuid.UUID
    name_ar: str
    slug: str
    icon: str | None = None
    sort_order: int
    is_active: bool
    talent_count: int = 0
    # The services directory and the jobs directory filter by the same
    # skills; each counts only its own kind.
    service_count: int = 0
    job_count: int = 0


class TalentSkillIn(BaseModel):
    name_ar: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int = 0
    is_active: bool = True


class TalentSkillUpdateIn(BaseModel):
    name_ar: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int | None = None
    is_active: bool | None = None


class TalentImageOut(ORMModel):
    id: uuid.UUID
    url: str
    kind: ImageKind
    caption: str | None = None
    sort_order: int
    width: int | None = None
    height: int | None = None


class TalentSummaryOut(ORMModel):
    """Card-sized payload used by the directory and search results."""

    id: uuid.UUID
    display_name: str
    slug: str
    # Which directory it is listed in: services, or job applications.
    kind: TalentKind = TalentKind.SERVICE
    photo_url: str | None = None
    # The wide image across the top of the profile page (29 Oct 2026).
    cover_url: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    years_experience: int | None = None
    skill: TalentSkillOut | None = None
    # The person's own words, shown instead of the literal "Other" skill name.
    custom_skill_text: str | None = None
    # One level below the skill and in their own words, which is what makes a
    # card worth reading: the trade narrowed to what this person actually does.
    skill_specialty: str | None = None
    # Remotely, in person or both: on the card because it is filtered on.
    work_mode: WorkMode | None = None
    # The stars on the published testimonials, as a business card shows them.
    rating_average: float | None = None
    rating_count: int = 0
    location: LocationOut | None = None
    # Where the owner was displaced from, only when they chose to show it
    # (User.published_displacement) -- the one identity value a public
    # payload carries, and test_identity.py pins that it needs the opt-in.
    displaced_from: str | None = None
    created_at: datetime
    # When the profile last changed: "last updated" on a candidate's page.
    updated_at: datetime | None = None

    # --- Job seekers (the candidate directory, 3 Nov 2026) ---------------
    # The job asked for: the card's subtitle.
    desired_title: str | None = None
    availability: TalentAvailability = TalentAvailability.NOW
    education_level: EducationLevel | None = None
    # A CV the public page may offer for download. The file itself is never
    # in a payload; it is fetched from /talent/{slug}/cv.
    has_cv: bool = False
    # Approved with an identity document on file: the verified-ID badge.
    id_verified: bool = False
    # The taxonomy skill and the person's own extras, for the card's chips.
    skill_tags: list[str] = Field(default_factory=list)
    work_types: list[TalentWorkType] = Field(default_factory=list)
    # Services: the lowest price among the priced services, for the card's
    # "from" line. Null when nothing is priced.
    starting_price: Decimal | None = None
    starting_price_currency: Currency | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_thumb_url(self) -> str | None:
        return thumbnail_url(self.photo_url)


class TalentLanguageOut(ORMModel):
    id: uuid.UUID
    name: str
    proficiency: LanguageProficiency
    sort_order: int


class TalentExperienceOut(ORMModel):
    id: uuid.UUID
    title: str
    employer: str | None = None
    town: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None


class TalentServiceOfferOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    currency: Currency = Currency.USD
    price_unit: str | None = None
    image_url: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_thumb_url(self) -> str | None:
        return thumbnail_url(self.image_url)


class TalentVideoOut(BaseModel):
    """A video of the provider's work, rebuilt from its platform and key."""

    platform: str
    url: str
    embed_url: str


class TalentFaqOut(ORMModel):
    id: uuid.UUID
    question: str
    answer: str


class TalentEducationOut(ORMModel):
    id: uuid.UUID
    degree: str | None = None
    field: str | None = None
    institution: str | None = None
    graduation_year: int | None = None


class TalentCourseOut(ORMModel):
    id: uuid.UUID
    name: str
    issuer: str | None = None
    year: int | None = None


class TalentDetailOut(TalentSummaryOut):
    bio: str | None = None
    email: str | None = None
    website: str | None = None
    # Which of the contact details above the page leads with. Never narrows
    # what is shown — see ContactChannel.
    preferred_contact: ContactChannel | None = None
    # The person's introduction video, as a YouTube id. An id rather than a
    # URL so the client composes the embed itself and never renders a string
    # the profile's owner typed — see app.core.urls.youtube_video_id.
    youtube_video_id: str | None = None
    # The owner's own pin, published on the profile page's map.
    latitude: float | None = None
    longitude: float | None = None
    images: list[TalentImageOut] = Field(default_factory=list)
    approved_at: datetime | None = None
    # Published ones only -- see talent_detail.
    testimonials: list[TestimonialOut] = Field(default_factory=list)

    # Professional detail: what the person can do, which is the whole point
    # of publishing a profile.
    highest_degree: str | None = None
    specialization: str | None = None
    university: str | None = None
    education_years: int | None = None
    graduation_date: date | None = None
    study_focus: str | None = None
    experience: str | None = None
    professional_training: str | None = None
    skills_text: str | None = None
    services_offered: str | None = None
    hobbies: str | None = None
    employment_type: EmploymentType | None = None
    remote_capable: bool = False
    languages: list[TalentLanguageOut] = Field(default_factory=list)
    social_links: list[SocialLinkOut] = Field(default_factory=list)

    # Job seekers: where they can work and their history, newest first.
    work_areas: list[LocationOut] = Field(default_factory=list)
    experiences: list[TalentExperienceOut] = Field(default_factory=list)
    service_offers: list[TalentServiceOfferOut] = Field(default_factory=list)
    faqs: list[TalentFaqOut] = Field(default_factory=list)
    work_videos: list[TalentVideoOut] = Field(default_factory=list)
    education: list[TalentEducationOut] = Field(default_factory=list)
    courses: list[TalentCourseOut] = Field(default_factory=list)


class OwnerTalentOut(TalentDetailOut):
    """Adds the moderation state only the owner (and administrators) see.

    Anything added below is invisible to an anonymous visitor; anything added
    above is published. The owner's identity is not here at all — it belongs
    to the account, not the profile, and is read through ``UserOut``.
    """

    # The owner's own numbers are always above, whatever this says; it is
    # whether visitors see them.
    phone_public: bool = True
    # The owner's own choices, which the public payload above already obeys.
    photo_hidden: bool = False
    cv_public: bool = True
    # A note to the team: the owner and staff only, never public.
    team_message: str | None = None
    status: BusinessStatus
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    updated_at: datetime


class TalentLanguageIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    proficiency: LanguageProficiency = LanguageProficiency.GOOD

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError(translate("talent.language_name_required"))
        return cleaned


class TalentExperienceIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    employer: str | None = Field(default=None, max_length=160)
    town: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=600)

    @field_validator("title", "employer", "town")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TalentServiceOfferIn(BaseModel):
    # An offer already saved keeps its id, so its photo survives an edit of
    # the profile; a new one has none.
    id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    price_from: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    price_to: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: Currency = Currency.USD
    price_unit: str | None = Field(default=None, max_length=40)

    @field_validator("title", "description", "price_unit")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def _range(self) -> Self:
        # A "to" alone is read as the single price.
        if self.price_from is None and self.price_to is not None:
            self.price_from, self.price_to = self.price_to, None
        if self.price_to is not None and self.price_from is not None:
            if self.price_to < self.price_from:
                raise ValueError(translate("talent.service_price_range"))
            if self.price_to == self.price_from:
                self.price_to = None
        return self


class TalentFaqIn(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=1000)

    @field_validator("question", "answer")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class TalentEducationIn(BaseModel):
    degree: str | None = Field(default=None, max_length=160)
    field: str | None = Field(default=None, max_length=160)
    institution: str | None = Field(default=None, max_length=200)
    graduation_year: int | None = Field(default=None, ge=1940, le=2100)

    @field_validator("degree", "field", "institution")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TalentCourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    issuer: str | None = Field(default=None, max_length=160)
    year: int | None = Field(default=None, ge=1940, le=2100)

    @field_validator("name", "issuer")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TalentProfileFieldsIn(BaseModel):
    """The professional detail shared by create and update.

    Identity is not part of this: it is set on the account
    (``PATCH /api/me``), so a person who also owns a business enters their
    legal name once rather than once per listing.
    """
    # One level below the chosen skill, in the person's own words.
    skill_specialty: str | None = Field(default=None, max_length=160)
    preferred_contact: ContactChannel | None = None

    highest_degree: str | None = Field(default=None, max_length=160)
    specialization: str | None = Field(default=None, max_length=160)
    university: str | None = Field(default=None, max_length=200)
    education_years: int | None = Field(default=None, ge=0, le=30)
    graduation_date: date | None = None
    study_focus: str | None = Field(default=None, max_length=2000)
    experience: str | None = Field(default=None, max_length=5000)
    professional_training: str | None = Field(default=None, max_length=2000)
    skills_text: str | None = Field(default=None, max_length=2000)
    services_offered: str | None = Field(default=None, max_length=2000)
    hobbies: str | None = Field(default=None, max_length=1000)
    employment_type: EmploymentType | None = None
    # Superseded by work_mode, which sets it; still accepted from older clients.
    remote_capable: bool = False
    work_mode: WorkMode | None = None

    languages: list[TalentLanguageIn] | None = Field(default=None, max_length=20)
    # Optional; omitted leaves them as they are, an empty list clears them.
    social_links: list[SocialLinkIn] | None = Field(default=None, max_length=10)

    # --- Job seekers. Each list replaces the stored one; omitted keeps it.
    desired_title: str | None = Field(default=None, max_length=60)
    availability: TalentAvailability | None = None
    education_level: EducationLevel | None = None
    work_types: list[TalentWorkType] | None = Field(default=None, max_length=4)
    work_area_ids: list[uuid.UUID] | None = Field(default=None, max_length=30)
    photo_hidden: bool | None = None
    cv_public: bool | None = None
    team_message: str | None = Field(default=None, max_length=2000)
    experiences: list[TalentExperienceIn] | None = Field(default=None, max_length=30)
    # Services: replaces the stored list; omitted keeps it.
    service_offers: list[TalentServiceOfferIn] | None = Field(default=None, max_length=20)
    faqs: list[TalentFaqIn] | None = Field(default=None, max_length=15)
    # Links to videos of the work: YouTube, Instagram, TikTok or Facebook
    # (the owners' review, 12 Nov 2026). Checked in TalentService.
    work_videos: list[Annotated[str, Field(max_length=500)]] | None = Field(
        default=None, max_length=6
    )
    education: list[TalentEducationIn] | None = Field(default=None, max_length=15)
    courses: list[TalentCourseIn] | None = Field(default=None, max_length=30)

    @field_validator("desired_title")
    @classmethod
    def _strip_desired_title(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("highest_degree", "specialization", "university")
    @classmethod
    def _strip_short_text(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TalentCreateIn(TalentProfileFieldsIn):
    display_name: str = Field(min_length=2, max_length=160)
    # Optional here, defaulting to a service, so a dashboard draft and every
    # client written before the split keep working; the public application
    # requires an answer (see TalentRegistrationIn).
    kind: TalentKind | None = None
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    skill_id: uuid.UUID | None = None
    custom_skill_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    # Show the numbers to visitors; absent keeps the current choice (shown).
    phone_public: bool | None = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    # A link, because that is what the person has; stored as an id.
    video_url: str | None = Field(default=None, max_length=500)
    # Where they are on the map, as a business's pin is: public, and enough
    # at the level of the town.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError(translate("talent.name_too_short"))
        return cleaned

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("custom_skill_text")
    @classmethod
    def _strip_custom_skill(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def _pin_in_lebanon(self) -> Self:
        check_pin(self.latitude, self.longitude)
        return self


class TalentSkillChangeIn(BaseModel):
    """An administrator's correction of the skill a profile was filed under."""

    skill_id: uuid.UUID
    custom_skill_text: str | None = Field(default=None, max_length=120)


class ConvertToBusinessIn(BaseModel):
    """The shop category a service profile is moved into."""

    category_id: uuid.UUID


class ConvertedOut(BaseModel):
    business_id: uuid.UUID


class ConvertToTalentIn(BaseModel):
    """The service skill a shop is moved into."""

    skill_id: uuid.UUID


class ConvertedToTalentOut(BaseModel):
    profile_id: uuid.UUID


class TalentUpdateIn(TalentProfileFieldsIn):
    """Every field optional: the profile editor saves one section at a time."""

    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    kind: TalentKind | None = None
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    skill_id: uuid.UUID | None = None
    custom_skill_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    # Show the numbers to visitors; absent keeps the current choice (shown).
    phone_public: bool | None = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    # A link, because that is what the person has; stored as an id.
    video_url: str | None = Field(default=None, max_length=500)
    # Where they are on the map, as a business's pin is: public, and enough
    # at the level of the town.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("custom_skill_text")
    @classmethod
    def _strip_custom_skill(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @model_validator(mode="after")
    def _pin_in_lebanon(self) -> Self:
        check_pin(self.latitude, self.longitude)
        return self


class EmployerRequestIn(BaseModel):
    """An employer's "have a job for this candidate?" form on their page."""

    employer_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=6, max_length=25)
    company: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=160)
    message: str | None = Field(default=None, max_length=1000)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        normalized = normalize_optional_phone(value)
        if not normalized:
            raise ValueError(translate("employer_request.phone_required"))
        return normalized

    @field_validator("employer_name", "company", "job_title")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class EmployerRequestOut(ORMModel):
    """The admin's log of employer requests (`/admin/employer-requests`)."""

    id: uuid.UUID
    profile_id: uuid.UUID
    candidate_name: str | None = None
    candidate_slug: str | None = None
    candidate_whatsapp: str | None = None
    employer_name: str
    phone: str
    company: str | None = None
    job_title: str | None = None
    message: str | None = None
    status: EmployerRequestStatus
    created_at: datetime


class EmployerRequestStatusIn(BaseModel):
    status: EmployerRequestStatus
