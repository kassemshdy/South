"""Administrator CRUD for articles, and the one cover image each carries.

Created as a draft (``is_published=False``); ``publish``/``unpublish`` are
separate calls from create/update, so writing a paragraph and saving it never
by itself puts it in front of a visitor. ``published_at`` is set once, on the
first publish, and never moved by a later republish -- a piece dated last
month should not read as new because an admin fixed a typo in it today.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.serializers import admin_article_out
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import ConflictError, NotFoundError
from app.core.i18n import translate
from app.models.article import Article
from app.models.enums import ArticleSection, ImageKind
from app.repositories.article import ArticleRepository
from app.schemas.article import AdminArticleOut, ArticleIn, ArticleUpdateIn
from app.schemas.common import MessageResponse
from app.services.images import ImageService
from app.services.slug import slugify_name, unique_slug
from app.storage.factory import get_storage

router = APIRouter(prefix="/admin/articles", tags=["admin-articles"])


def _get_or_404(repo: ArticleRepository, article_id: uuid.UUID) -> Article:
    article = repo.get(article_id)
    if article is None:
        raise NotFoundError("article.not_found")
    return article


@router.get("", response_model=list[AdminArticleOut])
def list_articles(
    db: DbSession,
    admin: AdminUser,
    section: Annotated[ArticleSection | None, Query()] = None,
) -> list[AdminArticleOut]:
    """Every article, draft and published alike, newest first."""
    return [
        admin_article_out(article) for article in ArticleRepository(db).list_all(section=section)
    ]


@router.post("", response_model=AdminArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleIn, db: DbSession, admin: AdminUser) -> AdminArticleOut:
    repo = ArticleRepository(db)
    slug = (
        slugify_name(payload.slug, fallback_prefix="article")
        if payload.slug
        else unique_slug(payload.title, repo.slug_exists, fallback_prefix="article")
    )
    if repo.slug_exists(slug):
        raise ConflictError("article.duplicate_slug", code="duplicate_slug")

    article = repo.add(
        Article(
            section=payload.section,
            slug=slug,
            title=payload.title,
            body=payload.body,
        )
    )
    db.commit()
    return admin_article_out(article)


@router.put("/{article_id}", response_model=AdminArticleOut)
def update_article(
    article_id: uuid.UUID, payload: ArticleUpdateIn, db: DbSession, admin: AdminUser
) -> AdminArticleOut:
    repo = ArticleRepository(db)
    article = _get_or_404(repo, article_id)

    data = payload.model_dump(exclude_unset=True)
    if data.get("slug"):
        slug = slugify_name(data["slug"], fallback_prefix="article")
        if repo.slug_exists(slug, exclude_id=article_id):
            raise ConflictError("article.duplicate_slug", code="duplicate_slug")
        data["slug"] = slug

    for field, value in data.items():
        setattr(article, field, value)
    db.commit()
    return admin_article_out(article)


@router.post("/{article_id}/publish", response_model=AdminArticleOut)
def publish_article(article_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminArticleOut:
    repo = ArticleRepository(db)
    article = _get_or_404(repo, article_id)
    article.is_published = True
    if article.published_at is None:
        article.published_at = datetime.now(UTC)
    db.commit()
    return admin_article_out(article)


@router.post("/{article_id}/unpublish", response_model=AdminArticleOut)
def unpublish_article(article_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminArticleOut:
    repo = ArticleRepository(db)
    article = _get_or_404(repo, article_id)
    article.is_published = False
    db.commit()
    return admin_article_out(article)


@router.post("/{article_id}/image", response_model=AdminArticleOut)
def upload_cover(
    article_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Cover image")],
) -> AdminArticleOut:
    repo = ArticleRepository(db)
    article = _get_or_404(repo, article_id)

    service = ImageService(get_storage(), settings)
    service.delete(article.cover_storage_key)

    data = file.file.read()
    stored = service.process_and_store(
        data=data,
        content_type=file.content_type,
        owner_id=article.id,
        kind=ImageKind.COVER,
        prefix="articles",
    )
    article.cover_url, article.cover_storage_key = stored.url, stored.key
    db.commit()
    return admin_article_out(article)


@router.delete("/{article_id}/image", response_model=AdminArticleOut)
def delete_cover(
    article_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> AdminArticleOut:
    repo = ArticleRepository(db)
    article = _get_or_404(repo, article_id)
    ImageService(get_storage(), settings).delete(article.cover_storage_key)
    article.cover_url, article.cover_storage_key = None, None
    db.commit()
    return admin_article_out(article)


@router.delete("/{article_id}", response_model=MessageResponse)
def delete_article(
    article_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    repo = ArticleRepository(db)
    article = _get_or_404(repo, article_id)
    ImageService(get_storage(), settings).delete(article.cover_storage_key)
    repo.delete(article)
    db.commit()
    return MessageResponse(message=translate("article.deleted"))
