"""The public products directory (`/items`).

A product is reachable independently of its business the instant that
business is `APPROVED` and the item itself is `is_available` — no new
moderation state. These tests exist to keep the two visibility rules (business
status, item availability) from being conflated with each other.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar


def _item_slug(db: Session, title: str) -> str:
    item = db.execute(select(BusinessItem).where(BusinessItem.title == title)).scalar_one()
    return item.slug


@pytest.fixture
def draft_business_with_item(client: TestClient, category: Category, location: Location) -> str:
    """An item on a business that never gets approved."""
    headers = sign_in(client, "03950001")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()
    client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.zaatar_local"), "price": "1.50", "currency": "USD"},
    )
    return business["id"]


def test_item_on_unapproved_business_is_excluded_from_search(
    client: TestClient, draft_business_with_item: str
) -> None:
    results = client.get("/api/items").json()
    assert results["items"] == []


def test_item_on_unapproved_business_404s_by_slug(
    client: TestClient, db: Session, draft_business_with_item: str
) -> None:
    slug = _item_slug(db, ar("item.zaatar_local"))
    response = client.get(f"/api/items/{slug}")
    assert response.status_code == 404


@pytest.fixture
def approved_business_with_items(
    client: TestClient, db: Session, category: Category, location: Location
) -> str:
    """An approved business with one available item and one unavailable item."""
    headers = sign_in(client, "03950002")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.sweets_shop"),
            "short_description": ar("business.sweets_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03950002",
        },
    ).json()
    client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.zaatar_local"), "price": "1.50", "currency": "USD"},
    )
    client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={
            "title": ar("item.generic"),
            "price": "2.00",
            "currency": "USD",
            "is_available": False,
        },
    )

    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return business["id"]


def test_available_item_is_searchable_and_reachable_by_slug(
    client: TestClient, db: Session, approved_business_with_items: str
) -> None:
    results = client.get("/api/items").json()
    assert [item["title"] for item in results["items"]] == [ar("item.zaatar_local")]

    slug = _item_slug(db, ar("item.zaatar_local"))
    detail = client.get(f"/api/items/{slug}").json()
    assert detail["title"] == ar("item.zaatar_local")
    assert detail["business"]["name"] == ar("business.sweets_shop")


def test_unavailable_item_excluded_from_search_but_visible_on_business_page(
    client: TestClient, db: Session, approved_business_with_items: str
) -> None:
    results = client.get("/api/items").json()
    assert ar("item.generic") not in [item["title"] for item in results["items"]]

    slug = _item_slug(db, ar("item.generic"))
    detail = client.get(f"/api/items/{slug}")
    assert detail.status_code == 404

    listing = client.get("/api/businesses", params={"q": ar("search.kunafa")}).json()
    business_slug = listing["items"][0]["slug"]
    profile = client.get(f"/api/businesses/{business_slug}").json()
    assert ar("item.generic") in [item["title"] for item in profile["items"]]


def test_category_and_location_filters_join_through_the_business(
    client: TestClient, db: Session, approved_business_with_items: str, category: Category, location: Location
) -> None:
    matches = client.get(
        "/api/items", params={"category": category.slug, "location": location.slug}
    ).json()
    assert [item["title"] for item in matches["items"]] == [ar("item.zaatar_local")]

    other_category = Category(name_ar=ar("category.sweets"), slug="sweets-products-test", sort_order=3)
    db.add(other_category)
    db.commit()
    no_matches = client.get("/api/items", params={"category": other_category.slug}).json()
    assert no_matches["items"] == []


def test_two_items_with_the_same_title_get_distinct_slugs(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03950003")
    first_business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()
    second_business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.second"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    client.post(
        f"/api/businesses/{first_business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "currency": "USD"},
    )
    client.post(
        f"/api/businesses/{second_business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "currency": "USD"},
    )

    slugs = {
        item.slug
        for item in db.execute(
            select(BusinessItem).where(BusinessItem.title == ar("item.generic"))
        ).scalars()
    }
    assert len(slugs) == 2
