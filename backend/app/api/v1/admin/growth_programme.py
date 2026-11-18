"""The growth programme in admin (the owners' decision, 18 Nov 2026).

See ``app/models/growth.py``. Every staff role reads it; managers and
reviewers enrol a shop, move it along the steps and take it out.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.serializers import staff_name
from app.core.dependencies import AdminUser, DbSession
from app.core.errors import ConflictError, NotFoundError
from app.core.i18n import translate
from app.models.analytics import ListingViewDaily
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, ViewSubject
from app.models.growth_programme import GrowthEnrollment
from app.schemas.common import MessageResponse
from app.services.images import thumbnail_url

router = APIRouter(prefix="/admin/growth-programme", tags=["admin-growth"])

GrowthStage = Literal["CONTACTED", "CONTENT", "LISTING", "SHOPIFY", "ADS"]
WINDOW_DAYS = 30


class GrowthNumbers(BaseModel):
    instagram: int | None = None
    facebook: int | None = None
    views_30d: int = 0
    clicks_30d: int = 0


class GrowthShop(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: BusinessStatus
    category: str | None = None
    location: str | None = None
    logo_thumb_url: str | None = None
    products: int = 0
    shopify_connected: bool = False


class GrowthRowOut(BaseModel):
    shop: GrowthShop
    stage: GrowthStage
    stage_changed_at: datetime
    note: str | None = None
    enrolled_at: datetime
    enrolled_by_name: str | None = None
    before: GrowthNumbers
    now: GrowthNumbers


class GrowthEnrollIn(BaseModel):
    business_id: uuid.UUID
    note: str | None = Field(default=None, max_length=2000)


class GrowthUpdateIn(BaseModel):
    stage: GrowthStage | None = None
    note: str | None = Field(default=None, max_length=2000)


def _activity(db: DbSession, business_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    """Views and contact presses over the last 30 days, per shop."""
    if not business_ids:
        return {}
    since = date.today() - timedelta(days=WINDOW_DAYS)
    rows = db.execute(
        select(
            ListingViewDaily.subject_id,
            func.coalesce(func.sum(ListingViewDaily.views), 0),
            func.coalesce(func.sum(ListingViewDaily.contact_clicks), 0),
        )
        .where(
            ListingViewDaily.subject_type == ViewSubject.BUSINESS,
            ListingViewDaily.subject_id.in_(business_ids),
            ListingViewDaily.day >= since,
        )
        .group_by(ListingViewDaily.subject_id)
    ).all()
    return {row[0]: (int(row[1]), int(row[2])) for row in rows}


def _product_counts(db: DbSession, business_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not business_ids:
        return {}
    rows = db.execute(
        select(BusinessItem.business_id, func.count())
        .where(BusinessItem.business_id.in_(business_ids), BusinessItem.is_available.is_(True))
        .group_by(BusinessItem.business_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _rows(db: DbSession, enrollments: list[GrowthEnrollment]) -> list[GrowthRowOut]:
    ids = [row.business_id for row in enrollments]
    activity = _activity(db, ids)
    products = _product_counts(db, ids)
    out = []
    for row in enrollments:
        shop = row.business
        views, clicks = activity.get(shop.id, (0, 0))
        out.append(
            GrowthRowOut(
                shop=GrowthShop(
                    id=shop.id,
                    name=shop.name,
                    slug=shop.slug,
                    status=shop.status,
                    category=shop.category.name_ar if shop.category else None,
                    location=shop.location.name_ar if shop.location else None,
                    logo_thumb_url=thumbnail_url(shop.logo_url),
                    products=products.get(shop.id, 0),
                    shopify_connected=shop.store_link is not None,
                ),
                stage=row.stage,  # type: ignore[arg-type]
                stage_changed_at=row.stage_changed_at,
                note=row.note,
                enrolled_at=row.created_at,
                enrolled_by_name=staff_name(row.enrolled_by),
                before=GrowthNumbers(
                    instagram=row.baseline_instagram,
                    facebook=row.baseline_facebook,
                    views_30d=row.baseline_views_30d,
                    clicks_30d=row.baseline_clicks_30d,
                ),
                now=GrowthNumbers(
                    instagram=shop.instagram_followers,
                    facebook=shop.facebook_followers,
                    views_30d=views,
                    clicks_30d=clicks,
                ),
            )
        )
    return out


def _load(db: DbSession, business_id: uuid.UUID | None = None) -> list[GrowthEnrollment]:
    stmt = (
        select(GrowthEnrollment)
        .options(
            selectinload(GrowthEnrollment.business).selectinload(Business.category),
            selectinload(GrowthEnrollment.business).selectinload(Business.location),
            selectinload(GrowthEnrollment.business).selectinload(Business.store_link),
            selectinload(GrowthEnrollment.enrolled_by),
        )
        .order_by(GrowthEnrollment.created_at.asc())
    )
    if business_id is not None:
        stmt = stmt.where(GrowthEnrollment.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def _one(db: DbSession, business_id: uuid.UUID) -> GrowthRowOut:
    rows = _load(db, business_id)
    if not rows:
        raise NotFoundError("growthProgramme.not_enrolled")
    return _rows(db, rows)[0]


@router.get("", response_model=list[GrowthRowOut])
def list_growth(db: DbSession, admin: AdminUser) -> list[GrowthRowOut]:
    """Every shop in the programme, in the order they joined."""
    return _rows(db, _load(db))


@router.get("/{business_id}", response_model=GrowthRowOut)
def get_growth(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> GrowthRowOut:
    return _one(db, business_id)


@router.post("", response_model=GrowthRowOut, status_code=status.HTTP_201_CREATED)
def enroll(payload: GrowthEnrollIn, db: DbSession, admin: AdminUser) -> GrowthRowOut:
    """Put a shop in the programme, keeping its numbers today as "before"."""
    business = db.get(Business, payload.business_id)
    if business is None:
        raise NotFoundError("business.not_found")
    exists = db.execute(
        select(GrowthEnrollment.id).where(GrowthEnrollment.business_id == business.id)
    ).first()
    if exists is not None:
        raise ConflictError("growthProgramme.already_enrolled", code="already_enrolled")
    views, clicks = _activity(db, [business.id]).get(business.id, (0, 0))
    db.add(
        GrowthEnrollment(
            business_id=business.id,
            stage="CONTACTED",
            stage_changed_at=datetime.now(UTC),
            note=(payload.note or "").strip() or None,
            enrolled_by_id=admin.id,
            baseline_instagram=business.instagram_followers,
            baseline_facebook=business.facebook_followers,
            baseline_views_30d=views,
            baseline_clicks_30d=clicks,
        )
    )
    db.commit()
    return _one(db, business.id)


@router.put("/{business_id}", response_model=GrowthRowOut)
def update_growth(
    business_id: uuid.UUID, payload: GrowthUpdateIn, db: DbSession, admin: AdminUser
) -> GrowthRowOut:
    row = db.execute(
        select(GrowthEnrollment).where(GrowthEnrollment.business_id == business_id)
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("growthProgramme.not_enrolled")
    data = payload.model_dump(exclude_unset=True)
    if data.get("stage") and data["stage"] != row.stage:
        row.stage = data["stage"]
        row.stage_changed_at = datetime.now(UTC)
    if "note" in data:
        row.note = (data["note"] or "").strip() or None
    db.commit()
    return _one(db, business_id)


@router.delete("/{business_id}", response_model=MessageResponse)
def leave_growth(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    row = db.execute(
        select(GrowthEnrollment).where(GrowthEnrollment.business_id == business_id)
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("growthProgramme.not_enrolled")
    db.delete(row)
    db.commit()
    return MessageResponse(message=translate("growthProgramme.removed"))
