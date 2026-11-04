from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.models.enums import ActivityKind, ActivityRegistrationMode
from app.schemas.common import ORMModel
from app.services.images import thumbnail_url


def _http_url(value: str | None) -> str | None:
    """A registration or slide link: empty, or an http(s) address."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if not cleaned.lower().startswith(("http://", "https://")):
        raise ValueError(translate("activity.link_scheme"))
    return cleaned


def _blank_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class ActivityIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10)
    summary: str | None = Field(default=None, max_length=300)
    slug: str | None = Field(default=None, max_length=180)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    sort_order: int = Field(default=0, ge=-1000, le=1000)
    kind: ActivityKind = ActivityKind.ACTIVITY
    registration_mode: ActivityRegistrationMode = ActivityRegistrationMode.ON_SITE
    register_url: str | None = Field(default=None, max_length=500)
    register_label: str | None = Field(default=None, max_length=60)
    show_calendar: bool = True

    _register_url = field_validator("register_url")(classmethod(lambda cls, v: _http_url(v)))
    _register_label = field_validator("register_label")(classmethod(lambda cls, v: _blank_none(v)))

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> ActivityIn:
        if self.ends_at is not None and (self.starts_at is None or self.ends_at <= self.starts_at):
            raise ValueError("ends_at must be after starts_at")
        return self

    @model_validator(mode="after")
    def _external_needs_its_link(self) -> ActivityIn:
        if self.registration_mode is ActivityRegistrationMode.EXTERNAL and not self.register_url:
            raise ValueError(translate("activity.external_needs_link"))
        return self


class ActivityUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, min_length=10)
    summary: str | None = Field(default=None, max_length=300)
    slug: str | None = Field(default=None, max_length=180)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    sort_order: int | None = Field(default=None, ge=-1000, le=1000)
    # Archiving is an edit: the administrator keeps it or puts it away.
    is_archived: bool | None = None
    kind: ActivityKind | None = None
    registration_mode: ActivityRegistrationMode | None = None
    register_url: str | None = Field(default=None, max_length=500)
    register_label: str | None = Field(default=None, max_length=60)
    show_calendar: bool | None = None
    # The form's "show in carousel" box: true puts it first, false takes it
    # out. Needs the photograph.
    in_carousel: bool | None = None

    _register_url = field_validator("register_url")(classmethod(lambda cls, v: _http_url(v)))
    _register_label = field_validator("register_label")(classmethod(lambda cls, v: _blank_none(v)))


class ActivityOut(ORMModel):
    """What a visitor reads: kept activities that have their photograph."""

    id: uuid.UUID
    slug: str
    title: str
    summary: str | None = None
    body: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None
    image_url: str | None = None
    kind: ActivityKind = ActivityKind.ACTIVITY
    registration_mode: ActivityRegistrationMode = ActivityRegistrationMode.ON_SITE
    register_url: str | None = None
    register_label: str | None = None
    show_calendar: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_thumb_url(self) -> str | None:
        return thumbnail_url(self.image_url)


class AdminActivityOut(ActivityOut):
    is_archived: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    in_carousel: bool = False
    registration_count: int = 0


class ActivityRegistrationIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone_number: str = Field(min_length=6, max_length=20)
    captcha_token: str | None = Field(default=None, max_length=4096)

    @field_validator("full_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)


class ActivityRegistrationOut(ORMModel):
    """The administrator's view of a sign-up; there is no other."""

    id: uuid.UUID
    full_name: str
    phone_number: str
    created_at: datetime


class CarouselSlideOut(BaseModel):
    """A slide as a visitor sees it."""

    id: uuid.UUID
    title: str | None = None
    image_url: str
    # An activity's own page (internal) or a custom slide's link (external);
    # null when a custom slide has no link.
    href: str | None = None
    external: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_thumb_url(self) -> str | None:
        return thumbnail_url(self.image_url)


class AdminCarouselSlideOut(CarouselSlideOut):
    kind: Literal["ACTIVITY", "CUSTOM"]
    position: int
    activity_id: uuid.UUID | None = None
    link_url: str | None = None
    ends_at: datetime | None = None
    # Why a visitor does not see it right now, if they do not.
    hidden_reason: Literal["ARCHIVED", "NO_IMAGE", "ENDED"] | None = None


class AdminCarouselOut(BaseModel):
    slides: list[AdminCarouselSlideOut]
    autoremove_expired: bool


class CarouselOrderIn(BaseModel):
    slide_ids: list[uuid.UUID] = Field(max_length=200)


class CarouselAddActivityIn(BaseModel):
    activity_id: uuid.UUID


class CarouselSlideUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    link_url: str | None = Field(default=None, max_length=500)

    _link = field_validator("link_url")(classmethod(lambda cls, v: _http_url(v)))
    _title = field_validator("title")(classmethod(lambda cls, v: _blank_none(v)))


class CarouselSettingsIn(BaseModel):
    autoremove_expired: bool
