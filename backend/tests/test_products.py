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
from tests.conftest import post_item, sign_in
from tests.samples import ar
from tests.test_uploads_and_urls import make_image


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
            "latitude": 33.27,
            "longitude": 35.2,
        },
    ).json()
    post_item(
        client,
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
            "latitude": 33.27,
            "longitude": 35.2,
            "whatsapp": "03950002",
        },
    ).json()
    post_item(
        client,
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.zaatar_local"), "price": "1.50", "currency": "USD"},
    )
    post_item(
        client,
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


def test_the_shops_with_products_filter_wants_something_on_sale(
    client: TestClient,
    db: Session,
    approved_business_with_items: str,
    category: Category,
    location: Location,
) -> None:
    """The products page lists shops (round 3): one with nothing on sale --
    no items, or only unavailable ones -- is not on it."""
    headers = sign_in(client, "03950003")
    empty = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()
    record = db.get(Business, empty["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()

    every = {row["id"] for row in client.get("/api/businesses").json()["items"]}
    assert every == {approved_business_with_items, empty["id"]}
    shops = client.get("/api/businesses", params={"with_products": "true"}).json()["items"]
    assert [row["id"] for row in shops] == [approved_business_with_items]

    for item in db.get(Business, approved_business_with_items).items:  # type: ignore[union-attr]
        item.is_available = False
    db.commit()
    shops = client.get("/api/businesses", params={"with_products": "true"}).json()["items"]
    assert shops == []


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
            "latitude": 33.27,
            "longitude": 35.2,
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
            "latitude": 33.27,
            "longitude": 35.2,
        },
    ).json()

    post_item(
        client,
        f"/api/businesses/{first_business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
    )
    post_item(
        client,
        f"/api/businesses/{second_business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
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
    # And the two origin pages, each its own address.
    assert "/products/local" in sitemap.text
    assert "/products/imported" in sitemap.text
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


# --- Price sort ------------------------------------------------------------
#
# This replaced a price *filter*, which needed a currency (a bound spanning
# USD and LBP means two things at once) plus a fourth control deciding what
# became of the products whose owner named no price. An ordering asks
# neither question, and the two things it must not do are asserted here:
#
# - it must not drop anything. An ordering is not a filter, and an owner who
#   left the price blank must not fall out of the directory for it;
# - a product with no stated price sorts last in *both* directions. Postgres
#   puts NULLs first descending, so "dearest first" would otherwise open with
#   the products that state no price -- a claim the data does not support.


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
            "latitude": 33.27,
            "longitude": 35.2,
        },
    ).json()

    for payload in (
        {"title": ar("item.cheap"), "price": "2.00", "currency": "USD"},
        {"title": ar("item.dear"), "price": "45.00", "currency": "USD"},
        {"title": ar("item.lira_priced"), "price": "300000.00", "currency": "LBP"},
        {"title": ar("item.unpriced"), "price": "1.00", "currency": "USD"},
    ):
        created = post_item(
            client,
            f"/api/businesses/{business['id']}/items", headers=headers, json=payload
        )
        assert created.status_code == 201, created.text
        # A price is required now, but products saved before it was carry
        # none, and the sorts must still put those last.
        if payload["title"] == ar("item.unpriced"):
            unpriced = db.get(BusinessItem, created.json()["id"])
            assert unpriced is not None
            unpriced.price = None

    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return business["id"]


def _titles(client: TestClient, **params: object) -> set[str]:
    response = client.get("/api/items", params=params)
    assert response.status_code == 200, response.text
    return {item["title"] for item in response.json()["items"]}


def _ordered(client: TestClient, sort: str) -> list[tuple[str, str | None]]:
    response = client.get("/api/items", params={"sort": sort})
    assert response.status_code == 200, response.text
    return [(item["title"], item["price"]) for item in response.json()["items"]]


EVERYTHING = {
    ar("item.cheap"),
    ar("item.dear"),
    ar("item.lira_priced"),
    ar("item.unpriced"),
}


@pytest.mark.parametrize("sort", ["price_asc", "price_desc"])
def test_a_price_sort_removes_nothing(
    client: TestClient, priced_catalogue: str, sort: str
) -> None:
    """The difference from the filter this replaced, and the reason it was
    replaced: nobody drops out of the directory for leaving a field blank."""
    assert {title for title, _ in _ordered(client, sort)} == EVERYTHING


