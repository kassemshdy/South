"""Platform statistics and the administrator's user list."""

from __future__ import annotations

import math
import statistics
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import aliased

from app.api.serializers import admin_user
from app.core.dependencies import AdminUser, DbSession
from app.core.pins import in_lebanon
from app.models.analytics import ListingViewDaily
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, TestimonialStatus, UserRole, ViewSubject
from app.models.order import Order
from app.models.talent import TalentProfile
from app.models.taxonomy import Category, Location
from app.models.testimonial import Testimonial
from app.models.user import User
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.user import UserRepository
from app.schemas.common import (
    ContactedShopOut,
    GrowthResponse,
    GrowthSeries,
    MapPointOut,
    PageMeta,
    PaginatedResponse,
    StatsResponse,
    StrayPinOut,
)
from app.schemas.growth_report import GrowthPlanIn, GrowthPlanOut, GrowthReportOut
from app.schemas.moderation import AdminUserOut
from app.services.growth_report import GrowthReportService

router = APIRouter(prefix="/admin", tags=["admin-stats"])

Counted = type[Business] | type[TalentProfile] | type[BusinessItem] | type[Order]


@router.get("/stats", response_model=StatsResponse)
def platform_stats(db: DbSession, admin: AdminUser) -> StatsResponse:
    businesses = BusinessRepository(db)
    counts = businesses.count_by_status()
    talent_counts = TalentRepository(db).count_by_status()
    users = UserRepository(db)
    total_items = int(
        db.execute(select(func.count()).select_from(BusinessItem)).scalar_one()
    )

    return StatsResponse(
        total_businesses=sum(counts.values()),
        pending_businesses=counts.get(BusinessStatus.PENDING_REVIEW, 0),
        approved_businesses=counts.get(BusinessStatus.APPROVED, 0),
        rejected_businesses=counts.get(BusinessStatus.REJECTED, 0),
        suspended_businesses=counts.get(BusinessStatus.SUSPENDED, 0),
        draft_businesses=counts.get(BusinessStatus.DRAFT, 0),
        total_users=users.count(),
        total_admins=users.count_by_role(UserRole.ADMIN),
        total_items=total_items,
        total_talents=sum(talent_counts.values()),
        pending_talents=talent_counts.get(BusinessStatus.PENDING_REVIEW, 0),
        approved_talents=talent_counts.get(BusinessStatus.APPROVED, 0),
        shops_with_products=businesses.shops_with_products_count(),
        pending_testimonials=int(
            db.execute(
                select(func.count())
                .select_from(Testimonial)
                .where(Testimonial.status == TestimonialStatus.PENDING_REVIEW)
            ).scalar_one()
        ),
    )


@router.get("/stats/map", response_model=list[MapPointOut])
def listings_map(db: DbSession, admin: AdminUser) -> list[MapPointOut]:
    """Every pinned shop and service profile, in any status, for the
    dashboard's map (the owners' request, 8 Nov 2026). Staff only, so a
    service provider's exact pin -- shown publicly only as an area -- is
    fine here."""
    points: list[MapPointOut] = []
    shops = db.execute(
        select(
            Business.id,
            Business.name,
            Business.status,
            Category.name_ar,
            Business.latitude,
            Business.longitude,
        )
        .outerjoin(Category, Business.category_id == Category.id)
        .where(Business.latitude.is_not(None), Business.longitude.is_not(None))
    ).all()
    points += [
        MapPointOut(
            kind="business",
            id=row[0],
            name=row[1],
            status=row[2].value,
            category=row[3],
            latitude=float(row[4]),
            longitude=float(row[5]),
        )
        for row in shops
    ]
    people = db.execute(
        select(
            TalentProfile.id,
            TalentProfile.display_name,
            TalentProfile.status,
            TalentProfile.latitude,
            TalentProfile.longitude,
        ).where(TalentProfile.latitude.is_not(None), TalentProfile.longitude.is_not(None))
    ).all()
    points += [
        MapPointOut(
            kind="service",
            id=row[0],
            name=row[1],
            status=row[2].value,
            latitude=float(row[3]),
            longitude=float(row[4]),
        )
        for row in people
    ]
    return points


