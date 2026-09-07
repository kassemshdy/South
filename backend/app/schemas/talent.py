from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_optional_phone
from app.models.enums import (
    BusinessStatus,
    Gender,
    ImageKind,
    LanguageProficiency,
    MaritalStatus,
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
    headline: str | None = None
    photo_url: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    years_experience: int | None = None
    skill: TalentSkillOut | None = None
    # The person's own words, shown instead of the literal "Other" skill name.
    custom_skill_text: str | None = None
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
    images: list[TalentImageOut] = Field(default_factory=list)
    approved_at: datetime | None = None

    # Professional detail: what the person can do, which is the whole point
    # of publishing a profile.
    highest_degree: str | None = None
    specialization: str | None = None
    university: str | None = None
    experience: str | None = None
    skills_text: str | None = None
    services_offered: str | None = None
    languages: list[TalentLanguageOut] = Field(default_factory=list)


class OwnerTalentOut(TalentDetailOut):
    """Adds the moderation state and the identity fields only the owner
    (and administrators) may see.

    The identity fields live here rather than on TalentDetailOut on purpose:
    a public directory should not publish someone's legal name, age, gender,
    marital status or civil-record places. Anything added below is invisible
    to an anonymous visitor; anything added above is published.
    """

    status: BusinessStatus
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    updated_at: datetime

    full_name: str | None = None
    birth_year: int | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    registration_place: str | None = None
    residence_place: str | None = None


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
    """The detail fields shared by create and update.

    Birth *year* rather than age: an age entered once is wrong a year later,
    and the profile can derive it for display.
    """

    highest_degree: str | None = Field(default=None, max_length=160)
    specialization: str | None = Field(default=None, max_length=160)
    university: str | None = Field(default=None, max_length=200)
    experience: str | None = Field(default=None, max_length=5000)
    skills_text: str | None = Field(default=None, max_length=2000)
    services_offered: str | None = Field(default=None, max_length=2000)

    full_name: str | None = Field(default=None, max_length=200)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    registration_place: str | None = Field(default=None, max_length=160)
    residence_place: str | None = Field(default=None, max_length=200)

    languages: list[TalentLanguageIn] | None = Field(default=None, max_length=20)

    @field_validator(
        "highest_degree",
        "specialization",
        "university",
        "full_name",
        "registration_place",
        "residence_place",
    )
    @classmethod
    def _strip_short_text(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class TalentCreateIn(TalentProfileFieldsIn):
    display_name: str = Field(min_length=2, max_length=160)
    headline: str | None = Field(default=None, max_length=300)
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    skill_id: uuid.UUID | None = None
    custom_skill_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)

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
    headline: str | None = Field(default=None, max_length=300)
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    skill_id: uuid.UUID | None = None
    custom_skill_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("custom_skill_text")
    @classmethod
    def _strip_custom_skill(cls, value: str | None) -> str | None:
        return _strip_or_none(value)
