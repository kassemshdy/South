"""Moving a service profile that really sells goods into a shop.

Some sellers applied through the services door although they sell products
(support tickets, 24-26 Oct 2026). An administrator moves them: the profile
becomes a shop for the same owner, in the category the administrator picks,
keeping what a shop has room for -- its name, description, contact details,
town and pin, photo (as the logo), gallery, social pages, video and reviews
-- and its status, so a published profile is a published shop and a pending
one is still waiting. Then the service profile is removed.

What a shop has no place for is left behind: languages, education and
experience fields, and the moderation trail. A profile with service requests
is refused rather than converted, because those are customers' messages and
a shop has nowhere to keep them.

Files are moved, not copied: the image rows are re-pointed at the shop and
the profile is deleted without its files, which are now the shop's.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.models.business import Business, BusinessImage, BusinessSocialLink
from app.models.enums import ImageKind
from app.models.service_request import ServiceRequest
from app.models.talent import TalentProfile
from app.models.testimonial import Testimonial
from app.repositories.business import BusinessRepository
from app.repositories.taxonomy import CategoryRepository
from app.services.business import BusinessService
from app.services.slug import unique_slug

logger = logging.getLogger(__name__)

SHORT_DESCRIPTION = 300


class TalentConversionService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def to_business(self, profile: TalentProfile, category_id: uuid.UUID) -> Business:
        if CategoryRepository(self._db).get(category_id) is None:
            raise ValidationError("business.unknown_category", code="unknown_category")
        requests = self._db.execute(
            select(func.count())
            .select_from(ServiceRequest)
            .where(ServiceRequest.profile_id == profile.id)
        ).scalar_one()
        if requests:
            raise ValidationError(
                "talent.convert_has_requests", code="has_service_requests"
            )

        bio = (profile.bio or "").strip() or None
        business = Business(
            owner_id=profile.owner_id,
            category_id=category_id,
            location_id=profile.location_id,
            name=profile.display_name,
            slug=unique_slug(profile.display_name, BusinessRepository(self._db).slug_exists),
            short_description=bio[:SHORT_DESCRIPTION] if bio else None,
            description=bio,
            years_of_experience=profile.years_experience,
            phone=profile.phone,
            whatsapp=profile.whatsapp,
            phone_public=profile.phone_public,
            email=profile.email,
            website=profile.website,
            youtube_video_id=profile.youtube_video_id,
            logo_url=profile.photo_url,
            logo_storage_key=profile.photo_storage_key,
            latitude=profile.latitude,
            longitude=profile.longitude,
            status=profile.status,
            rejection_reason=profile.rejection_reason,
            submitted_at=profile.submitted_at,
            approved_at=profile.approved_at,
            approved_by=profile.approved_by,
            rating_average=profile.rating_average,
            rating_count=profile.rating_count,
        )
        self._db.add(business)
        self._db.flush()

        for image in profile.images:
            self._db.add(
                BusinessImage(
                    business_id=business.id,
                    url=image.url,
                    storage_key=image.storage_key,
                    kind=ImageKind.GALLERY if image.kind is ImageKind.ITEM else image.kind,
                    caption=image.caption,
                    sort_order=image.sort_order,
                    width=image.width,
                    height=image.height,
                )
            )
        for link in profile.social_links:
            self._db.add(
                BusinessSocialLink(business_id=business.id, platform=link.platform, url=link.url)
            )
        for testimonial in self._db.execute(
            select(Testimonial).where(Testimonial.talent_profile_id == profile.id)
        ).scalars():
            testimonial.talent_profile_id = None
            testimonial.business_id = business.id

        # The profile's rows go; its files do not -- they are the shop's now.
        profile.images.clear()
        profile.photo_storage_key = None
        self._db.flush()
        self._db.delete(profile)
        self._db.flush()

        self._db.refresh(business)
        business.search_text = BusinessService(self._db)._build_search_text(business)
        self._db.commit()
        logger.info(
            "Service profile moved into a shop",
            extra={"profile_id": str(profile.id), "business_id": str(business.id)},
        )
        return business
