from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_optional_phone
from app.models.enums import (
    BusinessStatus,
    ContactChannel,
    EmploymentType,
    ImageKind,
    LanguageProficiency,
)
from app.schemas.common import ORMModel
from app.schemas.taxonomy import LocationOut

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
    photo_url: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    years_experience: int | None = None
    skill: TalentSkillOut | None = None
    # The person's own words, shown instead of the literal "Other" skill name.
    custom_skill_text: str | None = None
    # One level below the skill and in their own words, which is what makes a
    # card worth reading: the trade narrowed to what this person actually does.
    skill_specialty: str | None = None
    location: LocationOut | None = None
    created_at: datetime


class TalentLanguageOut(ORMModel):
    id: uuid.UUID
    name: str
    proficiency: LanguageProficiency
    sort_order: int


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
    images: list[TalentImageOut] = Field(default_factory=list)
    approved_at: datetime | None = None

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


class OwnerTalentOut(TalentDetailOut):
    """Adds the moderation state only the owner (and administrators) see.

    Anything added below is invisible to an anonymous visitor; anything added
    above is published. The owner's identity is not here at all — it belongs
    to the account, not the profile, and is read through ``UserOut``.
    """

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
    remote_capable: bool = False

    languages: list[TalentLanguageIn] | None = Field(default=None, max_length=20)

    @field_validator("highest_degree", "specialization", "university")
    @classmethod
    def _strip_short_text(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TalentCreateIn(TalentProfileFieldsIn):
    display_name: str = Field(min_length=2, max_length=160)
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    skill_id: uuid.UUID | None = None
    custom_skill_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    # A link, because that is what the person has; stored as an id.
    video_url: str | None = Field(default=None, max_length=500)

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


class TalentUpdateIn(TalentProfileFieldsIn):
    """Every field optional: the profile editor saves one section at a time."""

    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    skill_id: uuid.UUID | None = None
    custom_skill_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    # A link, because that is what the person has; stored as an id.
    video_url: str | None = Field(default=None, max_length=500)

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("custom_skill_text")
    @classmethod
    def _strip_custom_skill(cls, value: str | None) -> str | None:
        return _strip_or_none(value)
