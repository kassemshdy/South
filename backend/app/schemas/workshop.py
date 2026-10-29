from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.phone import normalize_phone
from app.models.enums import Currency, WorkshopMode
from app.schemas.common import ORMModel
from app.schemas.taxonomy import CategoryOut, LocationOut


class WorkshopIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    slug: str | None = Field(default=None, max_length=180)
    trainer_name: str | None = Field(default=None, max_length=120)
    starts_at: datetime
    ends_at: datetime | None = None
    mode: WorkshopMode = WorkshopMode.IN_PERSON
    venue: str | None = Field(default=None, max_length=200)
    # None is free.
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: Currency = Currency.USD
    category_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> WorkshopIn:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class WorkshopUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    slug: str | None = Field(default=None, max_length=180)
    trainer_name: str | None = Field(default=None, max_length=120)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    mode: WorkshopMode | None = None
    venue: str | None = Field(default=None, max_length=200)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: Currency | None = None
    category_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None


class WorkshopOut(ORMModel):
    """What a visitor reads: published workshops, and never who signed up."""

    id: uuid.UUID
    slug: str
    title: str
    description: str
    trainer_name: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    mode: WorkshopMode
    venue: str | None = None
    price: Decimal | None = None
    currency: Currency
    cover_url: str | None = None
    category: CategoryOut | None = None
    location: LocationOut | None = None


class AdminWorkshopOut(WorkshopOut):
    is_published: bool
    registration_count: int = 0
    created_at: datetime
    updated_at: datetime


class WorkshopRegistrationIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone_number: str = Field(min_length=6, max_length=20)
    captcha_token: str | None = Field(default=None, max_length=4096)

    @field_validator("full_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)


class WorkshopRegistrationOut(ORMModel):
    """The administrator's view of a sign-up; there is no other."""

    id: uuid.UUID
    full_name: str
    phone_number: str
    created_at: datetime
