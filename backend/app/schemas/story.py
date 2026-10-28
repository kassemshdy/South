from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StoryOut(BaseModel):
    """A story as its owner sees it, whatever its state."""

    id: uuid.UUID
    image_url: str
    caption: str | None = None
    status: str
    approved_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class AdminStoryOut(StoryOut):
    """A story in the review queue, with the listing it belongs to."""

    listing_kind: Literal["business", "talent"]
    listing_id: uuid.UUID
    listing_name: str
    listing_slug: str


class PublicStoryOut(BaseModel):
    id: uuid.UUID
    image_url: str
    caption: str | None = None
    approved_at: datetime


class StoryGroupOut(BaseModel):
    """One circle in the home page's stories row: a listing and its current
    photographs, oldest first, as they are watched."""

    kind: Literal["business", "talent"]
    slug: str
    name: str
    image_url: str | None
    stories: list[PublicStoryOut]
