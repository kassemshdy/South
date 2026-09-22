"""Products / services / menu items for a business the caller owns, plus the
independent public `/items` directory."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Path, Query, UploadFile, status
from sqlalchemy import func, select

from app.api.serializers import item_out, paginate, product_detail, product_summary
from app.core.dependencies import AppSettings, DbSession, OwnedBusiness, Viewer
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.core.i18n import translate
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models.business import BusinessItemImage
from app.models.enums import GoodsOrigin, ImageKind, ViewSubject
from app.repositories.item import ItemRepository
from app.schemas.business import ImageReorderIn
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.item import (
    BusinessItemIn,
    BusinessItemOut,
    BusinessItemUpdateIn,
    ItemReorderIn,
)
from app.schemas.product import ProductDetailOut, ProductSummaryOut
from app.services.analytics import ViewCounterService
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
    origin: Annotated[
        GoodsOrigin | None, Query(description="Made in the South, or imported")
    ] = None,
    sort: Annotated[
        Literal["newest", "name", "oldest", "price_asc", "price_desc"], Query()
    ] = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[ProductSummaryOut]:
    """Search available products/services of approved businesses.

    Never returns an item whose business isn't approved, or an unavailable one.

    **Ordering, not filtering, is how price is offered here.** A range needs a
    currency to mean anything, and it also has to decide what to do with the
    products whose owner named no price -- two questions asked before the
    visitor has seen a single result. ``price_asc``/``price_desc`` ask
    neither: nothing is removed, and a product with no stated price sorts to
    the end rather than being judged cheap or expensive.

    See ``ItemRepository._apply_sort`` for the one caveat -- ordering compares
    the stored number, so it is exact only while the listings share a
    currency, which today they do.
    """
    results = ItemRepository(db).search_public(
        q=q,
        category_slug=category,
        location_slug=location,
        origin=origin,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return paginate(results, product_summary)


@public_router.get("/items/{slug}", response_model=ProductDetailOut)
def get_product(
    slug: Annotated[str, Path(max_length=200)], db: DbSession, viewer: Viewer
) -> ProductDetailOut:
    item = ItemRepository(db).get_by_slug(slug)
    if item is None:
        raise NotFoundError("item.not_found")
    payload = product_detail(item)
    # Nothing surfaces product views yet. They are counted anyway because a
    # view cannot be backfilled: the history has to start before the screen
    # that reads it exists.
    ViewCounterService(db).record(
        ViewSubject.PRODUCT,
        item.id,
        owner_id=item.business.owner_id,
        viewer=viewer,
    )
    return payload


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
    storage_keys = service.delete(item)
    images = ImageService(get_storage(), settings)
    for storage_key in storage_keys:
        images.delete(storage_key)
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


@router.post(
    "/businesses/{business_id}/items/{item_id}/gallery",
    response_model=BusinessItemOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_item_gallery_image(
    item_id: uuid.UUID,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form(max_length=300)] = None,
) -> BusinessItemOut:
    """Add a photo to a product's gallery, separate from its card thumbnail.

    ``image_url`` (set by ``upload_item_image`` above) is what a listing card
    shows; this gallery is what a buyer sees after opening the product, the
    same distinction a business draws between its logo/cover and its gallery.
    """
    service = BusinessItemService(db)
    item = service.get_owned(business, item_id)

    gallery_count = int(
        db.execute(
            select(func.count())
            .select_from(BusinessItemImage)
            .where(BusinessItemImage.item_id == item.id)
        ).scalar_one()
    )
    if gallery_count >= settings.max_gallery_images:
        raise ValidationError(
            "image.gallery_limit",
            code="gallery_limit_reached",
            params={"max": settings.max_gallery_images},
        )

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()

    images = ImageService(get_storage(), settings)
    stored = images.process_and_store(
        data=data,
        content_type=file.content_type,
        owner_id=item.id,
        kind=ImageKind.GALLERY,
        prefix="items",
    )

    db.add(
        BusinessItemImage(
            item_id=item.id,
            url=stored.url,
            storage_key=stored.key,
            caption=caption,
            sort_order=gallery_count,
            width=stored.width,
            height=stored.height,
            size_bytes=stored.size_bytes,
        )
    )
    db.commit()
    db.refresh(item)
    return item_out(item)


@router.delete(
    "/businesses/{business_id}/items/{item_id}/gallery/{image_id}",
    response_model=BusinessItemOut,
)
def delete_item_gallery_image(
    item_id: uuid.UUID,
    image_id: uuid.UUID,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
) -> BusinessItemOut:
    service = BusinessItemService(db)
    item = service.get_owned(business, item_id)

    image = db.execute(
        select(BusinessItemImage).where(
            BusinessItemImage.id == image_id, BusinessItemImage.item_id == item.id
        )
    ).scalar_one_or_none()
    if image is None:
        raise NotFoundError("image.not_found")

    ImageService(get_storage(), settings).delete(image.storage_key)
    db.delete(image)
    db.commit()
    db.refresh(item)
    return item_out(item)


@router.put(
    "/businesses/{business_id}/items/{item_id}/gallery/order",
    response_model=BusinessItemOut,
)
def reorder_item_gallery(
    item_id: uuid.UUID,
    payload: ImageReorderIn,
    business: OwnedBusiness,
    db: DbSession,
) -> BusinessItemOut:
    service = BusinessItemService(db)
    item = service.get_owned(business, item_id)

    gallery = {image.id: image for image in item.images}
    unknown = [image_id for image_id in payload.image_ids if image_id not in gallery]
    if unknown:
        raise ValidationError("image.unknown_in_order", code="unknown_image")

    for position, image_id in enumerate(payload.image_ids):
        gallery[image_id].sort_order = position
    db.commit()
    db.refresh(item)
    return item_out(item)
