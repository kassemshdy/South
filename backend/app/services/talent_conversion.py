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
from app.models.enums import ImageKind, TalentKind
from app.models.service_request import ServiceRequest
from app.models.story import StoryImage
from app.models.talent import (
    TalentImage,
    TalentProfile,
    TalentServiceOffer,
    TalentSocialLink,
)
from app.models.testimonial import Testimonial
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository, TalentSkillRepository
from app.repositories.taxonomy import CategoryRepository
from app.services.business import BusinessService
from app.services.slug import unique_slug
from app.services.talent import TalentService

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


#: The longest offer title and description a TalentServiceOffer takes.
OFFER_TITLE = 120
OFFER_DESCRIPTION = 500


class BusinessConversionService:
    """The other direction: a shop that really offers a service, moved into
    a services profile by an administrator (the owners' review, 12 Nov 2026).

    It keeps what a services profile has room for: the name, description,
    contacts, town and pin, logo (as the photo), gallery, social pages,
    video, reviews, stories and status. Each product becomes a priced
    service with its photo. Files are moved, not copied.

    Refused rather than half-done when the owner already has a services
    profile (an account holds one), or when the shop has orders, a
    connected online store or official papers: a profile has nowhere to
    keep any of those.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def to_talent(self, business: Business, skill_id: uuid.UUID) -> TalentProfile:
        if TalentSkillRepository(self._db).get(skill_id) is None:
            raise ValidationError("talent.unknown_skill", code="unknown_skill")
        owner_has_profile = self._db.execute(
            select(TalentProfile.id).where(TalentProfile.owner_id == business.owner_id)
        ).first()
        if owner_has_profile is not None:
            raise ValidationError(
                "business.convert_owner_has_profile", code="owner_has_profile"
            )
        if business.orders:
            raise ValidationError("business.convert_has_orders", code="has_orders")
        if business.store_link is not None:
            raise ValidationError("business.convert_has_store", code="has_store")
        if business.documents:
            raise ValidationError("business.convert_has_documents", code="has_documents")

        bio = (business.description or business.short_description or "").strip() or None
        profile = TalentProfile(
            owner_id=business.owner_id,
            kind=TalentKind.SERVICE,
            skill_id=skill_id,
            location_id=business.location_id,
            latitude=business.latitude,
            longitude=business.longitude,
            display_name=business.name,
            slug=unique_slug(business.name, TalentRepository(self._db).slug_exists),
            bio=bio,
            years_experience=business.years_of_experience,
            phone=business.phone,
            whatsapp=business.whatsapp,
            phone_public=business.phone_public,
            email=business.email,
            website=business.website,
            youtube_video_id=business.youtube_video_id,
            photo_url=business.logo_url,
            photo_storage_key=business.logo_storage_key,
            status=business.status,
            rejection_reason=business.rejection_reason,
            submitted_at=business.submitted_at,
            approved_at=business.approved_at,
            approved_by=business.approved_by,
            rating_average=business.rating_average,
            rating_count=business.rating_count,
        )
        self._db.add(profile)
        self._db.flush()

        for image in business.images:
            self._db.add(
                TalentImage(
                    profile_id=profile.id,
                    url=image.url,
                    storage_key=image.storage_key,
                    # The wide cover is gone (10 Nov 2026); it joins the gallery.
                    kind=ImageKind.GALLERY if image.kind is ImageKind.COVER else image.kind,
                    caption=image.caption,
                    sort_order=image.sort_order,
                    width=image.width,
                    height=image.height,
                )
            )
        for index, item in enumerate(sorted(business.items, key=lambda row: row.sort_order)):
            description = (item.description or "").strip() or None
            self._db.add(
                TalentServiceOffer(
                    profile_id=profile.id,
                    title=item.title[:OFFER_TITLE],
                    description=description[:OFFER_DESCRIPTION] if description else None,
                    price_from=item.price,
                    currency=item.currency,
                    sort_order=index,
                    image_url=item.image_url,
                    image_storage_key=item.image_storage_key,
                )
            )
            # A product's extra photos have no place on a service; they
            # join the profile's gallery rather than being lost.
            for extra in item.images:
                self._db.add(
                    TalentImage(
                        profile_id=profile.id,
                        url=extra.url,
                        storage_key=extra.storage_key,
                        kind=ImageKind.GALLERY,
                        caption=extra.caption,
                        sort_order=1000 + index,
                    )
                )
        for link in business.social_links:
            self._db.add(
                TalentSocialLink(profile_id=profile.id, platform=link.platform, url=link.url)
            )
        for testimonial in self._db.execute(
            select(Testimonial).where(Testimonial.business_id == business.id)
        ).scalars():
            testimonial.business_id = None
            testimonial.talent_profile_id = profile.id
        for story in self._db.execute(
            select(StoryImage).where(StoryImage.business_id == business.id)
        ).scalars():
            story.business_id = None
            story.talent_profile_id = profile.id

        # The shop's rows go; its files do not -- they are the profile's now.
        self._db.flush()
        self._db.delete(business)
        self._db.flush()

        self._db.refresh(profile)
        profile.search_text = TalentService(self._db)._build_search_text(profile)
        self._db.commit()
        logger.info(
            "Shop moved into a service profile",
            extra={"business_id": str(business.id), "profile_id": str(profile.id)},
        )
        return profile
