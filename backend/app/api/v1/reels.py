"""The home page's reels: read by anyone, chosen by an administrator.

Each reel is a link to one Instagram post, embedded with Instagram's own
player (see ``app.core.instagram``). Only an administrator adds them -- there
is no owner submission and so no moderation state, only a published switch,
and a reel is saved hidden unless the administrator says otherwise. The row
appears on the home page only once the ``reels`` section is switched on at
``/admin/home-layout``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.instagram import InstagramPost, parse_instagram_post
from app.core.uploads import read_at_most
from app.models.enums import ImageKind
from app.models.reel import Reel
from app.schemas.reel import AdminReelOut, ReelIn, ReelOrderIn, ReelOut
from app.services.images import ImageService
from app.storage.factory import get_storage

public_router = APIRouter(prefix="/reels", tags=["reels"])
admin_router = APIRouter(prefix="/admin/reels", tags=["admin-reels"])

#: The row on the home page scrolls sideways; more than this is a list
#: nobody reaches the end of.
PUBLIC_LIMIT = 24

_ORDER = (Reel.sort_order.asc(), Reel.created_at.desc())


def _post(reel: Reel) -> InstagramPost:
    return InstagramPost(kind=reel.kind, code=reel.shortcode)


def _out(reel: Reel) -> ReelOut:
    post = _post(reel)
    return ReelOut(
        id=reel.id,
        url=post.url,
        embed_url=post.embed_url,
        caption_ar=reel.caption_ar,
        caption_en=reel.caption_en,
        cover_url=reel.cover_url,
    )


def _admin_out(reel: Reel) -> AdminReelOut:
    return AdminReelOut(
        **_out(reel).model_dump(),
        is_published=reel.is_published,
        sort_order=reel.sort_order,
        created_at=reel.created_at,
        updated_at=reel.updated_at,
    )


def _get(db: Session, reel_id: uuid.UUID) -> Reel:
    reel = db.get(Reel, reel_id)
    if reel is None:
        raise NotFoundError()
    return reel


def _apply(db: Session, reel: Reel, payload: ReelIn) -> None:
    post = parse_instagram_post(payload.url)
    if post is None:
        raise ValidationError("reel.invalid_url")
    taken = db.execute(
        select(Reel.id).where(Reel.shortcode == post.code, Reel.id != reel.id)
    ).scalar_one_or_none()
    if taken is not None:
        raise ConflictError("reel.duplicate")
    reel.kind, reel.shortcode = post.kind, post.code
    reel.caption_ar, reel.caption_en = payload.caption_ar, payload.caption_en
    reel.is_published = payload.is_published


@public_router.get("", response_model=list[ReelOut])
def reels(db: DbSession) -> list[ReelOut]:
    """The published reels, in the administrator's order."""
    rows = db.execute(
        select(Reel).where(Reel.is_published.is_(True)).order_by(*_ORDER).limit(PUBLIC_LIMIT)
    ).scalars()
    return [_out(reel) for reel in rows]


@admin_router.get("", response_model=list[AdminReelOut])
def list_reels(db: DbSession, admin: AdminUser) -> list[AdminReelOut]:
    return [_admin_out(reel) for reel in db.execute(select(Reel).order_by(*_ORDER)).scalars()]


@admin_router.post("", response_model=AdminReelOut, status_code=201)
def add_reel(payload: ReelIn, db: DbSession, admin: AdminUser) -> AdminReelOut:
    first = db.execute(select(func.min(Reel.sort_order))).scalar_one_or_none()
    reel = Reel(id=uuid.uuid4(), sort_order=(first or 0) - 1)
    _apply(db, reel, payload)
    db.add(reel)
    db.commit()
    db.refresh(reel)
    return _admin_out(reel)


# Before "/{reel_id}", so "order" is never read as an id.
@admin_router.put("/order", response_model=list[AdminReelOut])
def reorder_reels(payload: ReelOrderIn, db: DbSession, admin: AdminUser) -> list[AdminReelOut]:
    rows = {reel.id: reel for reel in db.execute(select(Reel)).scalars()}
    if len(payload.ids) != len(set(payload.ids)) or set(payload.ids) != set(rows):
        raise ValidationError("reel.order_mismatch")
    for position, reel_id in enumerate(payload.ids):
        rows[reel_id].sort_order = position
    db.commit()
    return list_reels(db, admin)


@admin_router.put("/{reel_id}", response_model=AdminReelOut)
def update_reel(
    reel_id: uuid.UUID, payload: ReelIn, db: DbSession, admin: AdminUser
) -> AdminReelOut:
    reel = _get(db, reel_id)
    _apply(db, reel, payload)
    db.commit()
    db.refresh(reel)
    return _admin_out(reel)


@admin_router.delete("/{reel_id}", response_model=list[AdminReelOut])
def delete_reel(
    reel_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> list[AdminReelOut]:
    """Removes the reel and its cover; answers with the reels that remain."""
    reel = _get(db, reel_id)
    key = reel.cover_storage_key
    db.delete(reel)
    db.commit()
    ImageService(get_storage(), settings).delete(key)
    return list_reels(db, admin)


@admin_router.post("/{reel_id}/cover", response_model=AdminReelOut)
def set_cover(
    reel_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="The reel card's cover photograph")],
) -> AdminReelOut:
    reel = _get(db, reel_id)
    service = ImageService(get_storage(), settings)
    # A tall card: the gallery's limits keep a 9:16 photo whole.
    stored = service.process_and_store(
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        owner_id=reel.id,
        kind=ImageKind.GALLERY,
        prefix="reels",
    )
    previous = reel.cover_storage_key
    reel.cover_url, reel.cover_storage_key = stored.url, stored.key
    db.commit()
    service.delete(previous)
    db.refresh(reel)
    return _admin_out(reel)


@admin_router.delete("/{reel_id}/cover", response_model=AdminReelOut)
def remove_cover(
    reel_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> AdminReelOut:
    reel = _get(db, reel_id)
    ImageService(get_storage(), settings).delete(reel.cover_storage_key)
    reel.cover_url = reel.cover_storage_key = None
    db.commit()
    db.refresh(reel)
    return _admin_out(reel)
