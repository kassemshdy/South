"""The about page's team section: read by anyone, set by an administrator.

Six fixed slots, each a photograph and a short caption -- the owners'
layout. A slot with neither is simply not shown, so the section appears as
soon as one is filled and disappears again if all are emptied.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import select

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError
from app.models.enums import ImageKind
from app.models.team import TEAM_SLOTS, TeamMember
from app.schemas.team import TeamCaptionIn, TeamMemberOut
from app.services.images import ImageService
from app.storage.factory import get_storage

public_router = APIRouter(prefix="/team", tags=["team"])
admin_router = APIRouter(prefix="/admin/team", tags=["admin-team"])


def _out(slot: int, row: TeamMember | None) -> TeamMemberOut:
    if row is None:
        return TeamMemberOut(slot=slot)
    return TeamMemberOut(
        slot=slot,
        photo_url=row.photo_url,
        caption_ar=row.caption_ar,
        caption_en=row.caption_en,
        updated_at=row.updated_at,
    )


def _rows(db: DbSession) -> dict[int, TeamMember]:
    return {row.slot: row for row in db.execute(select(TeamMember)).scalars()}


def _known(slot: int) -> int:
    if slot not in TEAM_SLOTS:
        raise NotFoundError()
    return slot


def _slot(db: DbSession, slot: int) -> TeamMember:
    row = db.get(TeamMember, _known(slot))
    if row is None:
        row = TeamMember(slot=slot)
        db.add(row)
    return row


def _prune(db: DbSession, row: TeamMember) -> None:
    """A slot with nothing in it is no row at all."""
    if not (row.photo_url or row.caption_ar or row.caption_en):
        db.delete(row)


@public_router.get("", response_model=list[TeamMemberOut])
def team(db: DbSession) -> list[TeamMemberOut]:
    """The filled slots, in order."""
    rows = _rows(db)
    return [_out(slot, rows[slot]) for slot in TEAM_SLOTS if slot in rows]


@admin_router.get("", response_model=list[TeamMemberOut])
def list_team(db: DbSession, admin: AdminUser) -> list[TeamMemberOut]:
    """All six slots, filled or not."""
    rows = _rows(db)
    return [_out(slot, rows.get(slot)) for slot in TEAM_SLOTS]


@admin_router.put("/{slot}", response_model=TeamMemberOut)
def set_caption(
    slot: int, payload: TeamCaptionIn, db: DbSession, admin: AdminUser
) -> TeamMemberOut:
    row = _slot(db, slot)
    row.caption_ar, row.caption_en = payload.caption_ar, payload.caption_en
    _prune(db, row)
    db.commit()
    return _out(slot, db.get(TeamMember, slot))


@admin_router.post("/{slot}/photo", response_model=TeamMemberOut)
def set_photo(
    slot: int,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Team member photograph")],
) -> TeamMemberOut:
    _known(slot)
    service = ImageService(get_storage(), settings)
    stored = service.process_and_store(
        data=file.file.read(),
        content_type=file.content_type,
        owner_id=admin.id,
        kind=ImageKind.LOGO,
        prefix="team",
    )
    row = _slot(db, slot)
    previous = row.photo_storage_key
    row.photo_url, row.photo_storage_key = stored.url, stored.key
    db.commit()
    service.delete(previous)
    return _out(slot, db.get(TeamMember, slot))


@admin_router.delete("/{slot}/photo", response_model=TeamMemberOut)
def remove_photo(
    slot: int, db: DbSession, admin: AdminUser, settings: AppSettings
) -> TeamMemberOut:
    row = db.get(TeamMember, _known(slot))
    if row is not None:
        ImageService(get_storage(), settings).delete(row.photo_storage_key)
        row.photo_url = row.photo_storage_key = None
        _prune(db, row)
        db.commit()
    return _out(slot, db.get(TeamMember, slot))
