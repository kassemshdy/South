from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TeamMemberOut(BaseModel):
    slot: int
    photo_url: str | None = None
    caption_ar: str | None = None
    caption_en: str | None = None
    updated_at: datetime | None = None


class TeamCaptionIn(BaseModel):
    """A slot's caption in both languages; blank clears that language."""

    caption_ar: str | None = Field(default=None, max_length=300)
    caption_en: str | None = Field(default=None, max_length=300)

    @field_validator("caption_ar", "caption_en")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.replace("\r\n", "\n").strip()
        return cleaned or None
