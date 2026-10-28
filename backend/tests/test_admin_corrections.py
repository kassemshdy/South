"""Corrections an administrator makes on an owner's behalf.

Two board tickets: moving a listing between the local and imported doors,
and giving a logo to a listing that went live without one.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, post_item, sign_in
from tests.samples import ar
from tests.test_uploads_and_urls import make_image


def _listing(client: TestClient, category: Category, location: Location) -> tuple[str, dict[str, str]]:
    headers = sign_in(client, "03990801")
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"]), headers


def test_an_administrator_moves_a_listing_and_its_products_to_the_other_door(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, owner = _listing(client, category, location)
    post_item(
        client,
        f"/api/businesses/{business_id}/items",
        headers=owner,
        json={"title": ar("item.generic"), "price": "2.00", "currency": "USD"},
    )

    moved = client.post(
        f"/api/admin/businesses/{business_id}/goods-origin",
        headers=admin_headers(client),
        json={"goods_origin": "IMPORTED"},
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["goods_origin"] == "IMPORTED"
    assert {item["goods_origin"] for item in moved.json()["items"]} == {"IMPORTED"}


def test_an_owner_cannot_use_the_administrators_corrections(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, owner = _listing(client, category, location)

    assert (
        client.post(
            f"/api/admin/businesses/{business_id}/goods-origin",
            headers=owner,
            json={"goods_origin": "IMPORTED"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/admin/businesses/{business_id}/images",
            headers=owner,
            files={"file": ("logo.jpg", make_image((400, 400)), "image/jpeg")},
            data={"kind": "LOGO"},
        ).status_code
        == 403
    )


def test_an_administrator_gives_a_listing_a_logo_but_not_a_gallery(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, _owner = _listing(client, category, location)
    headers = admin_headers(client)

    logo = client.post(
        f"/api/admin/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("logo.jpg", make_image((400, 400)), "image/jpeg")},
        data={"kind": "LOGO"},
    )
    assert logo.status_code == 200, logo.text
    assert logo.json()["logo_url"]

    gallery = client.post(
        f"/api/admin/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("photo.jpg", make_image((400, 400)), "image/jpeg")},
        data={"kind": "GALLERY"},
    )
    assert gallery.status_code == 422


def test_an_administrator_changes_a_shop_s_category_at_any_status(
    client: TestClient,
    admin: User,
    category: Category,
    category_other: Category,
    location: Location,
) -> None:
    """The owners' ticket: a shop filed under the wrong category. "Other"
    keeps the words it is given."""
    business_id, _ = _listing(client, category, location)

    changed = client.post(
        f"/api/admin/businesses/{business_id}/category",
        headers=admin_headers(client),
        json={
            "category_id": str(category_other.id),
            "custom_category_text": ar("business.custom_category_text"),
        },
    )

    assert changed.status_code == 200, changed.text
    assert changed.json()["category"]["id"] == str(category_other.id)
    assert changed.json()["custom_category_text"] == ar("business.custom_category_text")


def test_an_administrator_moves_a_shop_s_pin_but_not_across_the_border(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, _ = _listing(client, category, location)
    headers = admin_headers(client)
    path = f"/api/admin/businesses/{business_id}/place"

    moved = client.post(
        path,
        headers=headers,
        json={"location_id": str(location.id), "latitude": 33.5631, "longitude": 35.3709},
    )
    assert moved.status_code == 200, moved.text
    assert (moved.json()["latitude"], moved.json()["longitude"]) == (33.5631, 35.3709)

    # Kiryat Shmona: inside Lebanon's box, outside its border.
    refused = client.post(
        path,
        headers=headers,
        json={"location_id": str(location.id), "latitude": 33.207, "longitude": 35.57},
    )
    assert refused.status_code == 422, refused.text


def test_an_owner_cannot_change_category_or_place(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    business_id, owner = _listing(client, category, location)
    for action, body in (
        ("category", {"category_id": str(category.id)}),
        (
            "place",
            {"location_id": str(location.id), "latitude": 33.27, "longitude": 35.2},
        ),
    ):
        response = client.post(
            f"/api/admin/businesses/{business_id}/{action}", headers=owner, json=body
        )
        assert response.status_code == 403, action
