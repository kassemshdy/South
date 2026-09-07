"""Regression coverage for the deploy-time seed script.

The API's pre-deploy step used to run before Railway mounted the media
volume, so seeded businesses could end up with image *rows* pointing at
bytes that were never written anywhere durable. ``seed_businesses`` must
detect and repair that on every run, not only create new content.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.arabic import build_search_text
from app.core.config import get_settings
from app.models.business import Business
from app.models.talent import TalentProfile
from app.services.images import ImageService
from app.storage.factory import get_storage
from scripts.seed import (
    seed_admin,
    seed_businesses,
    seed_categories,
    seed_locations,
    seed_talent_skills,
    seed_talents,
)
from tests.samples import ar


def test_seed_businesses_repairs_missing_image_bytes(db):
    categories = seed_categories(db)
    locations = seed_locations(db)
    admin = seed_admin(db)
    created_first = seed_businesses(db, categories, locations, admin)
    db.commit()
    assert created_first > 0

    business = db.execute(select(Business)).scalars().first()
    business_id = business.id
    business_name = business.name
    assert business.images

    images = ImageService(get_storage(), get_settings())
    for image in business.images:
        get_storage().delete(image.storage_key)
    assert not all(images.exists(image.storage_key) for image in business.images)

    created_second = seed_businesses(db, categories, locations, admin)
    db.commit()
    assert created_second == 0

    db.expire_all()
    repaired = db.get(Business, business_id)
    assert repaired.images
    assert all(images.exists(image.storage_key) for image in repaired.images)
    assert repaired.logo_url and images.exists(repaired.logo_storage_key)
    assert repaired.cover_url and images.exists(repaired.cover_storage_key)

    duplicates = db.execute(
        select(Business).where(Business.name == business_name)
    ).scalars().all()
    assert len(duplicates) == 1


def test_seed_talents_backfills_detail_added_to_the_seed_file(db):
    """A profile seeded before the detail fields existed must gain them on the
    next run — a redeploy is the only chance staging gets to catch up."""
    locations = seed_locations(db)
    admin = seed_admin(db)
    skills = seed_talent_skills(db)
    assert seed_talents(db, skills, locations, admin) > 0
    db.commit()

    profile = db.execute(
        select(TalentProfile).where(TalentProfile.skills_text.is_not(None))
    ).scalars().first()
    assert profile is not None
    profile_id = profile.id

    # Simulate the pre-migration state: detail columns empty, no languages.
    profile.highest_degree = None
    profile.skills_text = None
    owner_text = ar('talent.owner_edited_services')
    profile.services_offered = owner_text
    profile.languages.clear()
    db.commit()

    assert seed_talents(db, skills, locations, admin) == 0
    db.commit()

    db.expire_all()
    healed = db.get(TalentProfile, profile_id)
    assert healed.highest_degree
    assert healed.skills_text
    assert healed.languages
    # An owner's own edit is never overwritten — only empty columns are filled.
    assert healed.services_offered == owner_text
    assert build_search_text(healed.skills_text) in healed.search_text


def test_seed_businesses_backfills_producer_detail(db):
    """Same rule as the talent backfill: a redeploy brings existing listings
    forward, without ever overwriting an owner's own edit."""
    categories = seed_categories(db)
    locations = seed_locations(db)
    admin = seed_admin(db)
    assert seed_businesses(db, categories, locations, admin) > 0
    db.commit()

    business = db.execute(
        select(Business).where(Business.production_nature.is_not(None))
    ).scalars().first()
    assert business is not None
    business_id = business.id

    owner_text = ar("business.institution_name")
    business.production_nature = None
    business.founding_date = None
    business.institution_name = owner_text
    db.commit()

    assert seed_businesses(db, categories, locations, admin) == 0
    db.commit()

    db.expire_all()
    healed = db.get(Business, business_id)
    assert healed.production_nature
    assert healed.founding_date is not None
    assert healed.institution_name == owner_text
    assert build_search_text(healed.production_nature) in healed.search_text
