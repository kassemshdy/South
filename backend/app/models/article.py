"""Admin-authored articles: the content behind the "coming soon" blog and
news placeholders in the top nav.

Unlike a business or talent listing, nothing here is owner-submitted — only
an administrator can write one, so there is no PENDING/REJECTED moderation
state, just a draft/published switch. ``section`` decides which of the two
already-linked pages (``/blog`` or ``/news``) an article appears on; the
detail page itself is shared, at ``/articles/<slug>``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import ArticleSection


class Article(Base, TimestampMixin):
    __tablename__ = "articles"
    __table_args__ = (
        # The public list is always (this section, published), newest first.
        Index("ix_articles_section_published", "section", "is_published", "published_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    section: Mapped[ArticleSection] = mapped_column(
        pg_enum(ArticleSection, "article_section"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
