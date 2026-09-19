"""Public registration: what an applicant sends before they have an account.

Deliberately a thin wrapper around the existing create schemas rather than a
parallel set of fields. An application *is* a listing — it is stored as one,
pending review — so the shapes stay in step by construction: a field added to
`BusinessCreateIn` is a field an applicant can fill, with no second definition
to forget.

What this adds on top is the three things an applicant has and an owner does
not: the phone number that will become their login, the captcha token, and who
they are.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.schemas.business import BusinessCreateIn
from app.schemas.identity import IdentityFieldsIn
from app.schemas.talent import TalentCreateIn


class RegistrationIdentityIn(IdentityFieldsIn):
    """Who the applicant is, asked at the point of applying.

    The same fields an account holds, with four of them required rather than
    optional. The reviewer is deciding whether this is a real person from the
    South, and every one of these is something they would otherwise have to
    ask for over WhatsApp before they could decide — so collecting them later,
    once the account exists, puts the audit before the evidence.

    Gender and marital status stay optional here, as they are everywhere else:
    nothing in the review turns on them, and a public form is the wrong place
    to insist on either. They are on the account page for whoever wants to
    fill them in.

    Nothing in this class reaches a public payload. It is written onto the
    ``users`` row, which no public schema carries — the boundary
    `tests/test_identity.py` pins.
    """

    full_name: str = Field(min_length=2, max_length=200)
    birth_year: int = Field(ge=1900, le=2100)
    registration_place: str = Field(min_length=2, max_length=160)
    residence_place: str = Field(min_length=2, max_length=200)

    @field_validator("full_name", "registration_place", "residence_place")
    @classmethod
    def _require_something(cls, value: str | None) -> str:
        """Refuse a field that is only whitespace.

        Runs after the inherited one, which collapses "  " to None — right
        for an optional field, and a hole in a required one: pydantic does
        not re-check the annotation after an after-validator, so that None
        would be stored as-is and the field would be required in name only.
        Hence the ``| None`` on a parameter the annotation says is a ``str``.
        """
        if value is None or len(value) < 2:
            raise ValueError(translate("registration.identity_required"))
        return value


class RegistrationBase(BaseModel):
    # Becomes the account's login identity — the number they will type into
    # the sign-in form, and the one a gateway would text if one ever arrives.
    # Required, unlike the listing's published phone: without it there is no
    # account to create and nowhere to send the credentials.
    login_phone: str = Field(min_length=6, max_length=25)
    # Absent when Turnstile is not configured; see app/core/captcha.py.
    captcha_token: str | None = Field(default=None, max_length=4096)
    # Nested rather than flattened, for the reason OwnerIdentityOut is: these
    # are only ever read together, and one block makes it obvious at a glance
    # that a schema carries identity data.
    identity: RegistrationIdentityIn

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
