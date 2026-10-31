"""The partner feed: Janobona's stores and products for Yalla Pay and AdsTalk.

Read-only, behind a per-partner API key (``Authorization: Bearer jnb_...``)
issued by a manager at ``/admin/api-partners``. It publishes nothing a
visitor cannot already read: approved listings, available products, and the
address of each shop's own Shopify store. ``docs/PARTNER_API.md`` is the
partners' reference; keep it in step with this file.

Paging is by cursor over ``(updated_at, id)`` so a partner syncing with
``updated_since`` never skips a row that changed while it paged.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import selectinload

from app.api.serializers import business_summary
from app.core.config import Settings
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    ValidationError,
)
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.integration import CONNECTED, ApiPartner, StoreLink
from app.schemas.integration import ApiPartnerIn, ApiPartnerIssuedOut, ApiPartnerOut
from app.schemas.partner_api import PartnerPage, PartnerProductOut, PartnerStoreOut
from app.services.api_partner import ApiPartnerService
from app.services.storefront import buy_url, online_store_url

_Row = TypeVar("_Row", Business, BusinessItem)

router = APIRouter(prefix="/partner/v1", tags=["partner-api"])
admin_router = APIRouter(prefix="/admin", tags=["admin-api-partners"])

MAX_LIMIT = 200


def _partner(request: Request, db: DbSession, settings: AppSettings) -> ApiPartner:
    header = request.headers.get("Authorization", "")
    scheme, _, key = header.partition(" ")
    partner = (
        ApiPartnerService(db).authenticate(key.strip()) if scheme.lower() == "bearer" else None
    )
    if partner is None:
        raise AuthenticationError("partner_api.bad_key", code="bad_api_key")
    status = DatabaseRateLimiter(db).hit(
        RateLimitRule(
            bucket="partner_api",
            limit=settings.partner_api_per_key_limit,
            window_seconds=settings.partner_api_per_key_window_seconds,
        ),
        str(partner.id),
    )
    db.commit()
    if not status.allowed:
        raise RateLimitedError(status.retry_after_seconds, "partner_api.rate_limited")
    return partner


Partner = Annotated[ApiPartner, Depends(_partner)]


def _require(partner: ApiPartner, scope: str) -> None:
    if scope not in partner.scope_set:
        raise PermissionDeniedError("partner_api.scope", code="scope_missing")


def _encode_cursor(updated_at: datetime, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{updated_at.isoformat()}|{row_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        stamp, row_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(stamp), uuid.UUID(row_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValidationError("partner_api.bad_cursor", code="bad_cursor") from exc


def _page(
    stmt: Select[tuple[_Row]],
    model: type[Business] | type[BusinessItem],
    cursor: str | None,
    since: datetime | None,
    limit: int,
) -> Select[tuple[_Row]]:
    if since is not None:
        stmt = stmt.where(model.updated_at >= since)
    if cursor:
        stamp, row_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(model.updated_at > stamp, and_(model.updated_at == stamp, model.id > row_id))
        )
    return stmt.order_by(model.updated_at, model.id).limit(limit + 1)


def _site(settings: Settings) -> str:
    return settings.public_base_url.rstrip("/")


def _store(business: Business, settings: Settings) -> PartnerStoreOut:
    link = business.store_link
    live = link is not None and link.is_live
    return PartnerStoreOut(
        **business_summary(business).model_dump(exclude={"logo_thumb_url", "cover_thumb_url"}),
        page_url=f"{_site(settings)}/business/{business.slug}",
        website=business.website,
        latitude=float(business.latitude) if business.latitude is not None else None,
        longitude=float(business.longitude) if business.longitude is not None else None,
        updated_at=business.updated_at,
        shop_domain=link.shop_domain if live and link else None,
        online_store_url=online_store_url(business),
        subdomain_hostname=link.subdomain_hostname if live and link else None,
    )


def _product(item: BusinessItem, settings: Settings) -> PartnerProductOut:
    return PartnerProductOut(
        id=item.id,
        slug=item.slug,
        store_slug=item.business.slug,
        title=item.title,
        description=item.description,
        price=item.price,
        currency=item.currency,
        image_url=item.image_url,
        images=[image.url for image in item.images],
        goods_origin=item.goods_origin,
        page_url=f"{_site(settings)}/product/{item.slug}",
        buy_url=buy_url(item),
        updated_at=item.updated_at,
    )


def _public_businesses() -> Select[tuple[Business]]:
    return (
        select(Business)
        .where(Business.status == BusinessStatus.APPROVED)
        .options(
            selectinload(Business.category),
            selectinload(Business.location),
            selectinload(Business.owner),
            selectinload(Business.store_link),
        )
    )


def _public_items() -> Select[tuple[BusinessItem]]:
    return (
        select(BusinessItem)
        .join(Business, Business.id == BusinessItem.business_id)
        .where(Business.status == BusinessStatus.APPROVED, BusinessItem.is_available.is_(True))
        .options(
            selectinload(BusinessItem.images),
            selectinload(BusinessItem.business).selectinload(Business.store_link),
        )
    )


@router.get("/stores", response_model=PartnerPage[PartnerStoreOut])
def list_stores(
    partner: Partner,
    db: DbSession,
    settings: AppSettings,
    connected: Annotated[bool, Query(description="Only stores with a live Shopify store")] = False,
    updated_since: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
) -> PartnerPage[PartnerStoreOut]:
    _require(partner, "stores:read")
    stmt = _public_businesses()
    if connected:
        stmt = stmt.join(StoreLink, StoreLink.business_id == Business.id).where(
            StoreLink.status == CONNECTED
        )
    rows = list(db.scalars(_page(stmt, Business, cursor, updated_since, limit)))
    more = len(rows) > limit
    rows = rows[:limit]
    return PartnerPage[PartnerStoreOut](
        items=[_store(b, settings) for b in rows],
        next_cursor=_encode_cursor(rows[-1].updated_at, rows[-1].id) if more else None,
    )


@router.get("/stores/{slug}", response_model=PartnerStoreOut)
def get_store(partner: Partner, slug: str, db: DbSession, settings: AppSettings) -> PartnerStoreOut:
    _require(partner, "stores:read")
    business = db.scalars(_public_businesses().where(Business.slug == slug)).first()
    if business is None:
        raise NotFoundError("business.not_found")
    return _store(business, settings)


@router.get("/products", response_model=PartnerPage[PartnerProductOut])
def list_products(
    partner: Partner,
    db: DbSession,
    settings: AppSettings,
    store: Annotated[str | None, Query(description="A store's slug")] = None,
    updated_since: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
) -> PartnerPage[PartnerProductOut]:
    _require(partner, "products:read")
    stmt = _public_items()
    if store:
        stmt = stmt.where(Business.slug == store)
    rows = list(db.scalars(_page(stmt, BusinessItem, cursor, updated_since, limit)))
    more = len(rows) > limit
    rows = rows[:limit]
    return PartnerPage[PartnerProductOut](
        items=[_product(i, settings) for i in rows],
        next_cursor=_encode_cursor(rows[-1].updated_at, rows[-1].id) if more else None,
    )


# --- Keys, for the manager ------------------------------------------------------


def _key_out(partner: ApiPartner) -> ApiPartnerOut:
    return ApiPartnerOut(
        id=partner.id,
        name=partner.name,
        key_prefix=partner.key_prefix,
        scopes=sorted(partner.scope_set),
        active=partner.active,
        created_at=partner.created_at,
        last_used_at=partner.last_used_at,
    )


@admin_router.get("/api-partners", response_model=list[ApiPartnerOut])
def list_api_partners(db: DbSession, admin: AdminUser) -> list[ApiPartnerOut]:
    return [_key_out(p) for p in ApiPartnerService(db).all()]


@admin_router.post("/api-partners", response_model=ApiPartnerIssuedOut, status_code=201)
def issue_api_partner(
    payload: ApiPartnerIn, db: DbSession, admin: AdminUser
) -> ApiPartnerIssuedOut:
    partner, key = ApiPartnerService(db).issue(payload.name, payload.scopes, admin.id)
    return ApiPartnerIssuedOut(**_key_out(partner).model_dump(), api_key=key)


@admin_router.post("/api-partners/{partner_id}/rotate", response_model=ApiPartnerIssuedOut)
def rotate_api_partner(
    partner_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> ApiPartnerIssuedOut:
    service = ApiPartnerService(db)
    partner = service.get(partner_id)
    key = service.rotate(partner)
    return ApiPartnerIssuedOut(**_key_out(partner).model_dump(), api_key=key)


@admin_router.post("/api-partners/{partner_id}/revoke", response_model=ApiPartnerOut)
def revoke_api_partner(partner_id: uuid.UUID, db: DbSession, admin: AdminUser) -> ApiPartnerOut:
    service = ApiPartnerService(db)
    partner = service.get(partner_id)
    service.revoke(partner)
    return _key_out(partner)
