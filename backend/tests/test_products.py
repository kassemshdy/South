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


# --- Sitemap ---------------------------------------------------------------
#
# Products had public pages and a directory and appeared in neither the
# sitemap nor robots' view of the site, so nothing told a crawler they
# existed. Advertising them means the two visibility rules above now have a
# second audience, and a crawler is the one visitor who will follow every URL
# it is handed — so both rules are asserted here from that direction too.


def test_sitemap_lists_an_available_product(
    client: TestClient, db: Session, approved_business_with_items: str
) -> None:
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200

    assert "/products" in sitemap.text
    slug = _item_slug(db, ar("item.zaatar_local"))
    assert f"/product/{slug}" in sitemap.text


def test_sitemap_hides_an_unavailable_product(
    client: TestClient, db: Session, approved_business_with_items: str
) -> None:
    """An owner marking a product unavailable must not leave it advertised."""
    slug = _item_slug(db, ar("item.generic"))
    assert client.get(f"/api/items/{slug}").status_code == 404
    assert f"/product/{slug}" not in client.get("/sitemap.xml").text


def test_sitemap_hides_a_product_whose_business_is_not_approved(
    client: TestClient, db: Session, draft_business_with_item: str
) -> None:
    """The rule that matters most: a draft listing's products stay invisible."""
    slug = _item_slug(db, ar("item.zaatar_local"))
    assert f"/product/{slug}" not in client.get("/sitemap.xml").text


# --- Price filter ----------------------------------------------------------
#
# The two decisions inside this filter are the ones asserted here, because
# both are ways it could quietly lie to somebody:
#
# - a range across USD and LBP is meaningless, so a bound without a currency
#   is refused rather than guessed;
# - a product whose owner left the price blank is kept unless the *visitor*
#   says otherwise. Dropping it silently would penalise an owner for leaving
#   a field empty, which is exactly the listing this directory exists to
#   carry.


@pytest.fixture
def priced_catalogue(client: TestClient, db: Session, category: Category, location: Location) -> str:
    """One approved listing with a cheap item, a dear one, one priced in lira
    and one with no price at all."""
    headers = sign_in(client, "03950010")
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

    for payload in (
        {"title": ar("item.cheap"), "price": "2.00", "currency": "USD"},
        {"title": ar("item.dear"), "price": "45.00", "currency": "USD"},
        {"title": ar("item.lira_priced"), "price": "300000.00", "currency": "LBP"},
        {"title": ar("item.unpriced"), "currency": "USD"},
    ):
        created = client.post(
            f"/api/businesses/{business['id']}/items", headers=headers, json=payload
        )
        assert created.status_code == 201, created.text

    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return business["id"]


def _titles(client: TestClient, **params: object) -> set[str]:
    response = client.get("/api/items", params=params)
    assert response.status_code == 200, response.text
    return {item["title"] for item in response.json()["items"]}


def test_a_price_bound_without_a_currency_is_refused(
    client: TestClient, priced_catalogue: str
) -> None:
    response = client.get("/api/items", params={"max_price": "20"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "price_currency_required"


def test_an_inverted_range_is_refused(client: TestClient, priced_catalogue: str) -> None:
    response = client.get(
        "/api/items", params={"currency": "USD", "min_price": "50", "max_price": "10"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "price_range_invalid"


def test_a_range_only_matches_prices_in_the_named_currency(
    client: TestClient, priced_catalogue: str
) -> None:
    # 300000 LBP is inside 0-100 only if the two currencies are compared as
    # bare numbers, which is the bug this filter must not have.
    matches = _titles(client, currency="USD", min_price="0", max_price="100")
    assert ar("item.lira_priced") not in matches
    assert {ar("item.cheap"), ar("item.dear")} <= matches

    lira = _titles(client, currency="LBP", min_price="100000", max_price="500000")
    assert ar("item.lira_priced") in lira
    assert ar("item.cheap") not in lira


def test_a_range_narrows_within_one_currency(client: TestClient, priced_catalogue: str) -> None:
    matches = _titles(client, currency="USD", max_price="10")
    assert ar("item.cheap") in matches
    assert ar("item.dear") not in matches


def test_a_product_with_no_price_survives_the_filter_by_default(
    client: TestClient, priced_catalogue: str
) -> None:
    matches = _titles(client, currency="USD", max_price="10")
    assert ar("item.unpriced") in matches


def test_the_visitor_can_drop_products_with_no_price(
    client: TestClient, priced_catalogue: str
) -> None:
    matches = _titles(client, currency="USD", max_price="10", include_unpriced="false")
    assert matches == {ar("item.cheap")}


def test_currency_alone_filters_without_a_range(client: TestClient, priced_catalogue: str) -> None:
    matches = _titles(client, currency="LBP", include_unpriced="false")
    assert matches == {ar("item.lira_priced")}


def test_no_price_filter_returns_everything_available(
    client: TestClient, priced_catalogue: str
) -> None:
    assert _titles(client) == {
        ar("item.cheap"),
        ar("item.dear"),
        ar("item.lira_priced"),
        ar("item.unpriced"),
    }


def test_the_price_filter_still_hides_what_a_visitor_may_not_see(
    client: TestClient, db: Session, priced_catalogue: str
) -> None:
    """A filter is a narrowing, never a way round ``public_query``."""
    record = db.get(Business, priced_catalogue)
    assert record is not None
    record.status = BusinessStatus.SUSPENDED
    db.commit()

    assert _titles(client, currency="USD", max_price="100") == set()
