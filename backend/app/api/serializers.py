"""Model → schema conversion.

Kept in one module so the rule "public payloads never contain moderation fields
or the owner's login phone" is visible in a single place.
"""

from __future__ import annotations

from app.core.pagination import Page
from app.models.business import Business, BusinessItem
from app.models.enums import ImageKind
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.schemas.business import (
    BusinessDetailOut,
    BusinessImageOut,
    BusinessSummaryOut,
    OwnerBusinessOut,
    SocialLinkOut,
)
from app.schemas.common import PageMeta, PaginatedResponse
from app.schemas.item import BusinessItemOut
from app.schemas.moderation import AdminBusinessOut, AdminUserOut, ModerationActionOut
from app.schemas.taxonomy import CategoryOut, LocationOut


def category_out(category: Category | None, *, business_count: int = 0) -> CategoryOut | None:
    if category is None:
        return None
    data = CategoryOut.model_validate(category)
    return data.model_copy(update={"business_count": business_count})


def location_out(location: Location | None, *, business_count: int = 0) -> LocationOut | None:
    if location is None:
        return None
    data = LocationOut.model_validate(location)
    return data.model_copy(update={"business_count": business_count})


def item_out(item: BusinessItem) -> BusinessItemOut:
    return BusinessItemOut.model_validate(item)


def _gallery(business: Business) -> list[BusinessImageOut]:
    return [
        BusinessImageOut.model_validate(image)
        for image in sorted(business.images, key=lambda i: i.sort_order)
        if image.kind is ImageKind.GALLERY
    ]


def business_summary(business: Business) -> BusinessSummaryOut:
    return BusinessSummaryOut(
        id=business.id,
        name=business.name,
        slug=business.slug,
        short_description=business.short_description,
        logo_url=business.logo_url,
        cover_url=business.cover_url,
        phone=business.phone,
        whatsapp=business.whatsapp,
        category=category_out(business.category),
        custom_category_text=business.custom_category_text,
        location=location_out(business.location),
        created_at=business.created_at,
    )


def business_detail(business: Business) -> BusinessDetailOut:
    """Public profile. Contains only what the owner chose to publish."""
    return BusinessDetailOut(
        **business_summary(business).model_dump(),
        description=business.description,
        email=business.email,
        website=business.website,
        address_text=business.address_text,
        latitude=float(business.latitude) if business.latitude is not None else None,
        longitude=float(business.longitude) if business.longitude is not None else None,
        maps_url=business.maps_url,
        images=_gallery(business),
        social_links=[SocialLinkOut.model_validate(link) for link in business.social_links],
        items=[item_out(item) for item in sorted(business.items, key=lambda i: i.sort_order)],
        approved_at=business.approved_at,
    )


def owner_business(business: Business) -> OwnerBusinessOut:
    """Owner's own view — adds moderation state and the rejection reason."""
    return OwnerBusinessOut(
        **business_detail(business).model_dump(),
        status=business.status,
        rejection_reason=business.rejection_reason,
        submitted_at=business.submitted_at,
        updated_at=business.updated_at,
    )


def admin_business(business: Business) -> AdminBusinessOut:
    """Review payload — administrators may see the owner's account details."""
    return AdminBusinessOut(
        **owner_business(business).model_dump(),
        owner_id=business.owner_id,
        owner_phone=business.owner.phone_number if business.owner else None,
        owner_personal_phone=business.owner.personal_phone_number if business.owner else None,
        owner_has_verification_document=bool(
            business.owner and business.owner.verification_document is not None
        ),
        owner_display_name=business.owner.display_name if business.owner else None,
        moderation_actions=[
            ModerationActionOut.model_validate(action)
            for action in sorted(business.moderation_actions, key=lambda a: a.created_at)
        ],
    )


def admin_user(user: User, *, business_count: int = 0) -> AdminUserOut:
    data = AdminUserOut.model_validate(user)
    return data.model_copy(update={"business_count": business_count})


def paginate(page: Page[Business], mapper) -> PaginatedResponse:  # type: ignore[type-arg]
    return PaginatedResponse(
        items=[mapper(item) for item in page.items],
        meta=PageMeta(
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            total_pages=page.total_pages,
            has_next=page.has_next,
            has_previous=page.has_previous,
        ),
    )
