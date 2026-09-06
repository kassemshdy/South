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
from tests.samples import ar


@pytest.fixture
def published(client: TestClient, db: Session, category: Category, location: Location) -> None:
    """Two approved businesses plus a town nested under the seeded district."""
    town = Location(
        name_ar=ar("location.qana"),
        slug="qana-test",
        type=LocationType.TOWN,
        parent_id=location.id,
    )
    other_category = Category(name_ar=ar("category.sweets"), slug="sweets-test", sort_order=2)
    db.add_all([town, other_category])
    db.commit()

    headers = sign_in(client, "03900001")

    first = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short_long"),
            "category_id": str(category.id),
            "location_id": str(town.id),
        },
    ).json()
    client.post(
        f"/api/businesses/{first['id']}/items",
        headers=headers,
        json={"title": ar("item.zaatar_local"), "price": "1.50", "currency": "USD"},
    )

    second = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.sweets_shop"),
            "short_description": ar("business.sweets_short"),
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
    results = client.get("/api/businesses", params={"q": ar("search.manakish")}).json()
    assert [item["name"] for item in results["items"]] == [ar("business.manakish")]


def test_search_matches_the_description(client: TestClient, published: None) -> None:
    results = client.get("/api/businesses", params={"q": ar("search.kunafa")}).json()
    assert [item["name"] for item in results["items"]] == [ar("business.sweets_shop")]


def test_search_matches_item_titles(client: TestClient, published: None) -> None:
    """Searching for a product finds the shop that sells it."""
    results = client.get("/api/businesses", params={"q": ar("item.zaatar")}).json()
    assert [item["name"] for item in results["items"]] == [ar("business.manakish")]


def test_search_ignores_arabic_spelling_variance(client: TestClient, published: None) -> None:
    """Spelling variants (shadda, hamza) must all find the same business."""
    for query in (
        ar("search.sweets"),
        ar("search.sweets_with_shadda"),
        ar("search.abu_ali_plain"),
        ar("search.abu_ali_hamza"),
    ):
        results = client.get("/api/businesses", params={"q": query}).json()
        assert results["meta"]["total"] == 1, query


@pytest.fixture
def published_other_category(
    client: TestClient, db: Session, category_other: Category, location: Location
) -> str:
    """An approved business under the "Other" category, findable by its own words."""
    headers = sign_in(client, "03900009")
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.other_shop"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category_other.id),
            "location_id": str(location.id),
            "custom_category_text": ar("business.custom_category_text"),
            "whatsapp": "03900009",
        },
    ).json()

    business = db.get(Business, created["id"])
    assert business is not None
    business.status = BusinessStatus.APPROVED
    db.commit()
    return created["id"]


def test_search_matches_custom_category_text_not_the_literal_other(
    client: TestClient, published_other_category: str
) -> None:
    results = client.get("/api/businesses", params={"q": ar("search.custom_category")}).json()
    assert [item["id"] for item in results["items"]] == [published_other_category]

    no_match = client.get("/api/businesses", params={"q": ar("category.other")}).json()
    assert no_match["meta"]["total"] == 0


def test_category_and_location_filters_combine(
    client: TestClient, published: None
) -> None:
    both = client.get(
        "/api/businesses", params={"category": "sweets-test", "q": ar("search.kunafa")}
    ).json()
    contradictory = client.get(
        "/api/businesses", params={"category": "sweets-test", "q": ar("search.manakish")}
    ).json()

    assert both["meta"]["total"] == 1
    assert contradictory["meta"]["total"] == 0


def test_filtering_by_district_includes_its_towns(
    client: TestClient, published: None, location: Location
) -> None:
    """A business in a town must appear when filtering by its district."""
    results = client.get("/api/businesses", params={"location": location.slug}).json()
    names = {item["name"] for item in results["items"]}

    assert ar("business.manakish") in names  # in the town
    assert ar("business.sweets_shop") in names  # directly in the district


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
    results = client.get("/api/businesses", params={"q": ar("search.no_match")})
    assert results.status_code == 200
    assert results.json()["items"] == []


def test_public_payload_excludes_private_fields(client: TestClient, published: None) -> None:
    """Owner phone and moderation state must never reach a visitor."""
    listing = client.get("/api/businesses", params={"q": ar("search.manakish")}).json()
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
    ("raw_key", "expected_key"),
    [
        ("normalize.manakish_diacritics", "normalize.manakish_expected"),
        ("normalize.sweets_shadda", "normalize.sweets_expected"),
        ("normalize.ahmad_hamza", "normalize.ahmad_expected"),
        ("normalize.ibrahim_hamza", "normalize.ibrahim_expected"),
        ("normalize.mustafa_maksura", "normalize.mustafa_expected"),
    ],
)
def test_arabic_normalization(raw_key: str, expected_key: str) -> None:
    assert normalize_arabic(ar(raw_key)) == ar(expected_key)


def test_arabic_normalization_of_empty_input() -> None:
    assert normalize_arabic("") == ""
    assert normalize_arabic(None) == ""


def test_build_search_text_skips_empty_parts() -> None:
    assert (
        build_search_text(ar("normalize.restaurant"), None, "", ar("location.tyre"))
        == ar("normalize.restaurant_and_city")
    )


def test_public_stats_counts_only_approved_businesses_and_distinct_towns(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    town_a = Location(name_ar=ar("location.qana"), slug="qana-stats", type=LocationType.TOWN, parent_id=location.id)
    town_b = Location(name_ar=ar("location.qana"), slug="qana-stats-2", type=LocationType.TOWN, parent_id=location.id)
    town_c = Location(name_ar=ar("location.qana"), slug="qana-stats-3", type=LocationType.TOWN, parent_id=location.id)
    db.add_all([town_a, town_b, town_c])
    db.commit()

    def create_business(phone: str, location_id: str) -> str:
        headers = sign_in(client, phone)
        return client.post(
            "/api/businesses",
            headers=headers,
            json={
                "name": ar("business.manakish"),
                "short_description": ar("business.manakish_short"),
                "category_id": str(category.id),
                "location_id": location_id,
            },
        ).json()["id"]

    # In the district itself (not a town), and two businesses sharing one town —
    # neither should inflate the town count beyond the distinct towns involved.
    approved_ids = [
        create_business("03910001", str(location.id)),
        create_business("03910002", str(town_a.id)),
        create_business("03910003", str(town_a.id)),
        create_business("03910004", str(town_b.id)),
    ]
    for business_id in approved_ids:
        business = db.get(Business, business_id)
        assert business is not None
        business.status = BusinessStatus.APPROVED
        db.commit()

    # A business in a third town that never gets approved must not count at all —
    # neither towards total_businesses nor towards total_towns.
    create_business("03910005", str(town_c.id))

    stats = client.get("/api/businesses/stats")
    assert stats.status_code == 200, stats.text
    assert stats.json() == {"total_businesses": 4, "total_towns": 2, "total_talents": 0}