@router.get("/stats/contacted-shops", response_model=list[ContactedShopOut])
def contacted_shops(
    db: DbSession,
    admin: AdminUser,
    days: Annotated[int, Query(ge=1, le=365)] = 90,
) -> list[ContactedShopOut]:
    """Published shops that visitors reached through the site in the last
    ``days`` days -- a WhatsApp or call press, or an order -- most first.

    The counter holds a number per shop per day and nothing about who
    pressed (see ``ListingViewDaily``), so this names shops, never visitors.
    """
    since = datetime.now(UTC).date() - timedelta(days=days - 1)
    clicks = {
        shop_id: (int(total), last)
        for shop_id, total, last in db.execute(
            select(
                ListingViewDaily.subject_id,
                func.sum(ListingViewDaily.contact_clicks),
                func.max(ListingViewDaily.day),
            )
            .where(
                ListingViewDaily.subject_type == ViewSubject.BUSINESS,
                ListingViewDaily.day >= since,
                ListingViewDaily.contact_clicks > 0,
            )
            .group_by(ListingViewDaily.subject_id)
        ).all()
    }
    orders = {
        shop_id: (int(total), last)
        for shop_id, total, last in db.execute(
            select(
                Order.business_id,
                func.count(Order.id),
                func.max(cast(Order.created_at, Date)),
            )
            .where(Order.created_at >= datetime.combine(since, time.min, tzinfo=UTC))
            .group_by(Order.business_id)
        ).all()
    }
    ids = set(clicks) | set(orders)
    if not ids:
        return []
    rows = db.execute(
        select(Business.id, Business.name, Business.slug, Business.logo_url, User.phone_number)
        .join(User, User.id == Business.owner_id)
        .where(Business.id.in_(ids), Business.status == BusinessStatus.APPROVED)
    ).all()
    shops = []
    for row in rows:
        click_count, click_day = clicks.get(row.id, (0, None))
        order_count, order_day = orders.get(row.id, (0, None))
        last = max((d for d in (click_day, order_day) if d is not None), default=None)
        shops.append(
            ContactedShopOut(
                id=row.id,
                name=row.name,
                slug=row.slug,
                logo_url=row.logo_url,
                contact_clicks=click_count,
                orders=order_count,
                last_contact=last,
                owner_phone=row.phone_number,
            )
        )
    shops.sort(
        key=lambda shop: (shop.orders + shop.contact_clicks, shop.last_contact or since),
        reverse=True,
    )
    return shops


