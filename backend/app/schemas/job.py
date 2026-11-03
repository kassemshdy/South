from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_phone
from app.models.enums import JobContactChannel, JobStatus, JobType, WorkMode
from app.schemas.common import ORMModel
from app.schemas.taxonomy import LocationOut


class JobOpeningIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    slug: str | None = Field(default=None, max_length=180)
    employer_name: str | None = Field(default=None, max_length=160)
    job_type: JobType = JobType.FULL_TIME
    salary: str | None = Field(default=None, max_length=120)
    deadline: date | None = None
    location_id: uuid.UUID | None = None
    work_place: str | None = Field(default=None, max_length=200)
    work_mode: WorkMode | None = None
    status: JobStatus = JobStatus.ACTIVE
    # Applicants contact this number; empty falls back to the site's WhatsApp.
    contact_phone: str | None = Field(default=None, max_length=25)
    contact_name: str | None = Field(default=None, max_length=120)
    whatsapp_enabled: bool = True

    @field_validator("contact_phone")
    @classmethod
    def _normalize_contact(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value and value.strip() else None


class JobOpeningUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    slug: str | None = Field(default=None, max_length=180)
    employer_name: str | None = Field(default=None, max_length=160)
    job_type: JobType | None = None
    salary: str | None = Field(default=None, max_length=120)
    deadline: date | None = None
    location_id: uuid.UUID | None = None
    work_place: str | None = Field(default=None, max_length=200)
    work_mode: WorkMode | None = None
    status: JobStatus | None = None
    contact_phone: str | None = Field(default=None, max_length=25)
    contact_name: str | None = Field(default=None, max_length=120)
    whatsapp_enabled: bool | None = None

    @field_validator("contact_phone")
    @classmethod
    def _normalize_contact(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value and value.strip() else None


class JobOpeningOut(ORMModel):
    """What a visitor reads: published openings, never who applied."""

    id: uuid.UUID
    slug: str
    title: str
    description: str
    employer_name: str | None = None
    job_type: JobType
    salary: str | None = None
    deadline: date | None = None
    location: LocationOut | None = None
    work_place: str | None = None
    work_mode: WorkMode | None = None
    cover_url: str | None = None
    created_at: datetime
    #: Open, filled or no longer available. An open opening past its
    #: deadline reads as no longer available without anyone changing it.
    status: JobStatus = JobStatus.ACTIVE
    status_changed_at: datetime | None = None
    #: The number to contact -- the opening's own, or the site's WhatsApp.
    contact_phone: str | None = None
    contact_name: str | None = None
    whatsapp_enabled: bool = True


class AdminJobOpeningOut(JobOpeningOut):
    is_published: bool
    #: The status as saved, which ``status`` may override after a deadline.
    saved_status: JobStatus = JobStatus.ACTIVE
    #: The opening's own number, empty when it falls back to the site's.
    own_contact_phone: str | None = None
    #: Presses of the WhatsApp and call buttons, all time.
    contact_clicks: int = 0
    updated_at: datetime
    #: Who offered it, when an employer did on the public form. Staff only.
    submitter_name: str | None = None
    submitter_phone: str | None = None
    has_id_document: bool = False


class JobOfferIn(BaseModel):
    """An employer's offer from the public form; the ID scan arrives beside it."""

    submitter_name: str = Field(min_length=2, max_length=80)
    phone_number: str = Field(min_length=6, max_length=20)
    employer_name: str = Field(min_length=2, max_length=160)
    work_place: str = Field(min_length=2, max_length=200)
    work_mode: WorkMode
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    captcha_token: str | None = Field(default=None, max_length=4096)

    @field_validator("submitter_name", "employer_name", "work_place", "title", "description")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone_number")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        return normalize_phone(value)


class JobContactClickIn(BaseModel):
    channel: JobContactChannel


class JobContactDayOut(BaseModel):
    day: date
    whatsapp: int = 0
    call: int = 0


class JobContactStatsOut(BaseModel):
    """Presses per button, all time and per day (newest first)."""

    whatsapp: int = 0
    call: int = 0
    days: list[JobContactDayOut] = Field(default_factory=list)
