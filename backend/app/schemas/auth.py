from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_optional_phone, normalize_phone
from app.models.enums import Gender, MaritalStatus, UserRole
from app.schemas.common import ORMModel
from app.schemas.identity import IdentityFieldsIn


class RequestOtpIn(BaseModel):
    phone_number: str = Field(min_length=6, max_length=25, examples=["03123456"])

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)


class RequestOtpOut(BaseModel):
    message: str = Field(default_factory=lambda: translate("auth.otp.sent"))
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
            raise ValueError(translate("auth.otp.digits_only"))
        return cleaned


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    """The authenticated user's own profile.

    A user's login phone (and personal phone) is returned only to themselves
    and to administrators; neither is ever part of any public payload.
    """

    id: uuid.UUID
    phone_number: str | None
    personal_phone_number: str | None
    email: str | None
    display_name: str | None
    role: UserRole
    # True while an administrator-issued password has not been replaced. The
    # client routes on this; the server enforces it regardless.
    must_change_password: bool = False
    created_at: datetime

    # Identity, returned only to the account itself. Every listing this
    # account owns reads from this one copy.
    full_name: str | None = None
    birth_year: int | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    registration_place: str | None = None
    residence_place: str | None = None
    # The account holder's own photo, on the same footing as the fields above:
    # returned to the account itself and to an administrator, and to nobody
    # else.
    photo_url: str | None = None


class OwnerLoginIn(BaseModel):
    """Phone and password, for an account an administrator issued one to."""

    phone_number: str = Field(min_length=6, max_length=25)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    """Replacing one's own password.

    The current password is required even while ``must_change_password`` is
    set: the session was opened with it moments ago, and asking again is what
    stops a borrowed unlocked phone from taking the account over.
    """

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class IssuedPasswordOut(BaseModel):
    """An administrator-issued password, returned exactly once.

    Never stored in plaintext, never logged, and not readable again after this
    response — losing it means issuing another. The account holder receives it
    out of band, from the administrator's own WhatsApp.
    """

    phone_number: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class UpdateProfileIn(IdentityFieldsIn):
    display_name: str | None = Field(default=None, max_length=120)
    personal_phone_number: str | None = Field(default=None, max_length=25)

    @field_validator("personal_phone_number")
    @classmethod
    def _normalize_personal_phone(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)
