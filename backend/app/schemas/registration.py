"""Public registration: what an applicant sends before they have an account.

Deliberately a thin wrapper around the existing create schemas rather than a
parallel set of fields. An application *is* a listing — it is stored as one,
pending review — so the shapes stay in step by construction: a field added to
`BusinessCreateIn` is a field an applicant can fill, with no second definition
to forget.

What this adds on top is the four things an applicant has and an owner does
not: the phone number that will become their login, the password they choose
for it, the captcha token, and who they are.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.models.enums import TalentKind
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
    # Yes or no, and an answer is required: the owners asked every applicant
    # whether they are currently displaced from the South. For the team only.
    is_displaced: bool

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

    @model_validator(mode="after")
    def _where_before(self) -> RegistrationIdentityIn:
        # The owners asked a displaced applicant where they lived before as
        # well as now; residence_place above is the "now".
        if self.is_displaced and not self.pre_displacement_place:
            raise ValueError(translate("registration.pre_displacement_required"))
        if not self.is_displaced:
            self.pre_displacement_place = None
        return self


class RegistrationBase(BaseModel):
    # Becomes the account's login identity — the number they will type into
    # the sign-in form, and the one a gateway would text if one ever arrives.
    # Required, unlike the listing's published phone: without it there is no
    # account to create and nowhere to send the credentials.
    login_phone: str = Field(min_length=6, max_length=25)
    # Chosen by the applicant (round 3: the owners dropped the administrator
    # issuing one). Same bounds as a password change. Hashed on the way in,
    # and excluded from everything else that is kept -- see
    # RegistrationService._claim_account.
    password: str = Field(min_length=8, max_length=128)
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

    @model_validator(mode="after")
    def _place(self) -> BusinessRegistrationIn:
        # Optional on a dashboard draft, where it has a step of its own, but
        # an application goes straight to review and "from the South" cannot
        # be judged without it.
        if self.business.location_id is None:
            raise ValueError(translate("registration.location_required"))
        if self.business.latitude is None or self.business.longitude is None:
            raise ValueError(translate("registration.map_pin_required"))
        return self


class TalentRegistrationIn(RegistrationBase):
    talent: TalentCreateIn

    @model_validator(mode="after")
    def _years_of_experience(self) -> TalentRegistrationIn:
        # Optional on a dashboard draft, which can be saved half-done, but an
        # application goes straight to review -- and the owners made the
        # number compulsory, since the directory can be sorted by it.
        if self.talent.years_experience is None:
            raise ValueError(translate("registration.years_experience_required"))
        # Services or a job application: the applicant's own choice, and
        # which directory the profile is listed in once approved.
        if self.talent.kind is None:
            raise ValueError(translate("registration.talent_kind_required"))
        # Remotely, in person or both: compulsory for a service, which is
        # what visitors filter on; a job application is not asked.
        if self.talent.kind == TalentKind.SERVICE and self.talent.work_mode is None:
            raise ValueError(translate("registration.work_mode_required"))
        if self.talent.location_id is None:
            raise ValueError(translate("registration.location_required"))
        if self.talent.latitude is None or self.talent.longitude is None:
            raise ValueError(translate("registration.map_pin_required"))
        return self


class RegistrationOut(BaseModel):
    """Says only that the application was received.

    No id, no status, nothing about the account: an applicant has nothing to do
    with any of it, and returning it would let this endpoint answer questions
    about who is already registered. Every outcome — new application, a phone
    number that already has an account — produces this same message.
    """

    message: str
