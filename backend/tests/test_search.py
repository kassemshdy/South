"""Search, filtering, pagination and Arabic normalization."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.arabic import build_search_text, normalize_arabic
from app.models.business import Business
from app.models.enums import BusinessStatus, LocationType
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in


@pytest.fixture
def published(client: TestClient, db: Session, category: Category, location: Location) -> None:
    """Two approved businesses plus a town nested under the seeded district."""
    town = Location(name_ar="قانا", slug="qana-test", type=LocationType.TOWN, parent_id=location.id)
    other_category = Category(name_ar="حلويات", slug="sweets-test", sort_order=2)
    db.add_all([town, other_category])
    db.commit()

    headers = sign_in(client, "03900001")

    first = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": "مناقيش الضيعة",
            "short_description": "مناقيش وفطائر على الصاج",
            "category_id": str(category.id),
            "location_id": str(town.id),
        },
    ).json()
    client.post(
        f"/api/businesses/{first['id']}/items",
        headers=headers,
        json={"title": "زعتر بلدي", "price": "1.50", "currency": "USD"},
    )

    second = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": "حلويات أبو علي",
            "short_description": "كنافة وبقلاوة",
            "category_id": str(other_category.id),
            "location_id": str(location.id),
        },
    ).json()

    for created in (first, second):
        business = db.get(Business, created["id"])
        assert business is not None
        business.status = BusinessStatus.APPROVED
        db.commit()


def test_search_matches_the_business_name(client: TestClient, published: None) -> None:
    results = client.get("/api/businesses", params={"q": "مناقيش"}).json()
    assert [item["name"] for item in results["items"]] == ["مناقيش الضيعة"]


def test_search_matches_the_description(client: TestClient, published: None) -> None:
    results = client.get("/api/businesses", params={"q": "كنافة"}).json()
    assert [item["name"] for item in results["items"]] == ["حلويات أبو علي"]


def test_search_matches_item_titles(client: TestClient, published: None) -> None:
    """Searching for a product finds the shop that sells it."""
    results = client.get("/api/businesses", params={"q": "زعتر"}).json()
    assert [item["name"] for item in results["items"]] == ["مناقيش الضيعة"]


def test_search_ignores_arabic_spelling_variance(client: TestClient, published: None) -> None:
    """حلويّات / حلويات and أبو / ابو must all find the same business."""
    for query in ("حلويات", "حلويّات", "ابو علي", "أبو علي"):
        results = client.get("/api/businesses", params={"q": query}).json()
        assert results["meta"]["total"] == 1, query


def test_category_and_location_filters_combine(
    client: TestClient, published: None
) -> None:
    both = client.get(
        "/api/businesses", params={"category": "sweets-test", "q": "كنافة"}
    ).json()
    contradictory = client.get(
        "/api/businesses", params={"category": "sweets-test", "q": "مناقيش"}
    ).json()

    assert both["meta"]["total"] == 1
    assert contradictory["meta"]["total"] == 0


def test_filtering_by_district_includes_its_towns(
    client: TestClient, published: None, location: Location
) -> None:
    """A business in قانا must appear when filtering by صور, its district."""
    results = client.get("/api/businesses", params={"location": location.slug}).json()
    names = {item["name"] for item in results["items"]}

    assert "مناقيش الضيعة" in names  # in the town
    assert "حلويات أبو علي" in names  # directly in the district


def test_sorting_by_name(client: TestClient, published: None) -> None:
    results = client.get("/api/businesses", params={"sort": "name"}).json()
    names = [item["name"] for item in results["items"]]
    assert names == sorted(names)


def test_pagination_metadata(client: TestClient, published: None) -> None:
    page = client.get("/api/businesses", params={"page": 1, "page_size": 1}).json()

    assert page["meta"]["total"] == 2
    assert page["meta"]["total_pages"] == 2
    assert page["meta"]["has_next"] is True
    assert page["meta"]["has_previous"] is False
    assert len(page["items"]) == 1


def test_no_results_returns_an_empty_page_not_an_error(client: TestClient, published: None) -> None:
    results = client.get("/api/businesses", params={"q": "لا يوجد شيء بهذا الاسم"})
    assert results.status_code == 200
    assert results.json()["items"] == []


def test_public_payload_excludes_private_fields(client: TestClient, published: None) -> None:
    """Owner phone and moderation state must never reach a visitor."""
    listing = client.get("/api/businesses", params={"q": "مناقيش"}).json()
    slug = listing["items"][0]["slug"]
    profile = client.get(f"/api/businesses/{slug}").json()

    for forbidden in ("owner_phone", "owner_id", "status", "rejection_reason", "search_text"):
        assert forbidden not in profile, forbidden


def test_sitemap_lists_only_approved_businesses(client: TestClient, published: None) -> None:
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert sitemap.text.count("<url>") >= 2


def test_robots_disallows_private_areas(client: TestClient) -> None:
    robots = client.get("/robots.txt").text
    assert "Disallow: /admin" in robots
    assert "Disallow: /dashboard" in robots
    assert "Sitemap:" in robots


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("مَنَاقيشُ الضَّيْعَة", "مناقيش الضيعه"),
        ("حلويّات", "حلويات"),
        ("أحمد", "احمد"),
        ("إبراهيم", "ابراهيم"),
        ("مصطفى", "مصطفي"),
        ("", ""),
    ],
)
def test_arabic_normalization(raw: str, expected: str) -> None:
    assert normalize_arabic(raw) == expected


def test_build_search_text_skips_empty_parts() -> None:
    assert build_search_text("مطعم", None, "", "صور") == "مطعم صور"
