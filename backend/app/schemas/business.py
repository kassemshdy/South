from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_optional_phone
from app.models.enums import BusinessStatus, ImageKind, OwnerRelation, SocialPlatform
from app.schemas.common import ORMModel
from app.schemas.item import BusinessItemOut
from app.schemas.taxonomy import CategoryOut, LocationOut
from app.schemas.testimonial import TestimonialOut

OptionalPhone = Annotated[str | None, Field(default=None, max_length=25)]


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class BusinessImageOut(ORMModel):
    id: uuid.UUID
    url: str
    kind: ImageKind
    caption: str | None = None
    sort_order: int
    width: int | None = None
    height: int | None = None


class SocialLinkOut(ORMModel):
    platform: SocialPlatform
    url: str


class SocialLinkIn(BaseModel):
    platform: SocialPlatform
    url: str = Field(min_length=3, max_length=500)


class BusinessSummaryOut(ORMModel):
    """Card-sized payload used by lists and search results."""

    id: uuid.UUID
    name: str
    slug: str
    short_description: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    category: CategoryOut | None = None
    # The owner's own words, shown instead of the literal "Other" category
    # name — public-safe, deliberately authored for display (unlike the
    # owner's personal contact info, which never appears on a business tier).
    custom_category_text: str | None = None
    location: LocationOut | None = None
    created_at: datetime


class BusinessDetailOut(BusinessSummaryOut):
    description: str | None = None
    # Producer detail — published, unlike the owner's own identity, which
    # belongs to the account and never reaches a public payload.
    institution_name: str | None = None
    founding_date: date | None = None
    production_nature: str | None = None
    years_of_experience: int | None = None
    email: str | None = None
    website: str | None = None
    # The owner's introduction video, as a YouTube id. An id rather than a URL
    # so the client composes the embed itself and never renders a string an
    # owner typed — see app.core.urls.youtube_video_id.
    youtube_video_id: str | None = None
    address_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    maps_url: str | None = None
    images: list[BusinessImageOut] = Field(default_factory=list)
    social_links: list[SocialLinkOut] = Field(default_factory=list)
    items: list[BusinessItemOut] = Field(default_factory=list)
    # Owner-selected praise, never a review. Only APPROVED ones ever arrive
    # here -- see business_detail's docstring for why they are passed in
    # rather than read off the relationship.
    testimonials: list[TestimonialOut] = Field(default_factory=list)
    approved_at: datetime | None = None


class OwnerBusinessOut(BusinessDetailOut):
    """Adds moderation fields only the owner (and admins) may see.

    ``owner_relation`` is here rather than one class up on purpose. It says
    whether the person listing owns, manages or works at the establishment,
    which is a reviewer's question and nobody else's, so this class is the
    boundary that keeps it off every public payload —— exactly the role
    ``OwnerIdentityOut`` plays for the account holder's own fields.
    ``tests/test_owner_relation.py`` pins it.
    """

    owner_relation: OwnerRelation | None = None
    status: BusinessStatus
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    updated_at: datetime


class BusinessCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    institution_name: str | None = Field(default=None, max_length=200)
    founding_date: date | None = None
    production_nature: str | None = Field(default=None, max_length=5000)
    years_of_experience: int | None = Field(default=None, ge=0, le=100)
    owner_relation: OwnerRelation | None = None
    category_id: uuid.UUID | None = None
    custom_category_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    # A link, because that is what an owner has; stored as an id.
    video_url: str | None = Field(default=None, max_length=500)
    address_text: str | None = Field(default=None, max_length=400)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    maps_url: str | None = Field(default=None, max_length=1000)
    social_links: list[SocialLinkIn] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError(translate("business.name_too_short"))
        return cleaned

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("custom_category_text", "institution_name")
    @classmethod
    def _strip_custom_category(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class BusinessUpdateIn(BaseModel):
    """Every field optional: the wizard saves one step at a time."""

    name: str | None = Field(default=None, min_length=2, max_length=160)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    institution_name: str | None = Field(default=None, max_length=200)
    founding_date: date | None = None
    production_nature: str | None = Field(default=None, max_length=5000)
    years_of_experience: int | None = Field(default=None, ge=0, le=100)
    owner_relation: OwnerRelation | None = None
    category_id: uuid.UUID | None = None
    custom_category_text: str | None = Field(default=None, max_length=120)
    location_id: uuid.UUID | None = None
    phone: OptionalPhone = None
    whatsapp: OptionalPhone = None
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=500)
    # A link, because that is what an owner has; stored as an id.
    video_url: str | None = Field(default=None, max_length=500)
    address_text: str | None = Field(default=None, max_length=400)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    maps_url: str | None = Field(default=None, max_length=1000)
    social_links: list[SocialLinkIn] | None = None

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("custom_category_text", "institution_name")
    @classmethod
    def _strip_custom_category(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class ImageReorderIn(BaseModel):
    image_ids: list[uuid.UUID] = Field(min_length=1)


class ImageCaptionIn(BaseModel):
    caption: str | None = Field(default=None, max_length=300)
