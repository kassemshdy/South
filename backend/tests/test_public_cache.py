"""The in-memory cache for anonymous public reads (29 Oct 2026).

Served from memory for a short while, never for a request with a token,
never for owner or admin routes, and emptied -- in every worker -- by any
successful write, so a moderation decision is seen on the next request."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import cache as public_cache
from app.core.cache import PublicCache
from app.core.config import Settings, get_settings
from app.main import create_app
from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


@pytest.fixture
def cached_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_url=get_settings().database_url,
        public_cache_seconds=60,
        public_cache_version_file=str(tmp_path / "version"),
    )
    yield TestClient(create_app(settings))
    public_cache.configure(0, str(tmp_path / "off"))


def _approved_shop(client: TestClient, db: Session, category: Category, location: Location) -> Business:
    created = client.post(
        "/api/businesses",
        headers=sign_in(client, "03770011"),
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    shop = db.get(Business, created.json()["id"])
    assert shop is not None
    shop.status = BusinessStatus.APPROVED
    shop.logo_url = "/media/test/logo.jpg"
    db.commit()
    return shop


def test_a_public_read_is_served_from_memory_until_a_write(
    cached_client: TestClient, db: Session, admin: object, category: Category, location: Location
) -> None:
    client = cached_client
    shop = _approved_shop(client, db, category, location)

    first = client.get("/api/businesses")
    assert first.headers["x-cache"] == "MISS"
    assert client.get("/api/businesses").headers["x-cache"] == "HIT"

    # A change straight in the database is not seen while the entry lives...
    shop.status = BusinessStatus.SUSPENDED
    db.commit()
    assert [b["slug"] for b in client.get("/api/businesses").json()["items"]] == [shop.slug]

    # ...but any write through the API empties it, as a moderation action does.
    client.post(
        f"/api/admin/businesses/{shop.id}/reactivate", headers=admin_headers(client)
    )
    after = client.get("/api/businesses")
    assert after.headers["x-cache"] == "MISS"


def test_nothing_with_a_token_and_no_private_route_is_cached(
    cached_client: TestClient, admin: object
) -> None:
    client = cached_client
    headers = admin_headers(client)
    client.get("/api/categories", headers=headers)
    assert client.get("/api/categories", headers=headers).headers.get("x-cache") is None
    client.get("/api/admin/stats", headers=headers)
    assert "x-cache" not in client.get("/api/admin/stats", headers=headers).headers
    assert "x-cache" not in client.get("/api/me").headers


def test_a_counted_page_still_counts_every_view(
    cached_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    client = cached_client
    shop = _approved_shop(client, db, category, location)
    for _ in range(3):
        response = client.get(f"/api/businesses/{shop.slug}")
        assert response.status_code == 200
        assert "x-cache" not in response.headers, "never cached as a response"
    from app.models.analytics import ListingViewDaily

    views = db.query(ListingViewDaily).filter(ListingViewDaily.subject_id == shop.id).all()
    assert sum(row.views for row in views) == 3


def test_a_write_in_one_worker_empties_another(tmp_path: Path) -> None:
    version = tmp_path / "version"
    one, two = PublicCache(60, version), PublicCache(60, version)
    two.set("k", "v")
    assert two.get("k") == "v"
    one.invalidate()
    assert two.get("k") is None


def test_off_means_off(tmp_path: Path) -> None:
    cache = PublicCache(0, tmp_path / "version")
    cache.set("k", "v")
    assert cache.get("k") is None
