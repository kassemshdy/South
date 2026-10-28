from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ReelOut(BaseModel):
    """A reel as the home page shows it. ``url`` and ``embed_url`` are rebuilt
    from the post's code on ``www.instagram.com``, never the pasted link."""

    id: uuid.UUID
    url: str
    embed_url: str
    caption_ar: str | None = None
    caption_en: str | None = None
    cover_url: str | None = None


class AdminReelOut(ReelOut):
    is_published: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ReelIn(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    caption_ar: str | None = Field(default=None, max_length=300)
    caption_en: str | None = Field(default=None, max_length=300)
    is_published: bool = False

    @field_validator("caption_ar", "caption_en")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.replace("\r\n", "\n").strip()
        return cleaned or None


class ReelOrderIn(BaseModel):
    """Every reel's id, in the order they are to be shown."""

    ids: list[uuid.UUID] = Field(max_length=500)
