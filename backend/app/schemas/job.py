from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.phone import normalize_phone
from app.models.enums import JobType, WorkMode
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
    created_at: datetime


class AdminJobOpeningOut(JobOpeningOut):
    is_published: bool
    application_count: int = 0
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


class JobApplicationIn(BaseModel):
    """The form fields of an application; the CV arrives as a file beside them."""

    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
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


class JobApplicationOut(ORMModel):
    """The staff view of an application; there is no other."""

    id: uuid.UUID
    full_name: str
    email: str
    phone_number: str
    original_filename: str | None = None
    content_type: str
    size_bytes: int
    created_at: datetime
