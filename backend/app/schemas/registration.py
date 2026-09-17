"""Public registration: what an applicant sends before they have an account.

Deliberately a thin wrapper around the existing create schemas rather than a
parallel set of fields. An application *is* a listing — it is stored as one,
pending review — so the shapes stay in step by construction: a field added to
`BusinessCreateIn` is a field an applicant can fill, with no second definition
to forget.

What this adds on top is the two things an applicant has and an owner does not:
the phone number that will become their login, and the captcha token.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_phone
from app.schemas.business import BusinessCreateIn
from app.schemas.talent import TalentCreateIn


class RegistrationBase(BaseModel):
    # Becomes the account's login identity, and the same identity an OTP would
    # use — so a gateway arriving later is a second door, not a migration.
    # Required, unlike the listing's published phone: without it there is no
    # account to create and nowhere to send the credentials.
    login_phone: str = Field(min_length=6, max_length=25)
    # Absent when Turnstile is not configured; see app/core/captcha.py.
    captcha_token: str | None = Field(default=None, max_length=4096)


    @field_validator("login_phone")
    @classmethod
    def _normalize_login_phone(cls, value: str) -> str:
        # Stored E.164 so the account matches however it is typed later, and
        # so a second application cannot create a duplicate of the same person
        # under a differently formatted number.
        return normalize_phone(value)


class BusinessRegistrationIn(RegistrationBase):
    business: BusinessCreateIn


class TalentRegistrationIn(RegistrationBase):
    talent: TalentCreateIn


class RegistrationOut(BaseModel):
    """Says only that the application was received.

    No id, no status, nothing about the account: an applicant has nothing to do
    with any of it, and returning it would let this endpoint answer questions
    about who is already registered. Every outcome — new application, a phone
    number that already has an account — produces this same message.
    """

    message: str
