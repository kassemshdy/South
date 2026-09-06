"""Photo and portfolio image management for the caller's own talent profile."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import func, select

from app.api.serializers import owner_talent
from app.core.dependencies import AppSettings, DbSession, OwnTalentProfile
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.core.i18n import translate
from app.models.enums import ImageKind
from app.models.talent import TalentImage
from app.schemas.business import ImageReorderIn
from app.schemas.common import MessageResponse
from app.schemas.talent import OwnerTalentOut
from app.services.images import ImageService
from app.storage.factory import get_storage

router = APIRouter(tags=["talent-images"])

# A profile has a headshot and a portfolio, and nothing else: COVER and ITEM
# are business concepts with no talent equivalent. LOGO is reused for the
# headshot because its variant (square, 600px) is exactly the right shape.
PHOTO_KIND = ImageKind.LOGO
ALLOWED_KINDS = frozenset({PHOTO_KIND, ImageKind.GALLERY})


@router.post(
    "/my/talent/images",
    response_model=OwnerTalentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_talent_image(
    profile: OwnTalentProfile,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Image file")],
    kind: Annotated[ImageKind, Form()] = ImageKind.GALLERY,
    caption: Annotated[str | None, Form(max_length=300)] = None,
) -> OwnerTalentOut:
    """Upload the profile photo or a portfolio image.

    The file is validated by decoding it, then re-encoded and resized before it
    reaches storage, so nothing the client sends is served back verbatim.
    """
    if kind not in ALLOWED_KINDS:
        raise ValidationError("image.invalid_kind", code="invalid_image_kind")

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()

    service = ImageService(get_storage(), settings)

    if kind is ImageKind.GALLERY:
        gallery_count = int(
            db.execute(
                select(func.count())
                .select_from(TalentImage)
                .where(
                    TalentImage.profile_id == profile.id,
                    TalentImage.kind == ImageKind.GALLERY,
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
        # A profile has one photo; replacing it removes the previous file from
        # storage rather than orphaning it.
        existing = (
            db.execute(
                select(TalentImage).where(
                    TalentImage.profile_id == profile.id, TalentImage.kind == kind
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
        data=data,
        content_type=file.content_type,
        owner_id=profile.id,
        kind=kind,
        prefix="talent",
    )

    db.add(
        TalentImage(
            profile_id=profile.id,
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

    if kind is PHOTO_KIND:
        profile.photo_url, profile.photo_storage_key = stored.url, stored.key

    db.commit()
    db.refresh(profile)
    return owner_talent(profile)


@router.delete("/my/talent/images/{image_id}", response_model=OwnerTalentOut)
def delete_talent_image(
    image_id: uuid.UUID, profile: OwnTalentProfile, db: DbSession, settings: AppSettings
) -> OwnerTalentOut:
    image = db.execute(
        select(TalentImage).where(
            TalentImage.id == image_id, TalentImage.profile_id == profile.id
        )
    ).scalar_one_or_none()
    if image is None:
        raise NotFoundError("image.not_found")

    ImageService(get_storage(), settings).delete(image.storage_key)

    if image.kind is PHOTO_KIND:
        profile.photo_url, profile.photo_storage_key = None, None

    db.delete(image)
    db.commit()
    db.refresh(profile)
    return owner_talent(profile)


@router.put("/my/talent/images/order", response_model=OwnerTalentOut)
def reorder_talent_images(
    payload: ImageReorderIn, profile: OwnTalentProfile, db: DbSession
) -> OwnerTalentOut:
    gallery = {
        image.id: image for image in profile.images if image.kind is ImageKind.GALLERY
    }
    unknown = [image_id for image_id in payload.image_ids if image_id not in gallery]
    if unknown:
        raise ValidationError("image.unknown_in_order", code="unknown_image")

    for position, image_id in enumerate(payload.image_ids):
        gallery[image_id].sort_order = position
    db.commit()
    db.refresh(profile)
    return owner_talent(profile)


@router.delete("/my/talent/images", response_model=MessageResponse)
def clear_talent_gallery(
    profile: OwnTalentProfile, db: DbSession, settings: AppSettings
) -> MessageResponse:
    service = ImageService(get_storage(), settings)
    for image in list(profile.images):
        if image.kind is ImageKind.GALLERY:
            service.delete(image.storage_key)
            db.delete(image)
    db.commit()
    return MessageResponse(message=translate("image.gallery_cleared"))
