"""Article data access. Makes no authorization decision -- ``list_all`` and
``get`` (inherited) return any status, and restricting a visitor to
published rows belongs to the public router's own methods here, not to a
caller-supplied flag that would be easy to leave off.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.article import Article
from app.models.enums import ArticleSection
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    model = Article

    def list_public(self, section: ArticleSection) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.section == section, Article.is_published.is_(True))
            .order_by(Article.published_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_public_by_slug(self, slug: str) -> Article | None:
        return self.db.execute(
            select(Article).where(Article.slug == slug, Article.is_published.is_(True))
        ).scalar_one_or_none()

    def list_all(self, *, section: ArticleSection | None = None) -> list[Article]:
        """Every article regardless of status -- the platform's own view."""
        stmt = select(Article)
        if section is not None:
            stmt = stmt.where(Article.section == section)
        stmt = stmt.order_by(Article.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Article.id).where(Article.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Article.id != exclude_id)
        return self.db.execute(stmt).first() is not None
