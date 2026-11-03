"""Development activities: read by anyone, written by administrators.

The owners' ticket (29 Oct 2026): announcement photographs in a carousel
on the home page, each opening a page of its own, and the same list on a
page in the menu. An administrator keeps an activity or archives it; an
archived one, or one still without its photograph, is invisible to every
public route, its own address included.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Path, Query, UploadFile, status
from sqlalchemy import Select, case, func, select

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.i18n import translate
from app.core.uploads import read_at_most
from app.models.activity import Activity, CarouselSlide
from app.models.enums import ImageKind
from app.schemas.activity import (
    ActivityIn,
    ActivityOut,
    ActivityUpdateIn,
    AdminActivityOut,
    AdminCarouselOut,
    AdminCarouselSlideOut,
    CarouselAddActivityIn,
    CarouselOrderIn,
    CarouselSettingsIn,
    CarouselSlideOut,
    CarouselSlideUpdateIn,
    _http_url,
)
from app.schemas.common import MessageResponse
from app.services.carousel import CarouselService, has_ended
from app.services.images import ImageService
from app.services.slug import slugify_name, unique_slug
from app.storage.factory import get_storage

public_router = APIRouter(tags=["activities"])
admin_router = APIRouter(prefix="/admin/activities", tags=["admin-activities"])
carousel_admin_router = APIRouter(prefix="/admin/carousel", tags=["admin-carousel"])

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
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=MAX_LISTED)] = MAX_LISTED,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> list[ActivityOut]:
    """Kept activities: upcoming and current first, soonest first; then
    those without dates; then finished ones, newest first (the owners'
    ticket, 31 Oct 2026). ``offset`` pages through them for "load more"."""
    now = datetime.now(UTC)
    end = func.coalesce(Activity.ends_at, Activity.starts_at)
    group = case((end.is_(None), 1), (end >= now, 0), else_=2)
    stmt = (
        _public()
        .order_by(
            group,
            case((end >= now, Activity.starts_at)).asc().nulls_last(),
            func.coalesce(end, Activity.created_at).desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return [ActivityOut.model_validate(row) for row in db.execute(stmt).scalars()]


@public_router.get("/carousel", response_model=list[CarouselSlideOut])
def carousel(db: DbSession) -> list[CarouselSlideOut]:
    """The announcements carousel, in the administrators' order: the home
    page and /activities read the same list."""
    return [_public_slide(slide) for slide in CarouselService(db).visible()]


def _public_slide(slide: CarouselSlide) -> CarouselSlideOut:
    if slide.activity is not None:
        return CarouselSlideOut(
            id=slide.id,
            title=slide.activity.title,
            image_url=slide.activity.image_url or "",
            href=f"/activities/{slide.activity.slug}",
        )
    return CarouselSlideOut(
        id=slide.id,
        title=slide.title,
        image_url=slide.image_url or "",
        href=slide.link_url,
        external=bool(slide.link_url),
    )


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


def _admin_out(db: DbSession, activity: Activity) -> AdminActivityOut:
    out = AdminActivityOut.model_validate(activity)
    out.in_carousel = CarouselService(db).slide_for(activity.id) is not None
    return out


@admin_router.get("", response_model=list[AdminActivityOut])
def admin_list_activities(db: DbSession, admin: AdminUser) -> list[AdminActivityOut]:
    """Every activity, archived included, newest first."""
    rows = list(db.execute(_ordered(select(Activity))).scalars())
    in_carousel = set(
        db.execute(
            select(CarouselSlide.activity_id).where(CarouselSlide.activity_id.is_not(None))
        ).scalars()
    )
    outs = [AdminActivityOut.model_validate(row) for row in rows]
    for out in outs:
        out.in_carousel = out.id in in_carousel
    return outs


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
    return _admin_out(db, activity)


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
    in_carousel = data.pop("in_carousel", None)
    for field in ("title", "body", "is_archived", "sort_order", "kind", "show_calendar"):
        # Not nullable: an explicit null leaves the value as it was.
        if field in data and data[field] is None:
            data.pop(field)
    for field, value in data.items():
        setattr(activity, field, value)
    if activity.ends_at is not None and (
        activity.starts_at is None or activity.ends_at <= activity.starts_at
    ):
        raise ValidationError("activity.ends_before_start", code="invalid_dates")
    carousel = CarouselService(db)
    if activity.is_archived or in_carousel is False:
        # Archived activities leave the carousel; the list keeps them.
        carousel.remove_activity(activity, commit=False)
    elif in_carousel:
        carousel.add_activity(activity, commit=False)
    db.commit()
    db.refresh(activity)
    return _admin_out(db, activity)


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
    first_photo = activity.image_url is None
    activity.image_url, activity.image_storage_key = stored.url, stored.key
    if first_photo and not activity.is_archived:
        # Its first photograph puts it first in the carousel, with no extra
        # step; taken out later, it stays out.
        CarouselService(db).add_activity(activity, commit=False)
    db.commit()
    db.refresh(activity)
    return _admin_out(db, activity)


@admin_router.delete("/{activity_id}", response_model=MessageResponse)
def delete_activity(
    activity_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    activity = _get_or_404(db, activity_id)
    ImageService(get_storage(), settings).delete(activity.image_storage_key)
    db.delete(activity)
    db.commit()
    return MessageResponse(message=translate("activity.deleted"))


# --- The carousel manager --------------------------------------------------


def _admin_slide(slide: CarouselSlide, now: datetime) -> AdminCarouselSlideOut:
    activity = slide.activity
    if activity is not None:
        hidden: Literal["ARCHIVED", "NO_IMAGE", "ENDED"] | None = None
        if activity.is_archived:
            hidden = "ARCHIVED"
        elif not activity.image_url:
            hidden = "NO_IMAGE"
        elif has_ended(activity, now):
            hidden = "ENDED"
        return AdminCarouselSlideOut(
            id=slide.id,
            kind="ACTIVITY",
            position=slide.position,
            activity_id=activity.id,
            title=activity.title,
            image_url=activity.image_url or "",
            href=f"/activities/{activity.slug}",
            ends_at=activity.ends_at,
            hidden_reason=hidden,
        )
    return AdminCarouselSlideOut(
        id=slide.id,
        kind="CUSTOM",
        position=slide.position,
        title=slide.title,
        image_url=slide.image_url or "",
        href=slide.link_url,
        external=bool(slide.link_url),
        link_url=slide.link_url,
    )


def _carousel_out(db: DbSession) -> AdminCarouselOut:
    service = CarouselService(db)
    now = datetime.now(UTC)
    autoremove = service.autoremove_expired()
    slides = [_admin_slide(slide, now) for slide in service.all()]
    if not autoremove:
        for slide in slides:
            if slide.hidden_reason == "ENDED":
                slide.hidden_reason = None
    return AdminCarouselOut(slides=slides, autoremove_expired=autoremove)


@carousel_admin_router.get("", response_model=AdminCarouselOut)
def admin_carousel(db: DbSession, admin: AdminUser) -> AdminCarouselOut:
    """Every slide in order, with why a visitor does not see one, if not."""
    return _carousel_out(db)


@carousel_admin_router.put("/order", response_model=AdminCarouselOut)
def reorder_carousel(
    payload: CarouselOrderIn, db: DbSession, admin: AdminUser
) -> AdminCarouselOut:
    CarouselService(db).reorder(payload.slide_ids)
    return _carousel_out(db)


@carousel_admin_router.post("/activities", response_model=AdminCarouselOut)
def add_activity_slide(
    payload: CarouselAddActivityIn, db: DbSession, admin: AdminUser
) -> AdminCarouselOut:
    activity = _get_or_404(db, payload.activity_id)
    if activity.is_archived:
        raise ValidationError("carousel.archived", code="carousel_archived")
    CarouselService(db).add_activity(activity)
    return _carousel_out(db)


@carousel_admin_router.post("/custom", response_model=AdminCarouselOut)
def add_custom_slide(
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Slide image")],
    title: Annotated[str | None, Form(max_length=200)] = None,
    link_url: Annotated[str | None, Form(max_length=500)] = None,
) -> AdminCarouselOut:
    """A slide of its own: an image, an optional title and an optional link."""
    try:
        link = _http_url(link_url)
    except ValueError as exc:
        raise ValidationError("activity.link_scheme", code="invalid_url") from exc
    stored = ImageService(get_storage(), settings).process_and_store(
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        owner_id=uuid.uuid4(),
        kind=ImageKind.COVER,
        prefix="carousel",
    )
    CarouselService(db).add_custom(
        image_url=stored.url,
        image_storage_key=stored.key,
        title=(title or "").strip() or None,
        link_url=link,
    )
    return _carousel_out(db)


@carousel_admin_router.put("/settings", response_model=AdminCarouselOut)
def carousel_settings(
    payload: CarouselSettingsIn, db: DbSession, admin: AdminUser
) -> AdminCarouselOut:
    CarouselService(db).set_autoremove_expired(payload.autoremove_expired)
    return _carousel_out(db)


@carousel_admin_router.put("/{slide_id}", response_model=AdminCarouselOut)
def update_custom_slide(
    slide_id: uuid.UUID, payload: CarouselSlideUpdateIn, db: DbSession, admin: AdminUser
) -> AdminCarouselOut:
    """A custom slide's title and link; an activity's slide reads its own."""
    slide = CarouselService(db).get(slide_id)
    if slide.activity_id is not None:
        raise ValidationError("carousel.not_custom", code="carousel_not_custom")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(slide, field, value)
    db.commit()
    return _carousel_out(db)


@carousel_admin_router.delete("/{slide_id}", response_model=AdminCarouselOut)
def delete_slide(
    slide_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> AdminCarouselOut:
    """Out of the carousel. An activity stays on the activities list."""
    service = CarouselService(db)
    key = service.delete(service.get(slide_id))
    if key:
        ImageService(get_storage(), settings).delete(key)
    return _carousel_out(db)
