"""The admin products page (the owners' request, 11 Nov 2026): every
product listed whatever its state, edited and re-photographed by staff
through the same rules as the owner's own routes."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, post_item
from tests.samples import ar
from tests.test_admin_corrections import _listing
from tests.test_uploads_and_urls import make_image


def _product(client: TestClient, category: Category, location: Location) -> tuple[str, str]:
    business_id, owner = _listing(client, category, location)
    created = post_item(
        client,
        f"/api/businesses/{business_id}/items",
        headers=owner,
        json={"title": ar("item.generic"), "price": "2.00", "currency": "USD"},
    )
    assert created.status_code == 201, created.text
    return business_id, created.json()["id"]


def test_staff_see_every_product_with_its_shop_even_a_hidden_one(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, item_id = _product(client, category, location)
    headers = admin_headers(client)

    # The shop is a draft: no visitor sees this product, staff still do.
    listed = client.get("/api/admin/items", headers=headers)
    assert listed.status_code == 200, listed.text
    row = listed.json()["items"][0]
    assert row["item"]["id"] == item_id
    assert row["shop"]["id"] == business_id
    assert row["shop"]["status"] == "DRAFT"

    hidden = client.put(
        f"/api/admin/businesses/{business_id}/items/{item_id}",
        headers=headers,
        json={"is_available": False},
    )
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["item"]["is_available"] is False

    only_hidden = client.get("/api/admin/items", headers=headers, params={"available": False})
    assert [r["item"]["id"] for r in only_hidden.json()["items"]] == [item_id]
    assert client.get(
        "/api/admin/items", headers=headers, params={"available": True}
    ).json()["items"] == []
    assert client.get(
        "/api/admin/items", headers=headers, params={"shop": business_id}
    ).json()["meta"]["total"] == 1

    # The shop filter lists it with its count, hidden product included.
    shops = client.get("/api/admin/items/shops", headers=headers)
    assert shops.status_code == 200, shops.text
    assert [(s["id"], s["count"]) for s in shops.json()] == [(business_id, 1)]


def test_staff_edit_a_product_and_replace_its_photo(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, item_id = _product(client, category, location)
    headers = admin_headers(client)
    path = f"/api/admin/businesses/{business_id}/items/{item_id}"

    renamed = client.put(
        path, headers=headers, json={"title": ar("item.zaatar_local"), "price": "3.50"}
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["item"]["title"] == ar("item.zaatar_local")
    assert renamed.json()["item"]["price"] == "3.50"

    # Found by its new name: the search text follows the edit.
    found = client.get("/api/admin/items", headers=headers, params={"q": ar("item.zaatar_local")})
    assert [r["item"]["id"] for r in found.json()["items"]] == [item_id]

    before = renamed.json()["item"]["image_url"]
    photo = client.post(
        f"{path}/image",
        headers=headers,
        files={"file": ("p.jpg", make_image(), "image/jpeg")},
    )
    assert photo.status_code == 200, photo.text
    assert photo.json()["item"]["image_url"] and photo.json()["item"]["image_url"] != before


def test_a_product_is_reached_only_through_its_own_shop(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, item_id = _product(client, category, location)
    other = "00000000-0000-0000-0000-000000000001"
    refused = client.put(
        f"/api/admin/businesses/{other}/items/{item_id}",
        headers=admin_headers(client),
        json={"title": ar("item.generic")},
    )
    assert refused.status_code == 404


def test_the_products_page_is_staff_only(client: TestClient) -> None:
    assert client.get("/api/admin/items").status_code == 401


def test_a_product_has_its_own_category_and_its_shop_is_found_under_both(
    client: TestClient,
    db: Session,
    admin: User,
    category: Category,
    category_other: Category,
    location: Location,
) -> None:
    """The owners' ticket (16 Nov 2026) and decision (17 Nov 2026)."""
    business_id, item_id = _product(client, category, location)
    headers = admin_headers(client)
    path = f"/api/admin/businesses/{business_id}/items/{item_id}"

    # A new product follows its shop.
    first = client.get("/api/admin/items", headers=headers).json()["items"][0]["item"]
    assert first["category_id"] is None and first["category"]["slug"] == category.slug

    moved = client.put(path, headers=headers, json={"category_id": str(category_other.id)})
    assert moved.status_code == 200, moved.text
    assert moved.json()["item"]["category"]["slug"] == category_other.slug
    by = lambda slug: [  # noqa: E731
        r["item"]["id"]
        for r in client.get("/api/admin/items", headers=headers, params={"category": slug})
        .json()["items"]
    ]
    assert by(category_other.slug) == [item_id] and by(category.slug) == []

    # Public: approved with a photo, the product is under its own category
    # and its shop under both.
    business = db.get(Business, uuid.UUID(business_id))
    assert business is not None
    business.status = BusinessStatus.APPROVED
    db.get(BusinessItem, uuid.UUID(item_id)).image_url = "/media/x.jpg"  # type: ignore[union-attr]
    db.commit()
    products = client.get("/api/items", params={"category": category_other.slug}).json()
    assert [p["id"] for p in products["items"]] == [item_id]
    assert products["items"][0]["category"]["slug"] == category_other.slug
    for slug in (category.slug, category_other.slug):
        shops = client.get("/api/businesses", params={"category": slug}).json()["items"]
        assert [s["id"] for s in shops] == [business_id], slug

    # The shop's own category picked again means "follow the shop".
    back = client.put(path, headers=headers, json={"category_id": str(category.id)})
    assert back.json()["item"]["category_id"] is None
    assert client.put(path, headers=headers, json={"category_id": str(uuid.uuid4())}).status_code == 422
