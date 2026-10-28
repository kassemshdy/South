"""Admin-authored articles: the content behind the "coming soon" blog and
news placeholders in the top nav.

Unlike a business or talent listing, nothing here is owner-submitted — only
an administrator can write one, so there is no PENDING/REJECTED moderation
state, just a draft/published switch. ``section`` decides which of the two
already-linked pages (``/blog`` or ``/news``) an article appears on; the
detail page itself is shared, at ``/articles/<slug>``.

An article may name a category and a place it is about; its page then ends
with the products and shops that match them. Both are optional and are
cleared, not cascaded, when the category or place is deleted.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import ArticleSection

if TYPE_CHECKING:
    from app.models.taxonomy import Category, Location


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

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[Category | None] = relationship(lazy="joined")
    location: Mapped[Location | None] = relationship(lazy="joined")
