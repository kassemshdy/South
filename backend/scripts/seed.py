"""Development seed script.

Idempotent: safe to re-run. Creates categories, the South Lebanon location tree,
sample businesses across every moderation status, and the administrator account
from environment configuration (never a hardcoded production credential).

Usage:
    python -m scripts.seed               # add missing records
    python -m scripts.seed --reset       # wipe seeded content first
    python -m scripts.seed --admin-only  # create/update only the administrator

Sample businesses are development fixtures and are never created against a
production database. ``--admin-only`` is the exception: bootstrapping the first
administrator is a legitimate production operation, so it is allowed there.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from PIL import Image, ImageDraw
from sqlalchemy import delete, select

from app.core.arabic import build_search_text
from app.core.config import get_settings
from app.core.i18n import translate
from app.core.logging import configure_logging
from app.core.phone import normalize_phone
from app.core.security import hash_password
from app.database.session import session_scope
from app.models.auth import OtpRequest, RateLimitEvent
from app.models.business import (
    Business,
    BusinessImage,
    BusinessItem,
    BusinessSocialLink,
    ModerationAction,
)
from app.models.enums import (
    BusinessStatus,
    Currency,
    ImageKind,
    LocationType,
    ModerationActionType,
    SocialPlatform,
    UserRole,
)
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services.images import ImageService
from app.storage.factory import get_storage
from scripts.seed_data import BUSINESSES, CATEGORIES, LOCATIONS, LocationSeed

logger = logging.getLogger("seed")

# Distinct, readable placeholder colours so seeded listings are visually
# distinguishable in the UI without shipping binary fixtures in the repo.
_PALETTE = [
    (198, 93, 59), (61, 122, 106), (140, 95, 168), (191, 143, 60),
    (75, 110, 175), (168, 74, 96), (94, 134, 66), (120, 110, 100),
]


def _placeholder_image(text: str, index: int, size: tuple[int, int]) -> bytes:
    """Generate a simple coloured placeholder so cards are not empty."""
    colour = _PALETTE[index % len(_PALETTE)]
    image = Image.new("RGB", size, colour)
    draw = ImageDraw.Draw(image)
    # Arabic glyphs need a shaping engine to render correctly; a neutral band is
    # honest placeholder art rather than mojibake.
    band_height = max(size[1] // 6, 12)
    draw.rectangle(
        [(0, size[1] - band_height), (size[0], size[1])],
        fill=tuple(min(255, channel + 45) for channel in colour),
    )
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


def seed_categories(db) -> dict[str, Category]:  # type: ignore[no-untyped-def]
    existing = {c.slug: c for c in db.execute(select(Category)).scalars().all()}
    for entry in CATEGORIES:
        slug = str(entry["slug"])
        if slug in existing:
            continue
        category = Category(
            name_ar=entry["name_ar"],
            slug=slug,
            icon=entry.get("icon"),
            sort_order=entry["sort_order"],
            is_active=True,
        )
        db.add(category)
        existing[slug] = category
    db.flush()
    logger.info("Categories ready", extra={"count": len(existing)})
    return existing


def seed_locations(db) -> dict[str, Location]:  # type: ignore[no-untyped-def]
    existing = {loc.slug: loc for loc in db.execute(select(Location)).scalars().all()}

    def create(
        entry: LocationSeed, location_type: LocationType, parent: Location | None, order: int
    ) -> Location:
        slug = entry["slug"]
        location = existing.get(slug)
        if location is None:
            location = Location(
                name_ar=entry["name_ar"],
                slug=slug,
                type=location_type,
                parent_id=parent.id if parent else None,
                sort_order=order,
                is_active=True,
            )
            db.add(location)
            db.flush()
            existing[slug] = location
        return location

    for gov_order, governorate in enumerate(LOCATIONS):
        gov = create(governorate, LocationType.GOVERNORATE, None, gov_order)
        for dist_order, district in enumerate(governorate.get("children", [])):
            dist = create(district, LocationType.DISTRICT, gov, dist_order)
            for town_order, town in enumerate(district.get("children", [])):
                create(town, LocationType.TOWN, dist, town_order)

    db.flush()
    logger.info("Locations ready", extra={"count": len(existing)})
    return existing


def seed_admin(db) -> User | None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD not configured; skipping admin seed")
        return None

    email = settings.admin_email.strip().lower()
    admin = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if admin is None:
        admin = User(
            email=email,
            password_hash=hash_password(settings.admin_password),
            display_name=settings.admin_display_name
            or translate("admin.default_display_name"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()
        logger.info("Administrator created", extra={"email": email})
    else:
        # Keep the seeded admin usable if the configured password changed.
        admin.password_hash = hash_password(settings.admin_password)
        admin.role = UserRole.ADMIN
        admin.is_active = True
        logger.info("Administrator updated", extra={"email": email})
    return admin


def seed_businesses(db, categories, locations, admin) -> int:  # type: ignore[no-untyped-def]
    settings = get_settings()
    images = ImageService(get_storage(), settings)
    created = 0

    for index, entry in enumerate(BUSINESSES):
        name = entry["name"]
        if db.execute(select(Business).where(Business.name == name)).scalar_one_or_none():
            continue

        phone = normalize_phone(entry["owner_phone"])
        owner = db.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()
        if owner is None:
            owner = User(phone_number=phone, role=UserRole.OWNER)
            db.add(owner)
            db.flush()

        category = categories[entry["category"]]
        location = locations[entry["location"]]
        status = BusinessStatus(entry["status"])
        created_at = datetime.now(UTC) - timedelta(days=len(BUSINESSES) - index)

        business = Business(
            owner_id=owner.id,
            category_id=category.id,
            location_id=location.id,
            name=name,
            slug=entry.get("slug") or _slug_for(name, db),
            short_description=entry.get("short_description"),
            description=entry.get("description"),
            phone=normalize_phone(entry["phone"]) if entry.get("phone") else None,
            whatsapp=normalize_phone(entry["whatsapp"]) if entry.get("whatsapp") else None,
            address_text=entry.get("address_text"),
            status=status,
            rejection_reason=entry.get("rejection_reason"),
            created_at=created_at,
        )

        if status in (BusinessStatus.PENDING_REVIEW, BusinessStatus.APPROVED, BusinessStatus.REJECTED, BusinessStatus.SUSPENDED):
            business.submitted_at = created_at + timedelta(hours=1)
        if status in (BusinessStatus.APPROVED, BusinessStatus.SUSPENDED):
            business.approved_at = created_at + timedelta(hours=6)
            business.approved_by = admin.id if admin else None

        db.add(business)
        db.flush()

        # Logo + cover + two gallery images.
        for kind, size in (
            (ImageKind.LOGO, (400, 400)),
            (ImageKind.COVER, (1200, 675)),
            (ImageKind.GALLERY, (900, 700)),
            (ImageKind.GALLERY, (900, 700)),
        ):
            sort_order = 0 if kind is not ImageKind.GALLERY else len(
                [i for i in business.images if i.kind is ImageKind.GALLERY]
            )
            stored = images.process_and_store(
                data=_placeholder_image(name, index + sort_order, size),
                content_type="image/jpeg",
                business_id=business.id,
                kind=kind,
            )
            business.images.append(
                BusinessImage(
                    business_id=business.id,
                    url=stored.url,
                    storage_key=stored.key,
                    kind=kind,
                    sort_order=sort_order,
                    width=stored.width,
                    height=stored.height,
                    size_bytes=stored.size_bytes,
                )
            )
            if kind is ImageKind.LOGO:
                business.logo_url, business.logo_storage_key = stored.url, stored.key
            elif kind is ImageKind.COVER:
                business.cover_url, business.cover_storage_key = stored.url, stored.key

        for platform, url in (entry.get("socials") or {}).items():
            business.social_links.append(
                BusinessSocialLink(
                    business_id=business.id, platform=SocialPlatform(platform), url=url
                )
            )

        for order, item in enumerate(entry.get("items") or []):
            business.items.append(
                BusinessItem(
                    business_id=business.id,
                    title=item["title"],
                    description=item.get("description"),
                    price=Decimal(item["price"]) if item.get("price") else None,
                    currency=Currency.USD,
                    is_available=bool(item.get("is_available", True)),
                    sort_order=order,
                )
            )

        db.flush()
        business.search_text = build_search_text(
            business.name,
            business.short_description,
            business.description,
            business.address_text,
            category.name_ar,
            location.name_ar,
            " ".join(item.title for item in business.items),
        )

        _seed_moderation_history(db, business, admin, entry.get("suspension_reason"))
        created += 1

    db.flush()
    logger.info("Businesses seeded", extra={"created_count": created})
    return created


def _seed_moderation_history(
    db,  # type: ignore[no-untyped-def]
    business: Business,
    admin: User | None,
    suspension_reason: str | None = None,
) -> None:
    """Recreate the audit trail that would have produced this status."""
    trail: list[tuple[ModerationActionType, BusinessStatus, BusinessStatus, str | None]] = []
    if business.status is not BusinessStatus.DRAFT:
        trail.append((ModerationActionType.SUBMIT, BusinessStatus.DRAFT, BusinessStatus.PENDING_REVIEW, None))
    if business.status is BusinessStatus.APPROVED:
        trail.append((ModerationActionType.APPROVE, BusinessStatus.PENDING_REVIEW, BusinessStatus.APPROVED, None))
    elif business.status is BusinessStatus.REJECTED:
        trail.append(
            (ModerationActionType.REJECT, BusinessStatus.PENDING_REVIEW, BusinessStatus.REJECTED, business.rejection_reason)
        )
    elif business.status is BusinessStatus.SUSPENDED:
        trail.append((ModerationActionType.APPROVE, BusinessStatus.PENDING_REVIEW, BusinessStatus.APPROVED, None))
        trail.append(
            (
                ModerationActionType.SUSPEND,
                BusinessStatus.APPROVED,
                BusinessStatus.SUSPENDED,
                suspension_reason,
            )
        )

    for action, from_status, to_status, reason in trail:
        is_admin_action = action is not ModerationActionType.SUBMIT
        db.add(
            ModerationAction(
                business_id=business.id,
                admin_id=admin.id if (is_admin_action and admin) else None,
                actor_id=(admin.id if is_admin_action and admin else business.owner_id),
                action=action,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
            )
        )


def _slug_for(name: str, db) -> str:  # type: ignore[no-untyped-def]
    from app.repositories.business import BusinessRepository
    from app.services.slug import unique_slug

    return unique_slug(name, BusinessRepository(db).slug_exists)


def reset(db) -> None:  # type: ignore[no-untyped-def]
    """Remove seeded content. Never run against production data."""
    for model in (
        ModerationAction, BusinessItem, BusinessImage, BusinessSocialLink,
        Business, OtpRequest, RateLimitEvent, Category, Location, User,
    ):
        db.execute(delete(model))
    db.flush()
    logger.info("Existing data cleared")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed database content")
    parser.add_argument("--reset", action="store_true", help="delete existing data first")
    parser.add_argument(
        "--admin-only",
        action="store_true",
        help="create or update only the administrator account (safe in production)",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)

    if settings.is_production and not args.admin_only:
        logger.error(
            "Refusing to seed sample data into a production database. "
            "Use --admin-only to bootstrap the administrator account."
        )
        return 1
    if args.reset and settings.is_production:
        logger.error("--reset is never allowed against a production database")
        return 1

    with session_scope() as db:
        if args.admin_only:
            admin = seed_admin(db)
            if admin is None:
                logger.error("ADMIN_EMAIL and ADMIN_PASSWORD must both be set")
                return 1
            print(f"\nAdministrator ready: {settings.admin_email}\n")
            return 0

        if args.reset:
            reset(db)
        categories = seed_categories(db)
        locations = seed_locations(db)
        admin = seed_admin(db)
        seed_businesses(db, categories, locations, admin)

    print("\nDevelopment data ready.")
    if settings.admin_email:
        print(f"   Admin panel: {settings.admin_email} / (ADMIN_PASSWORD from .env)")
    print(f"   Development OTP code: {settings.dev_fixed_otp_code}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