#: How far a pin may sit from the middle of its district's other pins
#: before staff are asked to look at it. A district in the South is about
#: 20-30 km across, so a pin further than this is in another district.
FAR_PIN_KM = 25
#: A district needs this many pins before its middle means anything.
FAR_PIN_MIN_PEERS = 3


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance on a flat map: accurate to a few percent across Lebanon."""
    return math.hypot((lat1 - lat2) * 111.0, (lng1 - lng2) * 111.0 * math.cos(math.radians(33.6)))


@router.get("/stats/stray-pins", response_model=list[StrayPinOut])
def stray_pins(db: DbSession, admin: AdminUser) -> list[StrayPinOut]:
    """Every shop and service profile, whatever its status, whose pin needs
    a person to look at it: outside Lebanon (saved before pins were checked,
    and hidden from the public maps), or inside it but far from the other
    pins of its district (9 Nov 2026). Outside first, then furthest first."""
    district = aliased(Location)
    rows: list[tuple[str, uuid.UUID, str, str | None, str | None, float, float]] = []
    for kind, model, name_col in (
        ("business", Business, Business.name),
        ("service", TalentProfile, TalentProfile.display_name),
    ):
        for listing_id, name, town, district_name, lat, lng in db.execute(
            select(
                model.id,
                name_col,
                Location.name_ar,
                # A town's district; a listing placed on a district itself
                # counts with that district.
                func.coalesce(district.name_ar, Location.name_ar),
                model.latitude,
                model.longitude,
            )
            .outerjoin(Location, model.location_id == Location.id)
            .outerjoin(district, Location.parent_id == district.id)
            .where(model.latitude.is_not(None), model.longitude.is_not(None))
        ).all():
            rows.append((kind, listing_id, name, town, district_name, float(lat), float(lng)))

    inside = [row for row in rows if in_lebanon(row[5], row[6])]
    by_district: dict[str, list[tuple[float, float]]] = {}
    for row in inside:
        if row[4]:
            by_district.setdefault(row[4], []).append((row[5], row[6]))
    middle = {
        name: (statistics.median(p[0] for p in pins), statistics.median(p[1] for p in pins))
        for name, pins in by_district.items()
        if len(pins) >= FAR_PIN_MIN_PEERS
    }

    outside: list[StrayPinOut] = []
    far: list[StrayPinOut] = []
    for kind, listing_id, name, town, district_name, lat, lng in rows:
        common = {
            "kind": kind,
            "id": listing_id,
            "name": name,
            "town": town,
            "latitude": lat,
            "longitude": lng,
        }
        if not in_lebanon(lat, lng):
            outside.append(StrayPinOut(**common, reason="outside"))  # type: ignore[arg-type]
        elif district_name in middle:
            km = _km(lat, lng, *middle[district_name])
            if km > FAR_PIN_KM:
                far.append(
                    StrayPinOut(**common, reason="far", km_from_district=round(km))  # type: ignore[arg-type]
                )
    far.sort(key=lambda pin: pin.km_from_district or 0, reverse=True)
    return outside + far


@router.get("/stats/growth", response_model=GrowthResponse)
def platform_growth(
    db: DbSession,
    admin: AdminUser,
    days: Annotated[int, Query(ge=7, le=180)] = 30,
) -> GrowthResponse:
    """Running totals per day, for the dashboard's growth chart.

    Every row whatever its status -- pending and rejected applications are
    part of how the platform grew -- counted by the day it was created, in
    UTC. Anything older than the window is the first day's starting total.
    """
    today = datetime.now(UTC).date()
    window = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    start = datetime.combine(window[0], time.min, tzinfo=UTC)

    def running(model: Counted) -> list[int]:
        before = int(
            db.execute(
                select(func.count()).select_from(model).where(model.created_at < start)
            ).scalar_one()
        )
        day = cast(model.created_at, Date)
        per_day: dict[date, int] = {
            created: int(count)
            for created, count in db.execute(
                select(day, func.count()).where(model.created_at >= start).group_by(day)
            ).all()
        }
        totals: list[int] = []
        for current in window:
            before += int(per_day.get(current, 0))
            totals.append(before)
        return totals

    return GrowthResponse(
        days=window,
        totals=GrowthSeries(
            businesses=running(Business),
            talents=running(TalentProfile),
            products=running(BusinessItem),
            orders=running(Order),
        ),
    )


@router.get("/growth-report", response_model=GrowthReportOut)
def growth_report(db: DbSession, admin: AdminUser) -> GrowthReportOut:
    """The value-equation analysis, computed now from the live data."""
    return GrowthReportService(db).build()


@router.get("/growth-plan", response_model=GrowthPlanOut)
def growth_plan(db: DbSession, admin: AdminUser) -> GrowthPlanOut:
    return GrowthReportService(db).plan()


@router.put("/growth-plan", response_model=GrowthPlanOut)
def set_growth_plan(payload: GrowthPlanIn, db: DbSession, admin: AdminUser) -> GrowthPlanOut:
    """The sales goal and the offer to sellers, in the owners' own words."""
    return GrowthReportService(db).set_plan(payload)


@router.get("/users", response_model=PaginatedResponse[AdminUserOut])
def list_users(
    db: DbSession,
    admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[UserRole | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
    sort: Annotated[Literal["newest", "oldest", "name", "listings"], Query()] = "newest",
) -> PaginatedResponse[AdminUserOut]:
    """Every account, searched by phone or name, filtered by role and
    status, newest first unless asked otherwise."""
    users, total = UserRepository(db).list_users(
        limit=page_size,
        offset=(page - 1) * page_size,
        query=q,
        role=role,
        active=active,
        sort=sort,
    )

    counts: dict[uuid.UUID, int] = {
        row[0]: row[1]
        for row in db.execute(
            select(Business.owner_id, func.count()).group_by(Business.owner_id)
        ).all()
    }

    page_size = max(page_size, 1)
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse[AdminUserOut](
        items=[admin_user(user, business_count=counts.get(user.id, 0)) for user in users],
        meta=PageMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )
