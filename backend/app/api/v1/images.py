"""Image upload and management for a business the caller owns."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import func, select

from app.api.serializers import owner_business
from app.core.dependencies import AppSettings, DbSession, OwnedBusiness
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.core.i18n import translate
from app.models.business import BusinessImage
from app.models.enums import ImageKind
from app.schemas.business import ImageReorderIn, OwnerBusinessOut
from app.schemas.common import MessageResponse
from app.services.images import ImageService
from app.storage.factory import get_storage

router = APIRouter(tags=["business-images"])


@router.post(
    "/businesses/{business_id}/images",
    response_model=OwnerBusinessOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_image(
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Image file")],
    kind: Annotated[ImageKind, Form()] = ImageKind.GALLERY,
    caption: Annotated[str | None, Form(max_length=300)] = None,
) -> OwnerBusinessOut:
    """Upload a logo, cover or gallery image.

    The file is validated by decoding it, then re-encoded and resized before it
    reaches storage, so nothing the client sends is served back verbatim.
    """
    if kind is ImageKind.ITEM:
        raise ValidationError(
            "image.invalid_kind", code="invalid_image_kind"
        )

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()

    service = ImageService(get_storage(), settings)

    if kind is ImageKind.GALLERY:
        gallery_count = int(
            db.execute(
                select(func.count())
                .select_from(BusinessImage)
                .where(
                    BusinessImage.business_id == business.id,
                    BusinessImage.kind == ImageKind.GALLERY,
                )
            ).scalar_one()
        )
        if gallery_count >= settings.max_gallery_images:
            raise ValidationError(
                "image.gallery_limit",
                code="gallery_limit_reached",
                params={"max": settings.max_gallery_images},
            )
    else:
        # A business has one logo and one cover; replacing either removes the
        # previous file from storage rather than orphaning it.
        existing = (
            db.execute(
                select(BusinessImage).where(
                    BusinessImage.business_id == business.id, BusinessImage.kind == kind
                )
            )
            .scalars()
            .all()
        )
        for image in existing:
            service.delete(image.storage_key)
            db.delete(image)
        db.flush()
        gallery_count = 0

    stored = service.process_and_store(
        data=data, content_type=file.content_type, owner_id=business.id, kind=kind
    )

    db.add(
        BusinessImage(
            business_id=business.id,
            url=stored.url,
            storage_key=stored.key,
            kind=kind,
            caption=caption,
            sort_order=gallery_count,
            width=stored.width,
            height=stored.height,
            size_bytes=stored.size_bytes,
        )
    )

    if kind is ImageKind.LOGO:
        business.logo_url, business.logo_storage_key = stored.url, stored.key
    elif kind is ImageKind.COVER:
        business.cover_url, business.cover_storage_key = stored.url, stored.key

    db.commit()
    db.refresh(business)
    return owner_business(business)


@router.delete("/businesses/{business_id}/images/{image_id}", response_model=OwnerBusinessOut)
def delete_image(
    image_id: uuid.UUID, business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> OwnerBusinessOut:
    image = db.execute(
        select(BusinessImage).where(
            BusinessImage.id == image_id, BusinessImage.business_id == business.id
        )
    ).scalar_one_or_none()
    if image is None:
        raise NotFoundError("image.not_found")

    ImageService(get_storage(), settings).delete(image.storage_key)

    if image.kind is ImageKind.LOGO:
        business.logo_url, business.logo_storage_key = None, None
    elif image.kind is ImageKind.COVER:
        business.cover_url, business.cover_storage_key = None, None

    db.delete(image)
    db.commit()
    db.refresh(business)
    return owner_business(business)


@router.put("/businesses/{business_id}/images/order", response_model=OwnerBusinessOut)
def reorder_images(
    payload: ImageReorderIn, business: OwnedBusiness, db: DbSession
) -> OwnerBusinessOut:
    gallery = {
        image.id: image for image in business.images if image.kind is ImageKind.GALLERY
    }
    unknown = [image_id for image_id in payload.image_ids if image_id not in gallery]
    if unknown:
        raise ValidationError("image.unknown_in_order", code="unknown_image")

    for position, image_id in enumerate(payload.image_ids):
        gallery[image_id].sort_order = position
    db.commit()
    db.refresh(business)
    return owner_business(business)


@router.delete("/businesses/{business_id}/images", response_model=MessageResponse)
def clear_gallery(business: OwnedBusiness, db: DbSession, settings: AppSettings) -> MessageResponse:
    service = ImageService(get_storage(), settings)
    for image in list(business.images):
        if image.kind is ImageKind.GALLERY:
            service.delete(image.storage_key)
            db.delete(image)
    db.commit()
    return MessageResponse(message=translate("image.gallery_cleared"))
