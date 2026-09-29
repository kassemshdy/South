"""The cover photograph of each public page: read by anyone, set by an admin.

A page with no cover set shows the site's default photograph, which the
frontend ships; this API only ever answers for the ones an administrator has
replaced. See ``PageCover``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import select

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError
from app.models.enums import ImageKind
from app.models.page_cover import PAGE_COVER_KEYS, PageCover
from app.schemas.page_cover import PageCoverOut
from app.services.images import ImageService
from app.storage.factory import get_storage

public_router = APIRouter(prefix="/page-covers", tags=["page-covers"])
admin_router = APIRouter(prefix="/admin/page-covers", tags=["admin-page-covers"])


def _all(db: DbSession) -> dict[str, PageCover]:
    return {row.page_key: row for row in db.execute(select(PageCover)).scalars()}


@public_router.get("", response_model=dict[str, str])
def page_covers(db: DbSession) -> dict[str, str]:
    """``{page_key: image_url}`` for every page whose cover has been set."""
    return {key: row.image_url for key, row in _all(db).items()}


@admin_router.get("", response_model=list[PageCoverOut])
def list_page_covers(db: DbSession, admin: AdminUser) -> list[PageCoverOut]:
    """Every page that can carry a cover, set or not, in a fixed order."""
    covers = _all(db)
    return [
        PageCoverOut(
            page_key=key,
            image_url=covers[key].image_url if key in covers else None,
            updated_at=covers[key].updated_at if key in covers else None,
        )
        for key in PAGE_COVER_KEYS
    ]


def _known(page_key: str) -> str:
    if page_key not in PAGE_COVER_KEYS:
        raise NotFoundError()
    return page_key


@admin_router.post("/{page_key}", response_model=PageCoverOut)
def set_page_cover(
    page_key: str,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Cover image")],
) -> PageCoverOut:
    _known(page_key)
    service = ImageService(get_storage(), settings)
    # Stored first and the old file removed after, so a rejected upload
    # leaves the page's current cover exactly as it was.
    stored = service.process_and_store(
        data=file.file.read(),
        content_type=file.content_type,
        owner_id=admin.id,
        kind=ImageKind.COVER,
        prefix="pages",
    )
    cover = db.get(PageCover, page_key)
    previous = cover.storage_key if cover else None
    if cover is None:
        cover = PageCover(page_key=page_key, image_url=stored.url, storage_key=stored.key)
        db.add(cover)
    else:
        cover.image_url, cover.storage_key = stored.url, stored.key
    db.commit()
    service.delete(previous)
    db.refresh(cover)
    return PageCoverOut(page_key=page_key, image_url=cover.image_url, updated_at=cover.updated_at)


@admin_router.delete("/{page_key}", response_model=PageCoverOut)
def reset_page_cover(
    page_key: str, db: DbSession, admin: AdminUser, settings: AppSettings
) -> PageCoverOut:
    """Back to the default photograph."""
    _known(page_key)
    cover = db.get(PageCover, page_key)
    if cover is not None:
        ImageService(get_storage(), settings).delete(cover.storage_key)
        db.delete(cover)
        db.commit()
    return PageCoverOut(page_key=page_key, image_url=None, updated_at=None)
