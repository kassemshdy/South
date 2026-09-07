"""The account holder's identity fields — read and written in one place.

These describe the *person* behind an account, not any listing they own, so
they live on :class:`~app.models.user.User` and are shared by every business
and the talent profile. Nothing here may appear on a public schema: the
account reads its own through ``UserOut``, an administrator reads it through
the ``owner_identity`` block on a review payload, and an anonymous visitor
never reads it at all.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Gender, MaritalStatus
from app.schemas.common import ORMModel


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class OwnerIdentityOut(ORMModel):
    """An owner's identity, as an administrator reviewing a listing sees it.

    Nested rather than flattened onto each review payload: six fields that
    are only ever read together, and one block makes it obvious at a glance
    that a schema carries identity data.
    """

    full_name: str | None = None
    birth_year: int | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    registration_place: str | None = None
    residence_place: str | None = None


class IdentityFieldsIn(BaseModel):
    """The identity fields an account may set on itself.

    Birth *year* rather than age: an age entered once is wrong a year later,
    and anything that needs an age can derive it.
    """

    full_name: str | None = Field(default=None, max_length=200)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    registration_place: str | None = Field(default=None, max_length=160)
    residence_place: str | None = Field(default=None, max_length=200)

    @field_validator("full_name", "registration_place", "residence_place")
    @classmethod
    def _strip_short_text(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


IDENTITY_FIELDS: tuple[str, ...] = tuple(IdentityFieldsIn.model_fields)
