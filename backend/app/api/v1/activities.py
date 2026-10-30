"""Development activities: read by anyone, written by administrators.

The owners' ticket (29 Oct 2026): announcement photographs in a carousel
on the home page, each opening a page of its own, and the same list on a
page in the menu. An administrator keeps an activity or archives it; an
archived one, or one still without its photograph, is invisible to every
public route, its own address included.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Path, Query, UploadFile, status
from sqlalchemy import Select, select

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.i18n import translate
from app.core.uploads import read_at_most
from app.models.activity import Activity
from app.models.enums import ImageKind
from app.schemas.activity import ActivityIn, ActivityOut, ActivityUpdateIn, AdminActivityOut
from app.schemas.common import MessageResponse
from app.services.images import ImageService
from app.services.slug import slugify_name, unique_slug
from app.storage.factory import get_storage

public_router = APIRouter(tags=["activities"])
admin_router = APIRouter(prefix="/admin/activities", tags=["admin-activities"])

MAX_LISTED = 60


def _ordered(stmt: Select[tuple[Activity]]) -> Select[tuple[Activity]]:
    return stmt.order_by(Activity.sort_order.asc(), Activity.created_at.desc())


def _public() -> Select[tuple[Activity]]:
    return select(Activity).where(
        Activity.is_archived.is_(False), Activity.image_url.is_not(None)
    )


def _slug_exists(db: DbSession, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
    stmt = select(Activity.id).where(Activity.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Activity.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none() is not None


# --- Public ----------------------------------------------------------------


@public_router.get("/activities", response_model=list[ActivityOut])
def list_activities(
    db: DbSession, limit: Annotated[int, Query(ge=1, le=MAX_LISTED)] = MAX_LISTED
) -> list[ActivityOut]:
    """Kept activities, in the administrators' order and then newest first."""
    rows = db.execute(_ordered(_public()).limit(limit)).scalars()
    return [ActivityOut.model_validate(row) for row in rows]


@public_router.get("/activities/{slug}", response_model=ActivityOut)
def get_activity(slug: Annotated[str, Path(max_length=180)], db: DbSession) -> ActivityOut:
    activity = db.execute(_public().where(Activity.slug == slug)).scalar_one_or_none()
    if activity is None:
        raise NotFoundError("activity.not_found")
    return ActivityOut.model_validate(activity)


# --- Administrators --------------------------------------------------------


def _get_or_404(db: DbSession, activity_id: uuid.UUID) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise NotFoundError("activity.not_found")
    return activity


@admin_router.get("", response_model=list[AdminActivityOut])
def admin_list_activities(db: DbSession, admin: AdminUser) -> list[AdminActivityOut]:
    """Every activity, archived included, in the order the public sees."""
    rows = db.execute(_ordered(select(Activity))).scalars()
    return [AdminActivityOut.model_validate(row) for row in rows]


@admin_router.post("", response_model=AdminActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityIn, db: DbSession, admin: AdminUser) -> AdminActivityOut:
    slug = (
        slugify_name(payload.slug, fallback_prefix="activity")
        if payload.slug
        else unique_slug(payload.title, lambda s: _slug_exists(db, s), fallback_prefix="activity")
    )
    if _slug_exists(db, slug):
        raise ConflictError("activity.duplicate_slug", code="duplicate_slug")
    activity = Activity(slug=slug, **payload.model_dump(exclude={"slug"}))
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return AdminActivityOut.model_validate(activity)


@admin_router.put("/{activity_id}", response_model=AdminActivityOut)
def update_activity(
    activity_id: uuid.UUID, payload: ActivityUpdateIn, db: DbSession, admin: AdminUser
) -> AdminActivityOut:
    activity = _get_or_404(db, activity_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("slug"):
        slug = slugify_name(data["slug"], fallback_prefix="activity")
        if _slug_exists(db, slug, exclude_id=activity_id):
            raise ConflictError("activity.duplicate_slug", code="duplicate_slug")
        data["slug"] = slug
    else:
        data.pop("slug", None)
    for field in ("title", "body", "is_archived", "sort_order"):
        # Not nullable: an explicit null leaves the value as it was.
        if field in data and data[field] is None:
            data.pop(field)
    for field, value in data.items():
        setattr(activity, field, value)
    if activity.ends_at is not None and (
        activity.starts_at is None or activity.ends_at <= activity.starts_at
    ):
        raise ValidationError("activity.ends_before_start", code="invalid_dates")
    db.commit()
    db.refresh(activity)
    return AdminActivityOut.model_validate(activity)


@admin_router.post("/{activity_id}/image", response_model=AdminActivityOut)
def upload_activity_image(
    activity_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Announcement image")],
) -> AdminActivityOut:
    activity = _get_or_404(db, activity_id)
    service = ImageService(get_storage(), settings)
    service.delete(activity.image_storage_key)
    stored = service.process_and_store(
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        owner_id=activity.id,
        kind=ImageKind.COVER,
        prefix="activities",
    )
    activity.image_url, activity.image_storage_key = stored.url, stored.key
    db.commit()
    db.refresh(activity)
    return AdminActivityOut.model_validate(activity)


@admin_router.delete("/{activity_id}", response_model=MessageResponse)
def delete_activity(
    activity_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    activity = _get_or_404(db, activity_id)
    ImageService(get_storage(), settings).delete(activity.image_storage_key)
    db.delete(activity)
    db.commit()
    return MessageResponse(message=translate("activity.deleted"))