@pytest.mark.parametrize("sort", ["price_asc", "price_desc"])
def test_a_product_with_no_stated_price_sorts_last_either_way(
    client: TestClient, priced_catalogue: str, sort: str
) -> None:
    ordered = _ordered(client, sort)
    assert ordered[-1][1] is None
    assert ordered[-1][0] == ar("item.unpriced")
    # ...and it is the only one there, so this is the tail rather than a
    # coincidence of a single-row result.
    assert [price for _, price in ordered[:-1]] == [
        price for _, price in ordered[:-1] if price is not None
    ]


def test_ascending_puts_the_cheapest_first(client: TestClient, priced_catalogue: str) -> None:
    priced = [
        (title, float(price)) for title, price in _ordered(client, "price_asc") if price is not None
    ]
    assert [price for _, price in priced] == sorted(price for _, price in priced)
    assert priced[0][0] == ar("item.cheap")


def test_descending_puts_the_dearest_first(client: TestClient, priced_catalogue: str) -> None:
    priced = [
        (title, float(price))
        for title, price in _ordered(client, "price_desc")
        if price is not None
    ]
    assert [price for _, price in priced] == sorted(
        (price for _, price in priced), reverse=True
    )
    # 300,000 lira, because the ordering compares the stored number and every
    # live listing shares a currency. Pinning it here so that the day a lira
    # listing appears beside a dollar one, this test says so out loud rather
    # than letting a $45 item quietly rank below a $3 one.
    assert priced[0][0] == ar("item.lira_priced")


def test_an_unknown_sort_is_refused(client: TestClient, priced_catalogue: str) -> None:
    assert client.get("/api/items", params={"sort": "price"}).status_code == 422


def test_a_price_sort_still_hides_what_a_visitor_may_not_see(
    client: TestClient, db: Session, priced_catalogue: str
) -> None:
    """An ordering is a rearrangement, never a way round ``public_query``."""
    record = db.get(Business, priced_catalogue)
    assert record is not None
    record.status = BusinessStatus.SUSPENDED
    db.commit()

    assert _titles(client, sort="price_asc") == set()


def test_a_product_needs_a_price_and_cannot_lose_it(
    client: TestClient, category: Category, location: Location
) -> None:
    """The owners made the price compulsory: refused without one, and an
    explicit null on an edit is refused rather than clearing it."""
    headers = sign_in(client, "03970099")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()
    refused = post_item(
        client,
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "currency": "USD"},
    )
    assert refused.status_code == 422, refused.text

    created = post_item(
        client,
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "price": "4.00", "currency": "USD"},
    ).json()
    cleared = client.put(
        f"/api/businesses/{business['id']}/items/{created['id']}",
        headers=headers,
        json={"price": None},
    )
    assert cleared.status_code == 422, cleared.text


def test_a_product_without_a_photo_stays_with_its_owner(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """The photo is mandatory (the owners' decision): a product saved without
    one -- before the rule, or after a failed upload -- is kept from the
    catalogue, its own page and the shop page until it has one, while its
    owner still sees it to add the photo."""
    headers = sign_in(client, "03950009")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.sweets_shop"),
            "short_description": ar("business.sweets_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    ).json()
    bare = client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
    )
    assert bare.status_code == 201, bare.text
    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()

    assert client.get("/api/items").json()["items"] == []
    assert client.get(f"/api/items/{_item_slug(db, ar('item.generic'))}").status_code == 404
    shop = client.get(f"/api/businesses/{business['slug']}").json()
    assert shop["items"] == []
    owned = client.get(f"/api/businesses/{business['id']}/items", headers=headers).json()
    assert [item["title"] for item in owned] == [ar("item.generic")]

    # Adding the photo is all it takes.
    photo = client.post(
        f"/api/businesses/{business['id']}/items/{bare.json()['id']}/image",
        headers=headers,
        files={"file": ("item.jpg", make_image((400, 300)), "image/jpeg")},
    )
    assert photo.status_code == 200, photo.text
    assert [i["title"] for i in client.get("/api/items").json()["items"]] == [ar("item.generic")]
    shop = client.get(f"/api/businesses/{business['slug']}").json()
    assert [i["title"] for i in shop["items"]] == [ar("item.generic")]
