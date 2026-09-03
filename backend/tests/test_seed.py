"""Regression coverage for the deploy-time seed script.

The API's pre-deploy step used to run before Railway mounted the media
volume, so seeded businesses could end up with image *rows* pointing at
bytes that were never written anywhere durable. ``seed_businesses`` must
detect and repair that on every run, not only create new content.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.models.business import Business
from app.services.images import ImageService
from app.storage.factory import get_storage
from scripts.seed import seed_admin, seed_businesses, seed_categories, seed_locations


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
