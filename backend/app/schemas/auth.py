from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.phone import normalize_phone
from app.models.enums import UserRole
from app.schemas.common import ORMModel


class RequestOtpIn(BaseModel):
    phone_number: str = Field(min_length=6, max_length=25, examples=["03123456"])

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)


class RequestOtpOut(BaseModel):
    message: str = "تم إرسال رمز التحقق."
    expires_in_seconds: int
    # Present only in development so the flow is testable without an SMS gateway.
    debug_code: str | None = None


class VerifyOtpIn(BaseModel):
    phone_number: str = Field(min_length=6, max_length=25)
    code: str = Field(min_length=4, max_length=8)

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.isdigit():
            raise ValueError("رمز التحقق يجب أن يتكون من أرقام فقط.")
        return cleaned


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    """The authenticated user's own profile.

    A user's login phone is returned only to themselves and to administrators;
    it is never part of any public payload.
    """

    id: uuid.UUID
    phone_number: str | None
    email: str | None
    display_name: str | None
    role: UserRole
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class UpdateProfileIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
