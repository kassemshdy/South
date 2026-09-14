from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ArticleSection
from app.schemas.common import ORMModel


class ArticleIn(BaseModel):
    """What an administrator sends to write one. Created as a draft; ``publish``
    is a separate call, so a half-finished article is never one save away from
    going live."""

    section: ArticleSection
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10)
    slug: str | None = Field(default=None, max_length=180)


class ArticleUpdateIn(BaseModel):
    section: ArticleSection | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, min_length=10)
    slug: str | None = Field(default=None, max_length=180)


class ArticleOut(ORMModel):
    """What a visitor reads — published only, no moderation state."""

    id: uuid.UUID
    section: ArticleSection
    slug: str
    title: str
    body: str
    cover_url: str | None
    published_at: datetime | None


class AdminArticleOut(ArticleOut):
    """The administrator's view: adds the draft switch and both timestamps."""

    is_published: bool
    created_at: datetime
    updated_at: datetime
