"""Staff accounts: administrators with a role, managed by a manager."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.phone import normalize_optional_phone
from app.models.enums import StaffRole
from app.schemas.common import ORMModel


class StaffOut(ORMModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    staff_role: StaffRole | None
    is_active: bool
    # Where the manager sends a password on WhatsApp; never a login.
    personal_phone_number: str | None = None
    created_at: datetime


class StaffInviteIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    staff_role: StaffRole
    phone: str | None = Field(default=None, max_length=25)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)


class StaffUpdateIn(BaseModel):
    staff_role: StaffRole | None = None
    is_active: bool | None = None


class StaffPasswordOut(BaseModel):
    """A staff member's password, returned exactly once, like an owner's."""

    staff: StaffOut
    password: str
