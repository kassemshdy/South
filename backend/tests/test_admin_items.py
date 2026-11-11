"""The admin products page (the owners' request, 11 Nov 2026): every
product listed whatever its state, edited and re-photographed by staff
through the same rules as the owner's own routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

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
