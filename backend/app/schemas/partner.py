from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_phone
from app.schemas.common import ORMModel


class PartnerRequestIn(BaseModel):
    """What the partner form sends. Every field is required: the team has to
    be able to answer, and to know who is offering what."""

    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=6, max_length=20)
    occupation: str = Field(min_length=2, max_length=160)
    residence: str = Field(min_length=2, max_length=200)
    offer: str = Field(min_length=5, max_length=2000)
    captcha_token: str | None = Field(default=None, max_length=4096)

    @field_validator("name", "occupation", "residence", "offer")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)


class PartnerRequestOut(ORMModel):
    """The administrator's view; there is no other."""

    id: uuid.UUID
    name: str
    phone: str
    occupation: str
    residence: str
    offer: str
    created_at: datetime
    solved_at: datetime | None = None
