"""Collab reels: listed for anyone, managed by an administrator.

See ``app.models.reel``. The cover is uploaded separately from the link,
like a team photo, so a reel can be saved first and given its cover after.
A reel without a cover is not shown publicly: the home page row is covers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.core.uploads import read_at_most
from app.core.urls import instagram_post
from app.models.enums import ImageKind
from app.models.reel import Reel
from app.schemas.common import MessageResponse
from app.services.images import ImageService
from app.storage.factory import get_storage

public_router = APIRouter(prefix="/reels", tags=["reels"])
admin_router = APIRouter(prefix="/admin/reels", tags=["admin-reels"])


class ReelOut(BaseModel):
    id: uuid.UUID
    title: str | None
    instagram_kind: str
    instagram_code: str
    cover_url: str | None
    sort_order: int
    is_published: bool
    created_at: datetime


class ReelIn(BaseModel):
    instagram_url: str = Field(min_length=10, max_length=500)
    title: str | None = Field(default=None, max_length=160)
    sort_order: int = 0
    is_published: bool = True


class ReelUpdateIn(BaseModel):
    instagram_url: str | None = Field(default=None, min_length=10, max_length=500)
    title: str | None = Field(default=None, max_length=160)
    sort_order: int | None = None
    is_published: bool | None = None


def _out(reel: Reel) -> ReelOut:
    return ReelOut(
        id=reel.id,
        title=reel.title,
        instagram_kind=reel.instagram_kind,
        instagram_code=reel.instagram_code,
        cover_url=reel.cover_url,
        sort_order=reel.sort_order,
        is_published=reel.is_published,
        created_at=reel.created_at,
    )


def _load(db: DbSession, reel_id: uuid.UUID) -> Reel:
    reel = db.get(Reel, reel_id)
    if reel is None:
        raise NotFoundError()
    return reel


@public_router.get("", response_model=list[ReelOut])
def reels(db: DbSession) -> list[ReelOut]:
    rows = db.execute(
        select(Reel)
        .where(Reel.is_published.is_(True), Reel.cover_url.is_not(None))
        .order_by(Reel.sort_order, Reel.created_at.desc())
    ).scalars()
    return [_out(reel) for reel in rows]


@admin_router.get("", response_model=list[ReelOut])
def list_reels(db: DbSession, admin: AdminUser) -> list[ReelOut]:
    rows = db.execute(select(Reel).order_by(Reel.sort_order, Reel.created_at.desc())).scalars()
    return [_out(reel) for reel in rows]


@admin_router.post("", response_model=ReelOut, status_code=201)
def create_reel(payload: ReelIn, db: DbSession, admin: AdminUser) -> ReelOut:
    kind, code = instagram_post(payload.instagram_url)
    reel = Reel(
        title=(payload.title or "").strip() or None,
        instagram_kind=kind,
        instagram_code=code,
        sort_order=payload.sort_order,
        is_published=payload.is_published,
    )
    db.add(reel)
    db.commit()
    return _out(reel)


@admin_router.patch("/{reel_id}", response_model=ReelOut)
def update_reel(
    reel_id: uuid.UUID, payload: ReelUpdateIn, db: DbSession, admin: AdminUser
) -> ReelOut:
    reel = _load(db, reel_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("instagram_url"):
        reel.instagram_kind, reel.instagram_code = instagram_post(data["instagram_url"])
    if "title" in data:
        reel.title = (data["title"] or "").strip() or None
    if data.get("sort_order") is not None:
        reel.sort_order = data["sort_order"]
    if data.get("is_published") is not None:
        reel.is_published = data["is_published"]
    db.commit()
    return _out(reel)


@admin_router.post("/{reel_id}/cover", response_model=ReelOut)
def set_cover(
    reel_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Reel cover image")],
) -> ReelOut:
    reel = _load(db, reel_id)
    service = ImageService(get_storage(), settings)
    stored = service.process_and_store(
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        owner_id=admin.id,
        kind=ImageKind.COVER,
        prefix="reels",
    )
    previous = reel.cover_storage_key
    reel.cover_url, reel.cover_storage_key = stored.url, stored.key
    db.commit()
    service.delete(previous)
    return _out(reel)


@admin_router.delete("/{reel_id}", response_model=MessageResponse)
def delete_reel(
    reel_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    reel = _load(db, reel_id)
    key = reel.cover_storage_key
    db.delete(reel)
    db.commit()
    ImageService(get_storage(), settings).delete(key)
    return MessageResponse(message=translate("reel.deleted"))
