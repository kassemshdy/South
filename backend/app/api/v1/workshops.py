"""Workshops: read and signed up for by anyone, written by administrators.

The owners' request (29 Oct 2026). A workshop is published by hand like an
article and names the category and town it relates to, so the product and
article pages can show the upcoming ones that match. Signing up is the
partner form's shape: anonymous, a name and a phone, behind a per-address
and a site-wide limit and the captcha when one is configured. Who signed up
is read by administrators only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, File, Path, Query, UploadFile, status
from sqlalchemy import Select, func, select

from app.core.captcha import verify_captcha
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession
from app.core.errors import ConflictError, NotFoundError, RateLimitedError, ValidationError
from app.core.i18n import translate
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.uploads import read_at_most
from app.models.enums import ImageKind, WorkshopMode
from app.models.taxonomy import Category, Location
from app.models.workshop import Workshop, WorkshopRegistration
from app.schemas.common import MessageResponse
from app.schemas.workshop import (
    AdminWorkshopOut,
    WorkshopIn,
    WorkshopOut,
    WorkshopRegistrationIn,
    WorkshopRegistrationOut,
    WorkshopUpdateIn,
)
from app.services.images import ImageService
from app.services.slug import slugify_name, unique_slug
from app.storage.factory import get_storage

public_router = APIRouter(tags=["workshops"])
admin_router = APIRouter(prefix="/admin/workshops", tags=["admin-workshops"])

#: A workshop stays listed as upcoming until a day after it starts, so one
#: that started this morning is still findable tonight.
STILL_ON = timedelta(days=1)
MAX_LISTED = 60


def _now() -> datetime:
    return datetime.now(UTC)


def _public(db: DbSession) -> Select[tuple[Workshop]]:
    return select(Workshop).where(Workshop.is_published.is_(True))


def _slug_exists(db: DbSession, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
    stmt = select(Workshop.id).where(Workshop.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Workshop.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none() is not None


# --- Public ----------------------------------------------------------------


@public_router.get("/workshops", response_model=list[WorkshopOut])
def list_workshops(
    db: DbSession,
    when: Annotated[Literal["upcoming", "past"], Query()] = "upcoming",
    mode: Annotated[WorkshopMode | None, Query()] = None,
    category: Annotated[str | None, Query(max_length=140)] = None,
    location: Annotated[str | None, Query(max_length=140)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LISTED)] = MAX_LISTED,
) -> list[WorkshopOut]:
    """Published workshops: upcoming soonest first, or past latest first.

    ``category`` and ``location`` narrow to the workshops about that category
    or that town -- how the product and article pages find the related ones.
    A workshop that names neither is about everything and always matches.
    """
    cutoff = _now() - STILL_ON
    stmt = _public(db)
    if when == "upcoming":
        stmt = stmt.where(Workshop.starts_at >= cutoff).order_by(Workshop.starts_at.asc())
    else:
        stmt = stmt.where(Workshop.starts_at < cutoff).order_by(Workshop.starts_at.desc())
    if mode is not None:
        stmt = stmt.where(Workshop.mode == mode)
    if category:
        category_id = select(Category.id).where(Category.slug == category).scalar_subquery()
        stmt = stmt.where(
            (Workshop.category_id == category_id) | Workshop.category_id.is_(None)
        )
    if location:
        place = select(Location.id).where(Location.slug == location).scalar_subquery()
        parent = select(Location.parent_id).where(Location.slug == location).scalar_subquery()
        stmt = stmt.where(
            Workshop.location_id.in_([place, parent])
            | Workshop.location_id.is_(None)
            | (Workshop.mode == WorkshopMode.ONLINE)
        )
    return [
        WorkshopOut.model_validate(workshop)
        for workshop in db.execute(stmt.limit(limit)).unique().scalars()
    ]


@public_router.get("/workshops/{slug}", response_model=WorkshopOut)
def get_workshop(slug: Annotated[str, Path(max_length=180)], db: DbSession) -> WorkshopOut:
    workshop = db.execute(_public(db).where(Workshop.slug == slug)).unique().scalar_one_or_none()
    if workshop is None:
        raise NotFoundError("workshop.not_found")
    return WorkshopOut.model_validate(workshop)


@public_router.post(
    "/workshops/{slug}/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_for_workshop(
    slug: Annotated[str, Path(max_length=180)],
    payload: WorkshopRegistrationIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> MessageResponse:
    workshop = db.execute(_public(db).where(Workshop.slug == slug)).unique().scalar_one_or_none()
    if workshop is None:
        raise NotFoundError("workshop.not_found")
    if workshop.starts_at < _now():
        raise ValidationError("workshop.already_started", code="workshop_started")

    limiter = DatabaseRateLimiter(db)
    if client_ip:
        per_ip = limiter.hit(
            RateLimitRule(
                bucket="workshop_ip",
                limit=settings.partner_per_ip_limit,
                window_seconds=settings.partner_per_ip_window_seconds,
            ),
            client_ip,
        )
        if not per_ip.allowed:
            raise RateLimitedError(per_ip.retry_after_seconds, "workshop.rate_limited")
    overall = limiter.hit(
        RateLimitRule(
            bucket="workshop_global",
            limit=settings.partner_per_day_limit,
            window_seconds=86400,
        ),
        "all",
    )
    if not overall.allowed:
        raise RateLimitedError(overall.retry_after_seconds, "workshop.rate_limited")
    verify_captcha(payload.captcha_token, settings, client_ip=client_ip)

    db.add(
        WorkshopRegistration(
            workshop_id=workshop.id,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
        )
    )
    db.commit()
    return MessageResponse(message=translate("workshop.registered"))


# --- Administrators --------------------------------------------------------


def _get_or_404(db: DbSession, workshop_id: uuid.UUID) -> Workshop:
    workshop = db.get(Workshop, workshop_id)
    if workshop is None:
        raise NotFoundError("workshop.not_found")
    return workshop


def _check_related(
    db: DbSession, category_id: uuid.UUID | None, location_id: uuid.UUID | None
) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise NotFoundError("taxonomy.category.not_found")
    if location_id is not None and db.get(Location, location_id) is None:
        raise NotFoundError("taxonomy.location.not_found")


def _admin_out(db: DbSession, workshop: Workshop) -> AdminWorkshopOut:
    count = db.execute(
        select(func.count())
        .select_from(WorkshopRegistration)
        .where(WorkshopRegistration.workshop_id == workshop.id)
    ).scalar_one()
    return AdminWorkshopOut.model_validate(workshop).model_copy(
        update={"registration_count": int(count)}
    )


@admin_router.get("", response_model=list[AdminWorkshopOut])
def admin_list_workshops(db: DbSession, admin: AdminUser) -> list[AdminWorkshopOut]:
    """Every workshop, drafts included, the latest first."""
    workshops = db.execute(select(Workshop).order_by(Workshop.starts_at.desc())).unique()
    return [_admin_out(db, workshop) for workshop in workshops.scalars()]


@admin_router.post("", response_model=AdminWorkshopOut, status_code=status.HTTP_201_CREATED)
def create_workshop(payload: WorkshopIn, db: DbSession, admin: AdminUser) -> AdminWorkshopOut:
    slug = (
        slugify_name(payload.slug, fallback_prefix="workshop")
        if payload.slug
        else unique_slug(
            payload.title, lambda s: _slug_exists(db, s), fallback_prefix="workshop"
        )
    )
    if _slug_exists(db, slug):
        raise ConflictError("workshop.duplicate_slug", code="duplicate_slug")
    _check_related(db, payload.category_id, payload.location_id)
    workshop = Workshop(slug=slug, **payload.model_dump(exclude={"slug"}))
    db.add(workshop)
    db.commit()
    db.refresh(workshop)
    return _admin_out(db, workshop)


@admin_router.post("/examples", response_model=list[AdminWorkshopOut])
def add_example_workshops(db: DbSession, admin: AdminUser) -> list[AdminWorkshopOut]:
    """The example online workshops, added as drafts.

    Each is a starting point -- a date a few weeks out, no trainer, free --
    for an administrator to complete and publish; none reaches a visitor on
    its own. An example whose slug is already taken is skipped, so pressing
    the button twice adds nothing the second time.
    """
    from scripts.seed_data import WORKSHOPS

    evening = _now().replace(hour=16, minute=0, second=0, microsecond=0)
    added: list[Workshop] = []
    for example in WORKSHOPS:
        if _slug_exists(db, example["slug"]):
            continue
        starts_at = evening + timedelta(days=example["days_from_now"])
        workshop = Workshop(
            slug=example["slug"],
            title=example["title"],
            description=example["description"],
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=example["duration_minutes"]),
            mode=WorkshopMode.ONLINE,
        )
        db.add(workshop)
        added.append(workshop)
    db.commit()
    return [_admin_out(db, workshop) for workshop in added]


@admin_router.put("/{workshop_id}", response_model=AdminWorkshopOut)
def update_workshop(
    workshop_id: uuid.UUID, payload: WorkshopUpdateIn, db: DbSession, admin: AdminUser
) -> AdminWorkshopOut:
    workshop = _get_or_404(db, workshop_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("slug"):
        slug = slugify_name(data["slug"], fallback_prefix="workshop")
        if _slug_exists(db, slug, exclude_id=workshop_id):
            raise ConflictError("workshop.duplicate_slug", code="duplicate_slug")
        data["slug"] = slug
    _check_related(db, data.get("category_id"), data.get("location_id"))
    for field, value in data.items():
        setattr(workshop, field, value)
    if workshop.ends_at is not None and workshop.ends_at <= workshop.starts_at:
        raise ValidationError("workshop.ends_before_start", code="invalid_dates")
    db.commit()
    db.refresh(workshop)
    return _admin_out(db, workshop)


@admin_router.post("/{workshop_id}/publish", response_model=AdminWorkshopOut)
def publish_workshop(workshop_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminWorkshopOut:
    workshop = _get_or_404(db, workshop_id)
    workshop.is_published = True
    db.commit()
    return _admin_out(db, workshop)


@admin_router.post("/{workshop_id}/unpublish", response_model=AdminWorkshopOut)
def unpublish_workshop(
    workshop_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> AdminWorkshopOut:
    workshop = _get_or_404(db, workshop_id)
    workshop.is_published = False
    db.commit()
    return _admin_out(db, workshop)


@admin_router.post("/{workshop_id}/image", response_model=AdminWorkshopOut)
def upload_workshop_cover(
    workshop_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Cover image")],
) -> AdminWorkshopOut:
    workshop = _get_or_404(db, workshop_id)
    service = ImageService(get_storage(), settings)
    service.delete(workshop.cover_storage_key)
    stored = service.process_and_store(
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        owner_id=workshop.id,
        kind=ImageKind.COVER,
        prefix="workshops",
    )
    workshop.cover_url, workshop.cover_storage_key = stored.url, stored.key
    db.commit()
    return _admin_out(db, workshop)


@admin_router.delete("/{workshop_id}/image", response_model=AdminWorkshopOut)
def delete_workshop_cover(
    workshop_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> AdminWorkshopOut:
    workshop = _get_or_404(db, workshop_id)
    ImageService(get_storage(), settings).delete(workshop.cover_storage_key)
    workshop.cover_url, workshop.cover_storage_key = None, None
    db.commit()
    return _admin_out(db, workshop)


@admin_router.delete("/{workshop_id}", response_model=MessageResponse)
def delete_workshop(
    workshop_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    workshop = _get_or_404(db, workshop_id)
    ImageService(get_storage(), settings).delete(workshop.cover_storage_key)
    db.delete(workshop)
    db.commit()
    return MessageResponse(message=translate("workshop.deleted"))


@admin_router.get("/{workshop_id}/registrations", response_model=list[WorkshopRegistrationOut])
def list_registrations(
    workshop_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> list[WorkshopRegistrationOut]:
    """Who signed up, the latest first (the owners' decision, 30 Oct 2026)."""
    _get_or_404(db, workshop_id)
    rows = db.execute(
        select(WorkshopRegistration)
        .where(WorkshopRegistration.workshop_id == workshop_id)
        .order_by(WorkshopRegistration.created_at.desc())
    ).scalars()
    return [WorkshopRegistrationOut.model_validate(row) for row in rows]
