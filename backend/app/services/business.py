"""Business lifecycle: create, update, and keep the search haystack in sync."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.arabic import build_search_text
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.i18n import LazyJoin
from app.core.urls import normalize_maps_url, normalize_social_url, normalize_url
from app.models.business import Business, BusinessSocialLink
from app.models.enums import BusinessStatus, ImageKind, ViewSubject
from app.models.user import User
from app.repositories.business import BusinessRepository
from app.repositories.taxonomy import CategoryRepository, LocationRepository
from app.schemas.business import BusinessCreateIn, BusinessUpdateIn, SocialLinkIn
from app.services.analytics import ViewCounterService
from app.services.slug import unique_slug

logger = logging.getLogger(__name__)

# Fields an owner must supply before a listing can be reviewed. Kept here rather
# than in the schema because they are required *at submission*, not at save:
# the wizard deliberately allows saving an incomplete draft.
SUBMISSION_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("name", "business.field.name"),
    ("short_description", "business.field.short_description"),
    ("category_id", "business.field.category"),
    ("location_id", "business.field.location"),
)


class BusinessService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = BusinessRepository(db)
        self._categories = CategoryRepository(db)
        self._locations = LocationRepository(db)

    # --- Creation and updates ---------------------------------------------

    def create(self, owner: User, payload: BusinessCreateIn) -> Business:
        self._validate_taxonomy(payload.category_id, payload.location_id)

        business = Business(
            owner_id=owner.id,
            name=payload.name,
            slug=unique_slug(payload.name, self._repo.slug_exists),
            short_description=payload.short_description,
            description=payload.description,
            institution_name=payload.institution_name,
            founding_date=payload.founding_date,
            production_nature=payload.production_nature,
            years_of_experience=payload.years_of_experience,
            owner_relation=payload.owner_relation,
            category_id=payload.category_id,
            custom_category_text=payload.custom_category_text,
            location_id=payload.location_id,
            phone=payload.phone,
            whatsapp=payload.whatsapp,
            email=payload.email,
            website=normalize_url(payload.website) if payload.website else None,
            address_text=payload.address_text,
            latitude=payload.latitude,
            longitude=payload.longitude,
            maps_url=normalize_maps_url(payload.maps_url) if payload.maps_url else None,
            status=BusinessStatus.DRAFT,
        )
        # Add (and flush) before deriving the haystack: on a transient object
        # not yet attached to the session, relationship access (business.category,
        # business.location) silently returns None regardless of the FK columns
        # above, which would index every new business with a blank category and
        # location.
        self._repo.add(business)
        business.search_text = self._build_search_text(business)

        if payload.social_links:
            self._replace_social_links(business, payload.social_links)

        self._db.commit()
        logger.info(
            "Business created",
            extra={"business_id": str(business.id), "owner_id": str(owner.id)},
        )
        return self._reload(business.id)

    def update(self, business: Business, payload: BusinessUpdateIn) -> Business:
        data = payload.model_dump(exclude_unset=True)
        social_links = data.pop("social_links", None)

        if "category_id" in data or "location_id" in data:
            self._validate_taxonomy(
                data.get("category_id", business.category_id),
                data.get("location_id", business.location_id),
            )

        if "website" in data:
            data["website"] = normalize_url(data["website"]) if data["website"] else None
        if "maps_url" in data:
            data["maps_url"] = normalize_maps_url(data["maps_url"]) if data["maps_url"] else None

        for field, value in data.items():
            setattr(business, field, value)

        # The slug is part of the public URL; renaming a listing must not break
        # links that are already shared, so it is only derived once at creation.
        business.search_text = self._build_search_text(business)

        if social_links is not None:
            self._replace_social_links(
                business, [SocialLinkIn.model_validate(link) for link in social_links]
            )

        self._db.commit()
        logger.info("Business updated", extra={"business_id": str(business.id)})
        return self._reload(business.id)

    def delete(self, business: Business) -> None:
        # Images cascade at the database level; storage objects are cleaned up
        # by the caller, which holds the storage backend.
        business_id = business.id
        # View counters do not cascade -- their subject_id carries no foreign
        # key, because it points at one of three tables. See ViewSubject.
        ViewCounterService(self._db).forget(ViewSubject.BUSINESS, business_id)
        for item in list(business.items):
            ViewCounterService(self._db).forget(ViewSubject.PRODUCT, item.id)
        self._repo.delete(business)
        self._db.commit()
        logger.info("Business deleted", extra={"business_id": str(business_id)})

    def refresh_search_text(self, business: Business) -> None:
        """Re-derive the haystack after items change."""
        business.search_text = self._build_search_text(business)
        self._db.flush()

    # --- Submission readiness ---------------------------------------------

    def missing_requirements(self, business: Business) -> list[str]:
        """Translation keys for the fields still needed before review.

        Keys rather than text: the caller renders them in the reader's locale.
        """
        missing = [
            key
            for field, key in SUBMISSION_REQUIREMENTS
            if not getattr(business, field, None)
        ]
        has_logo = business.logo_url or any(
            image.kind is ImageKind.LOGO for image in business.images
        )
        if not has_logo:
            missing.append("business.field.logo")
        if not (business.phone or business.whatsapp):
            missing.append("business.field.contact")
        if (
            business.category is not None
            and business.category.slug == "other"
            and not (business.custom_category_text or "").strip()
        ):
            missing.append("business.field.custom_category")
        return missing

    def assert_ready_for_review(self, business: Business) -> None:
        missing = self.missing_requirements(business)
        if missing:
            raise ValidationError(
                "business.incomplete",
                code="incomplete_business",
                details={"missing": missing},
                params={"missing": LazyJoin(tuple(missing))},
            )

    # --- internals ---------------------------------------------------------

    def _reload(self, business_id: uuid.UUID) -> Business:
        business = self._repo.get_with_relations(business_id)
        if business is None:  # pragma: no cover - only on concurrent deletion
            raise NotFoundError("business.not_found")
        return business

    def _validate_taxonomy(
        self, category_id: uuid.UUID | None, location_id: uuid.UUID | None
    ) -> None:
        if category_id is not None and self._categories.get(category_id) is None:
            raise ValidationError("business.unknown_category", code="unknown_category")
        if location_id is not None and self._locations.get(location_id) is None:
            raise ValidationError("business.unknown_location", code="unknown_location")

    def _replace_social_links(self, business: Business, links: list[SocialLinkIn]) -> None:
        seen: set[str] = set()
        normalized: list[BusinessSocialLink] = []

        for link in links:
            if not link.url or not link.url.strip():
                continue
            if link.platform.value in seen:
                raise ConflictError(
                    "business.duplicate_social_platform",
                    code="duplicate_social_platform",
                )
            seen.add(link.platform.value)
            normalized.append(
                BusinessSocialLink(
                    business_id=business.id,
                    platform=link.platform,
                    url=normalize_social_url(link.platform, link.url),
                )
            )

        business.social_links.clear()
        self._db.flush()
        for link_model in normalized:
            business.social_links.append(link_model)
        self._db.flush()

    def _build_search_text(self, business: Business) -> str:
        item_titles = " ".join(item.title for item in business.items) if business.items else ""
        if business.category is None:
            category = ""
        elif business.category.slug == "other" and business.custom_category_text:
            # Otherwise every "Other" business would index the same literal
            # category name and none of them would be findable by what they
            # actually are.
            category = business.custom_category_text
        else:
            category = business.category.name_ar
        location = business.location.name_ar if business.location else ""
        return build_search_text(
            business.name,
            business.short_description,
            business.description,
            # A buyer searches for what a place makes and, sometimes, for the
            # registered name on its paperwork. The founding date is not text
            # anyone searches by, so it stays out.
            business.institution_name,
            business.production_nature,
            business.address_text,
            category,
            location,
            item_titles,
        )
