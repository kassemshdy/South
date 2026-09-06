"""Products / services / menu items for a business the caller owns, plus the
independent public `/items` directory."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Path, Query, UploadFile, status

from app.api.serializers import item_out, paginate, product_detail, product_summary
from app.core.dependencies import AppSettings, DbSession, OwnedBusiness
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.core.i18n import translate
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models.enums import ImageKind
from app.repositories.item import ItemRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.item import (
    BusinessItemIn,
    BusinessItemOut,
    BusinessItemUpdateIn,
    ItemReorderIn,
)
from app.schemas.product import ProductDetailOut, ProductSummaryOut
from app.services.business import BusinessService
from app.services.images import ImageService
from app.services.items import BusinessItemService
from app.storage.factory import get_storage

router = APIRouter(tags=["business-items"])
public_router = APIRouter(tags=["products"])


# --- Public ------------------------------------------------------------------


@public_router.get("/items", response_model=PaginatedResponse[ProductSummaryOut])
def search_products(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120, description="Free-text search query")] = None,
    category: Annotated[str | None, Query(description="Category slug")] = None,
    location: Annotated[str | None, Query(description="Location slug")] = None,
    sort: Annotated[Literal["newest", "name", "oldest"], Query()] = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[ProductSummaryOut]:
    """Search available products/services of approved businesses.

    Never returns an item whose business isn't approved, or an unavailable one.
    """
    results = ItemRepository(db).search_public(
        q=q,
        category_slug=category,
        location_slug=location,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return paginate(results, product_summary)


@public_router.get("/items/{slug}", response_model=ProductDetailOut)
def get_product(slug: Annotated[str, Path(max_length=200)], db: DbSession) -> ProductDetailOut:
    item = ItemRepository(db).get_by_slug(slug)
    if item is None:
        raise NotFoundError("item.not_found")
    return product_detail(item)


@router.get("/businesses/{business_id}/items", response_model=list[BusinessItemOut])
def list_items(business: OwnedBusiness, db: DbSession) -> list[BusinessItemOut]:
    return [item_out(item) for item in BusinessItemService(db).list_for_business(business.id)]


@router.post(
    "/businesses/{business_id}/items",
    response_model=BusinessItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    payload: BusinessItemIn, business: OwnedBusiness, db: DbSession
) -> BusinessItemOut:
    item = BusinessItemService(db).create(business, payload)
    # Item titles are part of the searchable haystack (searching for a product
    # should find the shop that sells it), so the text is refreshed here.
    BusinessService(db).refresh_search_text(business)
    db.commit()
    return item_out(item)


@router.put("/businesses/{business_id}/items/{item_id}", response_model=BusinessItemOut)
def update_item(
    item_id: uuid.UUID,
    payload: BusinessItemUpdateIn,
    business: OwnedBusiness,
    db: DbSession,
) -> BusinessItemOut:
    service = BusinessItemService(db)
    item = service.get_owned(business, item_id)
    updated = service.update(item, payload)
    BusinessService(db).refresh_search_text(business)
    db.commit()
    return item_out(updated)


@router.delete("/businesses/{business_id}/items/{item_id}", response_model=MessageResponse)
def delete_item(
    item_id: uuid.UUID, business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> MessageResponse:
    service = BusinessItemService(db)
    item = service.get_owned(business, item_id)
    storage_key = service.delete(item)
    ImageService(get_storage(), settings).delete(storage_key)
    BusinessService(db).refresh_search_text(business)
    db.commit()
    return MessageResponse(message=translate("item.deleted"))


@router.put("/businesses/{business_id}/items/order", response_model=list[BusinessItemOut])
def reorder_items(
    payload: ItemReorderIn, business: OwnedBusiness, db: DbSession
) -> list[BusinessItemOut]:
    items = BusinessItemService(db).reorder(business, payload.item_ids)
    return [item_out(item) for item in items]


@router.post("/businesses/{business_id}/items/{item_id}/image", response_model=BusinessItemOut)
def upload_item_image(
    item_id: uuid.UUID,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> BusinessItemOut:
    service = BusinessItemService(db)
    item = service.get_owned(business, item_id)

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()

    images = ImageService(get_storage(), settings)
    stored = images.process_and_store(
        data=data,
        content_type=file.content_type,
        owner_id=business.id,
        kind=ImageKind.ITEM,
    )

    images.delete(item.image_storage_key)
    item.image_url, item.image_storage_key = stored.url, stored.key
    db.commit()
    return item_out(item)
