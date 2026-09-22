"""Development seed script.

Idempotent: safe to re-run. Creates categories, talent skills, the South Lebanon
location tree, sample businesses and talent profiles across every moderation
status, and the administrator account from environment configuration (never a
hardcoded production credential).

Usage:
    python -m scripts.seed               # add missing records
    python -m scripts.seed --reset       # wipe seeded content first
    python -m scripts.seed --admin-only  # create/update only the administrator
    python -m scripts.seed --ensure      # seed whatever this environment permits

Sample businesses and talent profiles are fixtures: they are created in
development and staging (a
staging deployment nobody can click through is not much of a staging
deployment) and never in production. Bootstrapping the administrator is a
legitimate production operation and is always allowed.

``--ensure`` is the deploy-time entry point. It seeds what the environment
permits and exits successfully either way, so it can run before every deploy
without blocking a production release.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from datetime import UTC, date, datetime, timedelta
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
from app.models.article import Article
from app.models.auth import RateLimitEvent
from app.models.business import (
    Business,
    BusinessImage,
    BusinessItem,
    BusinessSocialLink,
    ModerationAction,
)
from app.models.enums import (
    ArticleSection,
    BusinessStatus,
    Currency,
    ImageKind,
    LanguageProficiency,
    LocationType,
    ModerationActionType,
    SocialPlatform,
    UserRole,
)
from app.models.talent import (
    TalentImage,
    TalentLanguage,
    TalentModerationAction,
    TalentProfile,
    TalentSkill,
)
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services.images import ImageService
from app.storage.factory import get_storage
from scripts.seed_data import (
    ARTICLES,
    BUSINESSES,
    CATEGORIES,
    DEMO_OWNERS,
    LOCATIONS,
    TALENT_SKILLS,
    TALENTS,
    BusinessSeed,
    LocationSeed,
    TalentSeed,
)

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


def _demo_owner(db, owner_phone: str) -> User:  # type: ignore[no-untyped-def]
    """The account a seeded listing belongs to, created if it is not there.

    Sign-in is by password, so a seeded owner with no password is a listing
    whose dashboard nobody can open — fine for a real account, which waits for
    an administrator to issue credentials, and useless for demo data and for
    the end-to-end suite, which both need to get in.

    ``SEED_OWNER_PASSWORD`` is therefore applied here when it is set, on every
    run rather than only at creation, so changing it in the environment is
    enough to make these accounts usable again. It is refused in production by
    ``Settings.enforce_production_safety`` — these phone numbers are in this
    repository, so their password would be too.
    """
    phone = normalize_phone(owner_phone)
    owner = db.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()
    if owner is None:
        owner = User(phone_number=phone, role=UserRole.OWNER)
        db.add(owner)

    password = get_settings().seed_owner_password
    if password:
        owner.password_hash = hash_password(password)
        # Demo data is for looking at, not for walking through a first
        # sign-in: the forced change would put a password screen in front of
        # every one of these accounts.
        owner.must_change_password = False

    db.flush()
    return owner


def seed_demo_owners(db) -> int:  # type: ignore[no-untyped-def]
    """Owner accounts with a password and nothing listed under them.

    Every owner seeded alongside a business already has one, so neither a
    person looking at a deployed demo nor the end-to-end suite can walk the
    owner journey from its beginning: an empty dashboard, a first listing, a
    first submission. These are for that.

    Skipped entirely without ``SEED_OWNER_PASSWORD``, which production
    refuses to boot with — an account nobody can sign into is not seed data.
    """
    if not get_settings().seed_owner_password:
        logger.info("SEED_OWNER_PASSWORD not set; skipping demo owner accounts")
        return 0

    for entry in DEMO_OWNERS:
        _demo_owner(db, entry["phone"])

    logger.info("Demo owner accounts seeded", extra={"count": len(DEMO_OWNERS)})
    return len(DEMO_OWNERS)


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


_BUSINESS_DETAIL_FIELDS = ("institution_name", "production_nature")


def _seed_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _business_search_text(
    business: Business, category_name: str, location_name: str
) -> str:
    """The same haystack ``BusinessService`` builds, so a seeded listing is as
    findable as an owner-authored one."""
    return build_search_text(
        business.name,
        business.short_description,
        business.description,
        business.institution_name,
        business.production_nature,
        business.address_text,
        category_name,
        location_name,
        " ".join(item.title for item in business.items),
    )


def _backfill_business_detail(business: Business, entry: BusinessSeed) -> None:
    """Fill in producer detail a seed file grew after this listing was created.

    Only ever writes where the column is still empty, so a real edit made
    through the dashboard is never overwritten — the same conservative rule
    the image self-healing follows.
    """
    changed = False
    for field in _BUSINESS_DETAIL_FIELDS:
        value = entry.get(field)  # type: ignore[misc]
        if value and getattr(business, field) is None:
            setattr(business, field, value)
            changed = True

    founding = _seed_date(entry.get("founding_date"))
    if founding and business.founding_date is None:
        business.founding_date = founding
        changed = True

    if changed:
        category = business.category.name_ar if business.category else ""
        location = business.location.name_ar if business.location else ""
        business.search_text = _business_search_text(business, category, location)


def seed_businesses(db, categories, locations, admin) -> int:  # type: ignore[no-untyped-def]
    settings = get_settings()
    images = ImageService(get_storage(), settings)
    created = 0

    for index, entry in enumerate(BUSINESSES):
        name = entry["name"]
        existing = db.execute(select(Business).where(Business.name == name)).scalar_one_or_none()
        if existing is not None:
            # A prior deploy may have written image *rows* whose bytes never
            # reached the storage backend (e.g. a pre-deploy step that ran
            # before a volume was mounted). Detect and repair that rather
            # than silently leaving broken image URLs live.
            if not all(images.exists(image.storage_key) for image in existing.images):
                _reattach_images(db, images, existing, name, index)
            _backfill_business_detail(existing, entry)
            continue

        owner = _demo_owner(db, entry["owner_phone"])

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
            institution_name=entry.get("institution_name"),
            founding_date=_seed_date(entry.get("founding_date")),
            production_nature=entry.get("production_nature"),
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

        _reattach_images(db, images, business, name, index)

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
                    slug=_item_slug_for(item["title"], db),
                    description=item.get("description"),
                    price=Decimal(item["price"]) if item.get("price") else None,
                    currency=Currency.USD,
                    is_available=bool(item.get("is_available", True)),
                    sort_order=order,
                    search_text=build_search_text(item["title"], item.get("description")),
                )
            )

        db.flush()
        business.search_text = _business_search_text(
            business, category.name_ar, location.name_ar
        )

        _seed_moderation_history(db, business, admin, entry.get("suspension_reason"))
        created += 1

    db.flush()
    logger.info("Businesses seeded", extra={"created_count": created})
    return created


def _reattach_article_cover(  # type: ignore[no-untyped-def]
    db, images: ImageService, article: Article, index: int
) -> None:
    """(Re)generate the cover placeholder for ``article``.

    Also the repair path for an article row that survived a deploy whose
    image bytes never reached storage, the same hazard ``seed_businesses``
    guards against.
    """
    images.delete(article.cover_storage_key)
    stored = images.process_and_store(
        data=_placeholder_image(article.title, index, (1200, 675)),
        content_type="image/jpeg",
        owner_id=article.id,
        kind=ImageKind.COVER,
        prefix="articles",
    )
    article.cover_url, article.cover_storage_key = stored.url, stored.key
    db.flush()


def seed_articles(db) -> int:  # type: ignore[no-untyped-def]
    """Publish the sample articles, so /blog and /news are not empty.

    Seeded as published rather than draft: an empty section renders its
    "nothing here yet" state, which is exactly what these fixtures exist to
    replace. Matched on slug, so re-running never duplicates one and an
    administrator's own edits to the title or body survive a redeploy.
    """
    settings = get_settings()
    images = ImageService(get_storage(), settings)
    created = 0

    for index, entry in enumerate(ARTICLES):
        slug = entry["slug"]
        existing = db.execute(select(Article).where(Article.slug == slug)).scalar_one_or_none()
        if existing is not None:
            if not images.exists(existing.cover_storage_key):
                _reattach_article_cover(db, images, existing, index)
            continue

        published_at = datetime.now(UTC) - timedelta(days=len(ARTICLES) - index)
        article = Article(
            section=ArticleSection(entry["section"]),
            slug=slug,
            title=entry["title"],
            body=entry["body"],
            is_published=True,
            published_at=published_at,
            created_at=published_at,
        )
        db.add(article)
        db.flush()
        _reattach_article_cover(db, images, article, index)
        created += 1

    db.flush()
    logger.info("Articles seeded", extra={"created_count": created})
    return created


def seed_talent_skills(db) -> dict[str, TalentSkill]:  # type: ignore[no-untyped-def]
    existing = {s.slug: s for s in db.execute(select(TalentSkill)).scalars().all()}
    for entry in TALENT_SKILLS:
        slug = str(entry["slug"])
        if slug in existing:
            continue
        skill = TalentSkill(
            name_ar=entry["name_ar"],
            slug=slug,
            icon=entry.get("icon"),
            sort_order=int(entry["sort_order"]),
        )
        db.add(skill)
        existing[slug] = skill
    db.flush()
    logger.info("Talent skills seeded", extra={"total_count": len(existing)})
    return existing


_TALENT_DETAIL_FIELDS = (
    "highest_degree",
    "specialization",
    "university",
    "experience",
    "skills_text",
    "services_offered",
)


def _talent_search_text(profile: TalentProfile, skill_name: str, location_name: str) -> str:
    """The same haystack ``TalentService`` builds, so a seeded profile is as
    findable as an owner-authored one."""
    return build_search_text(
        profile.display_name,
        profile.bio,
        profile.skills_text,
        profile.services_offered,
        skill_name,
        location_name,
    )


def _backfill_talent_detail(profile: TalentProfile, entry: TalentSeed) -> None:
    """Fill in detail fields a seed file grew after this profile was created.

    Only ever writes where the column is still empty, so a real edit made
    through the dashboard is never overwritten — the same conservative rule
    the image self-healing follows.
    """
    changed = False
    for field in _TALENT_DETAIL_FIELDS:
        value = entry.get(field)  # type: ignore[misc]
        if value and getattr(profile, field) is None:
            setattr(profile, field, value)
            changed = True

    if entry.get("languages") and not profile.languages:
        for order, language in enumerate(entry.get("languages", [])):
            profile.languages.append(
                TalentLanguage(
                    name=language["name"],
                    proficiency=LanguageProficiency(language["proficiency"]),
                    sort_order=order,
                )
            )
        changed = True

    if changed:
        skill_name = entry.get("custom_skill_text") or (
            profile.skill.name_ar if profile.skill else ""
        )
        location_name = profile.location.name_ar if profile.location else ""
        profile.search_text = _talent_search_text(profile, skill_name, location_name)


def seed_talents(db, skills, locations, admin) -> int:  # type: ignore[no-untyped-def]
    settings = get_settings()
    images = ImageService(get_storage(), settings)
    created = 0

    for index, entry in enumerate(TALENTS):
        display_name = entry["display_name"]
        existing = db.execute(
            select(TalentProfile).where(TalentProfile.display_name == display_name)
        ).scalar_one_or_none()
        if existing is not None:
            # Same self-healing rule as businesses: image rows can outlive the
            # bytes they point at when a deploy writes them without a volume.
            if not all(images.exists(image.storage_key) for image in existing.images):
                _reattach_talent_images(db, images, existing, display_name, index)
            _backfill_talent_detail(existing, entry)
            continue

        owner = _demo_owner(db, entry["owner_phone"])

        skill = skills[entry["skill"]]
        location = locations[entry["location"]]
        status = BusinessStatus(entry["status"])
        created_at = datetime.now(UTC) - timedelta(days=len(TALENTS) - index)

        profile = TalentProfile(
            owner_id=owner.id,
            skill_id=skill.id,
            custom_skill_text=entry.get("custom_skill_text"),
            location_id=location.id,
            display_name=display_name,
            slug=entry.get("slug") or _talent_slug_for(display_name, db),
            bio=entry.get("bio"),
            years_experience=entry.get("years_experience"),
            highest_degree=entry.get("highest_degree"),
            specialization=entry.get("specialization"),
            university=entry.get("university"),
            experience=entry.get("experience"),
            skills_text=entry.get("skills_text"),
            services_offered=entry.get("services_offered"),
            phone=normalize_phone(entry["phone"]) if entry.get("phone") else None,
            whatsapp=normalize_phone(entry["whatsapp"]) if entry.get("whatsapp") else None,
            website=entry.get("website"),
            status=status,
            rejection_reason=entry.get("rejection_reason"),
            created_at=created_at,
        )

        if status is not BusinessStatus.DRAFT:
            profile.submitted_at = created_at + timedelta(hours=1)
        if status in (BusinessStatus.APPROVED, BusinessStatus.SUSPENDED):
            profile.approved_at = created_at + timedelta(hours=6)
            profile.approved_by = admin.id if admin else None

        for order, language in enumerate(entry.get("languages", [])):
            profile.languages.append(
                TalentLanguage(
                    name=language["name"],
                    proficiency=LanguageProficiency(language["proficiency"]),
                    sort_order=order,
                )
            )

        db.add(profile)
        db.flush()

        _reattach_talent_images(db, images, profile, display_name, index)

        db.flush()
        profile.search_text = _talent_search_text(
            profile, entry.get("custom_skill_text") or skill.name_ar, location.name_ar
        )

        _seed_talent_moderation_history(db, profile, admin, entry.get("suspension_reason"))
        created += 1

    db.flush()
    logger.info("Talent profiles seeded", extra={"created_count": created})
    return created


def _reattach_images(  # type: ignore[no-untyped-def]
    db, images: ImageService, business: Business, name: str, index: int
) -> None:
    """(Re)generate the logo, cover and gallery placeholders for ``business``.

    Replaces whatever image rows it already has, so this is also the repair
    path for a business whose rows survived a broken deploy but whose bytes
    never reached storage.
    """
    for image in list(business.images):
        images.delete(image.storage_key)
        db.delete(image)
    business.images.clear()
    business.logo_url = business.logo_storage_key = None
    business.cover_url = business.cover_storage_key = None
    db.flush()

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
            owner_id=business.id,
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


def _reattach_talent_images(  # type: ignore[no-untyped-def]
    db, images: ImageService, profile: TalentProfile, name: str, index: int
) -> None:
    """(Re)generate the photo and portfolio placeholders for ``profile``."""
    for image in list(profile.images):
        images.delete(image.storage_key)
        db.delete(image)
    profile.images.clear()
    profile.photo_url = profile.photo_storage_key = None
    db.flush()

    for kind, size in (
        (ImageKind.LOGO, (400, 400)),
        (ImageKind.GALLERY, (900, 700)),
        (ImageKind.GALLERY, (900, 700)),
    ):
        sort_order = 0 if kind is not ImageKind.GALLERY else len(
            [i for i in profile.images if i.kind is ImageKind.GALLERY]
        )
        stored = images.process_and_store(
            data=_placeholder_image(name, index + sort_order, size),
            content_type="image/jpeg",
            owner_id=profile.id,
            kind=kind,
            prefix="talent",
        )
        profile.images.append(
            TalentImage(
                profile_id=profile.id,
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
            profile.photo_url, profile.photo_storage_key = stored.url, stored.key


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


def _seed_talent_moderation_history(
    db,  # type: ignore[no-untyped-def]
    profile: TalentProfile,
    admin: User | None,
    suspension_reason: str | None = None,
) -> None:
    """Recreate the audit trail that would have produced this status."""
    trail: list[tuple[ModerationActionType, BusinessStatus, BusinessStatus, str | None]] = []
    if profile.status is not BusinessStatus.DRAFT:
        trail.append((ModerationActionType.SUBMIT, BusinessStatus.DRAFT, BusinessStatus.PENDING_REVIEW, None))
    if profile.status is BusinessStatus.APPROVED:
        trail.append((ModerationActionType.APPROVE, BusinessStatus.PENDING_REVIEW, BusinessStatus.APPROVED, None))
    elif profile.status is BusinessStatus.REJECTED:
        trail.append(
            (ModerationActionType.REJECT, BusinessStatus.PENDING_REVIEW, BusinessStatus.REJECTED, profile.rejection_reason)
        )
    elif profile.status is BusinessStatus.SUSPENDED:
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
            TalentModerationAction(
                profile_id=profile.id,
                admin_id=admin.id if (is_admin_action and admin) else None,
                actor_id=(admin.id if is_admin_action and admin else profile.owner_id),
                action=action,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
            )
        )


def _talent_slug_for(name: str, db) -> str:  # type: ignore[no-untyped-def]
    from app.repositories.talent import TalentRepository
    from app.services.slug import unique_slug

    return unique_slug(name, TalentRepository(db).slug_exists, fallback_prefix="talent")


def _slug_for(name: str, db) -> str:  # type: ignore[no-untyped-def]
    from app.repositories.business import BusinessRepository
    from app.services.slug import unique_slug

    return unique_slug(name, BusinessRepository(db).slug_exists)


def _item_slug_for(title: str, db) -> str:  # type: ignore[no-untyped-def]
    from app.repositories.item import ItemRepository
    from app.services.slug import unique_slug

    return unique_slug(title, ItemRepository(db).slug_exists, fallback_prefix="item")


def reset(db) -> None:  # type: ignore[no-untyped-def]
    """Remove seeded content. Never run against production data."""
    for model in (
        TalentModerationAction, TalentImage, TalentProfile, TalentSkill,
        Article, ModerationAction, BusinessItem, BusinessImage, BusinessSocialLink,
        Business, RateLimitEvent, Category, Location, User,
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
        help="seed structure and the administrator only, no sample content (safe in production)",
    )
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="seed whatever this environment permits, without failing",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)

    # Two tiers, and the difference matters more than it looks.
    #
    # **Structure** is the categories, the locations, the talent skills and the
    # administrator: reference data the site cannot function without. A
    # listing form with no category to choose is not a degraded site, it is an
    # unusable one. This is seeded everywhere, production included.
    #
    # **Sample content** is demo owners, their businesses, talent profiles and
    # articles. Invented shops on the live directory would be a lie told to
    # every visitor, so this is development-only.
    #
    # The two used to be one switch, and setting APP_ENV=production turned
    # both off together. That quietly removed the recovery path `AGENTS.md`
    # documents: the `postgres` service has no persistent volume, so any
    # redeploy of it wipes the database, and the answer has always been
    # "redeploy the api, its start command re-runs migrations and the seed".
    # With structure switched off, that answer returned an empty site.
    #
    # Every seeder below is additive — it looks a row up by slug and creates
    # only what is missing — so running this against a live database with real
    # listings in it changes nothing that anyone has edited.
    sample_data_allowed = not settings.is_production
    structure_only = args.admin_only or (args.ensure and not sample_data_allowed)

    if args.ensure and not sample_data_allowed:
        logger.info(
            "Production database: seeding structure and the administrator, no sample content"
        )

    if not sample_data_allowed and not structure_only:
        logger.error(
            "Refusing to seed sample data into a production database. "
            "Use --admin-only to bootstrap structure and the administrator account."
        )
        return 1
    if args.reset and settings.is_hardened:
        logger.error("--reset is never allowed against a deployed database")
        return 1

    with session_scope() as db:
        if structure_only:
            seed_categories(db)
            seed_talent_skills(db)
            seed_locations(db)
            admin = seed_admin(db)
            if admin is None:
                logger.error("ADMIN_EMAIL and ADMIN_PASSWORD must both be set")
                return 1
            print(f"\nStructure ready. Administrator ready: {settings.admin_email}\n")
            return 0

        if args.reset:
            reset(db)
        categories = seed_categories(db)
        skills = seed_talent_skills(db)
        locations = seed_locations(db)
        admin = seed_admin(db)
        seed_demo_owners(db)
        seed_businesses(db, categories, locations, admin)
        seed_talents(db, skills, locations, admin)
        seed_articles(db)

    print("\nDevelopment data ready.")
    if settings.admin_email:
        print(f"   Admin panel: {settings.admin_email} / (ADMIN_PASSWORD from .env)")
    if settings.seed_owner_password:
        print("   Owner sign-in: any seeded owner_phone / (SEED_OWNER_PASSWORD from .env)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
