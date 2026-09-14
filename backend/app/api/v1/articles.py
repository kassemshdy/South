"""Public reads for admin-authored articles.

Write-only from a visitor's side, same as everything else here: an article
is never owner- or visitor-submitted, so there is nothing on this router but
the two reads the ``/blog`` and ``/news`` pages, and the shared detail page,
need.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.serializers import article_out
from app.core.dependencies import DbSession
from app.core.errors import NotFoundError
from app.models.enums import ArticleSection
from app.repositories.article import ArticleRepository
from app.schemas.article import ArticleOut

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleOut])
def list_articles(db: DbSession, section: ArticleSection = Query(...)) -> list[ArticleOut]:
    return [article_out(article) for article in ArticleRepository(db).list_public(section)]


@router.get("/{slug}", response_model=ArticleOut)
def get_article(slug: str, db: DbSession) -> ArticleOut:
    article = ArticleRepository(db).get_public_by_slug(slug)
    if article is None:
        raise NotFoundError("article.not_found")
    return article_out(article)
