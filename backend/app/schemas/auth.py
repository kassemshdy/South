from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.phone import normalize_optional_phone
from app.models.enums import Gender, MaritalStatus, UserRole
from app.schemas.common import ORMModel
from app.schemas.identity import IdentityFieldsIn


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


class LoginIn(BaseModel):
    """What somebody types into the one sign-in form.

    ``identifier`` rather than a phone field and an email field, because the
    form has one box: an owner fills it with the phone number their account is
    keyed by, an administrator with their email address, and the service tells
    them apart. Deliberately unvalidated beyond a length — normalizing it here
    would answer "is that a real Lebanese number?" with a 422 to anyone who
    asked, and the answer to every sign-in that does not work is the same
    sentence. The minimum is one character rather than a plausible one for
    the same reason: a length only a real identifier could reach is itself an
    answer.
    """

    identifier: str = Field(min_length=1, max_length=255)
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
