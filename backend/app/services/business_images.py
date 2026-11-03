"""Storing a business's logo, cover and gallery images.

Shared by the owner's upload route, the administrators' (who can add a logo
or cover a listing went live without) and the public application form, which
arrives with the applicant's logo.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ValidationError
from app.models.business import Business, BusinessImage
from app.models.enums import ImageKind
from app.services.images import ImageService
from app.storage.factory import get_storage


def store_business_image(
    db: Session,
    settings: Settings,
    business: Business,
    *,
    kind: ImageKind,
    data: bytes,
    content_type: str | None,
    caption: str | None = None,
) -> None:
    """Store one logo, cover or gallery image and point the listing at it.

    Shared by the owner's route and the administrators' (who can add a logo
    or cover a listing went live without). Does not commit.
    """
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
        data=data, content_type=content_type, owner_id=business.id, kind=kind
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
