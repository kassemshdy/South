"""Every product on the site, for staff to find and correct (the owners'
request, 11 Nov 2026).

Until this, a product could be changed from the admin only by deleting it or
by opening the owner's account. The edit and the photo go through the same
service as the owner's own routes, so the search text, the clean-up of the
old photo and the size limits are one rule, not two.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.serializers import item_out, paginate
from app.core.arabic import normalize_arabic
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError
from app.core.pagination import MAX_PAGE_SIZE, Page
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category
from app.schemas.common import PaginatedResponse
from app.schemas.item import BusinessItemOut, BusinessItemUpdateIn
from app.services.business import BusinessService
from app.services.items import BusinessItemService, replace_main_image

router = APIRouter(prefix="/admin", tags=["admin-items"])


class AdminItemShop(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: BusinessStatus


class AdminItemOut(BaseModel):
    item: BusinessItemOut
    shop: AdminItemShop
    created_at: datetime


def _admin_item(item: BusinessItem) -> AdminItemOut:
    shop = item.business
    return AdminItemOut(
        item=item_out(item),
        shop=AdminItemShop(id=shop.id, name=shop.name, slug=shop.slug, status=shop.status),
        created_at=item.created_at,
    )


def _load(db: DbSession, business_id: uuid.UUID, item_id: uuid.UUID) -> BusinessItem:
    # Scoped by business, as the owner's route is: an item id from another
    # listing reaches nothing.
    item = db.get(BusinessItem, item_id)
    if item is None or item.business_id != business_id:
        raise NotFoundError("item.not_found")
    return item


@router.get("/items", response_model=PaginatedResponse[AdminItemOut])
def list_items(
    db: DbSession,
    admin: AdminUser,
    q: Annotated[str | None, Query(max_length=120)] = None,
    shop: Annotated[uuid.UUID | None, Query(description="One shop's id")] = None,
    category: Annotated[str | None, Query(description="Category slug")] = None,
    available: Annotated[bool | None, Query()] = None,
    no_photo: Annotated[bool, Query(description="Only products without a photo")] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 25,
) -> PaginatedResponse[AdminItemOut]:
    """Every product, whatever its shop's status or its own, newest first.
    Unlike the catalogue, hidden products and ones without a photo are here:
    they are what staff come to fix."""
    stmt = select(BusinessItem).join(Business, BusinessItem.business_id == Business.id)
    if shop is not None:
        stmt = stmt.where(BusinessItem.business_id == shop)
    if category:
        stmt = stmt.join(Category, Business.category_id == Category.id).where(
            Category.slug == category
        )
    if available is not None:
        stmt = stmt.where(BusinessItem.is_available.is_(available))
    if no_photo:
        stmt = stmt.where(BusinessItem.image_url.is_(None))
    if q:
        folded = normalize_arabic(q)
        stmt = stmt.where(
            or_(
                BusinessItem.search_text.like(f"%{folded}%"),
                Business.name.ilike(f"%{q}%"),
            )
        )

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    rows = (
        db.execute(
            stmt.options(selectinload(BusinessItem.images), selectinload(BusinessItem.business))
            .order_by(BusinessItem.created_at.desc(), BusinessItem.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        Page(items=list(rows), total=total, page=page, page_size=page_size), _admin_item
    )


@router.put("/businesses/{business_id}/items/{item_id}", response_model=AdminItemOut)
def update_item(
    business_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: BusinessItemUpdateIn,
    db: DbSession,
    admin: AdminUser,
) -> AdminItemOut:
    item = _load(db, business_id, item_id)
    updated = BusinessItemService(db).update(item, payload)
    BusinessService(db).refresh_search_text(item.business)
    db.commit()
    return _admin_item(updated)


@router.post("/businesses/{business_id}/items/{item_id}/image", response_model=AdminItemOut)
def replace_item_image(
    business_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> AdminItemOut:
    item = _load(db, business_id, item_id)
    return _admin_item(replace_main_image(db, settings, item.business, item, file))
