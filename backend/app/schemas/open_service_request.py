from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.schemas.common import ORMModel


class OpenServiceRequestIn(BaseModel):
    """What the "request a service" form sends. The skill and the town are optional:
    a visitor who does not know what the trade is called can still ask."""

    customer_name: str = Field(min_length=2, max_length=80)
    customer_phone: str = Field(min_length=6, max_length=20)
    details: str = Field(min_length=10, max_length=1000)
    skill_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    captcha_token: str | None = Field(default=None, max_length=4096)

    @field_validator("customer_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("customer_phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("details")
    @classmethod
    def _strip_details(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError(translate("service_request.details_too_short"))
        return cleaned


class OpenServiceRequestOut(ORMModel):
    """The staff view; there is no public one."""

    id: uuid.UUID
    customer_name: str
    customer_phone: str
    details: str
    skill_id: uuid.UUID | None = None
    skill_name: str | None = None
    skill_slug: str | None = None
    location_id: uuid.UUID | None = None
    location_name: str | None = None
    location_slug: str | None = None
    created_at: datetime
    solved_at: datetime | None = None
