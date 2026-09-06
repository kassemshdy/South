from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_optional_phone
from app.models.enums import BusinessStatus, ImageKind
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


class TalentDetailOut(TalentSummaryOut):
    bio: str | None = None
    email: str | None = None
    website: str | None = None
    images: list[TalentImageOut] = Field(default_factory=list)
    approved_at: datetime | None = None


class OwnerTalentOut(TalentDetailOut):
    """Adds moderation fields only the owner (and admins) may see."""

    status: BusinessStatus
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    updated_at: datetime


class TalentCreateIn(BaseModel):
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


class TalentUpdateIn(BaseModel):
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
