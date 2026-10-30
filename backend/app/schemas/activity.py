from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class ActivityIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10)
    summary: str | None = Field(default=None, max_length=300)
    slug: str | None = Field(default=None, max_length=180)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    sort_order: int = Field(default=0, ge=-1000, le=1000)

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> ActivityIn:
        if self.ends_at is not None and (self.starts_at is None or self.ends_at <= self.starts_at):
            raise ValueError("ends_at must be after starts_at")
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


class AdminActivityOut(ActivityOut):
    is_archived: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
