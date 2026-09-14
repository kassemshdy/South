"""Product profile fields and gallery (ticket 25d9a495).

A physical good gets a few fields a service or menu item never needs --
brand, ingredients, manufacture/expiry dates, net weight, an external link --
plus a gallery separate from its card thumbnail. All of it is public: unlike
an account holder's identity, nothing here describes a person, so it belongs
on ``ProductDetailOut`` rather than an owner-only schema.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar


def make_image(size: tuple[int, int] = (400, 400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (80, 140, 90)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def business_with_item(
    client: TestClient, db: Session, category: Category, location: Location
) -> tuple[str, str, dict[str, str]]:
    """An approved business with one available item, ready to carry product detail."""
    headers = sign_in(client, "03970001")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.sweets_shop"),
            "short_description": ar("business.sweets_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03970001",
        },
    ).json()
    item = client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={
            "title": ar("item.zaatar_local"),
            "price": "1.50",
            "currency": "USD",
            "good_type": ar("product.good_type"),
            "brand_name": ar("product.brand_name"),
            "ingredients": ar("product.ingredients"),
            "manufactured_at": "2026-01-10",
            "expiry_date": "2026-12-31",
            "net_weight": ar("product.net_weight"),
            "external_link": "https://example.com/zaatar",
        },
    ).json()

    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return business["id"], item["id"], headers


def test_product_fields_reach_the_owner(
    client: TestClient, business_with_item: tuple[str, str, dict[str, str]]
) -> None:
    business_id, item_id, headers = business_with_item
    listed = client.get(f"/api/businesses/{business_id}/items", headers=headers).json()
    item = next(i for i in listed if i["id"] == item_id)

    assert item["good_type"] == ar("product.good_type")
    assert item["brand_name"] == ar("product.brand_name")
    assert item["ingredients"] == ar("product.ingredients")
    assert item["manufactured_at"] == "2026-01-10"
    assert item["expiry_date"] == "2026-12-31"
    assert item["net_weight"] == ar("product.net_weight")
    assert item["external_link"] == "https://example.com/zaatar"
    assert item["images"] == []


def test_product_fields_reach_an_anonymous_reader(
    client: TestClient, db: Session, business_with_item: tuple[str, str, dict[str, str]]
) -> None:
    from app.models.business import BusinessItem

    business_id, item_id, _ = business_with_item
    slug = db.get(BusinessItem, item_id).slug  # type: ignore[union-attr]

    detail = client.get(f"/api/items/{slug}").json()

    assert detail["good_type"] == ar("product.good_type")
    assert detail["brand_name"] == ar("product.brand_name")
    assert detail["ingredients"] == ar("product.ingredients")
    assert detail["manufactured_at"] == "2026-01-10"
    assert detail["expiry_date"] == "2026-12-31"
    assert detail["net_weight"] == ar("product.net_weight")
    assert detail["external_link"] == "https://example.com/zaatar"


def test_fields_are_optional(client: TestClient, category: Category, location: Location) -> None:
    headers = sign_in(client, "03970002")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()
    response = client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic")},
    )
    assert response.status_code == 201
    item = response.json()
    assert item["good_type"] is None
    assert item["brand_name"] is None
    assert item["images"] == []


def test_gallery_upload_list_and_order(
    client: TestClient, business_with_item: tuple[str, str, dict[str, str]]
) -> None:
    business_id, item_id, headers = business_with_item

    first = client.post(
        f"/api/businesses/{business_id}/items/{item_id}/gallery",
        headers=headers,
        files={"file": ("a.jpg", make_image(), "image/jpeg")},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/businesses/{business_id}/items/{item_id}/gallery",
        headers=headers,
        files={"file": ("b.jpg", make_image(), "image/jpeg")},
        data={"caption": ar("item.generic")},
    )
    assert second.status_code == 201
    images = second.json()["images"]
    assert len(images) == 2
    assert images[1]["caption"] == ar("item.generic")

    reordered = client.put(
        f"/api/businesses/{business_id}/items/{item_id}/gallery/order",
        headers=headers,
        json={"image_ids": [images[1]["id"], images[0]["id"]]},
    ).json()
    assert [image["id"] for image in reordered["images"]] == [images[1]["id"], images[0]["id"]]


def test_gallery_delete_removes_only_that_image(
    client: TestClient, business_with_item: tuple[str, str, dict[str, str]]
) -> None:
    business_id, item_id, headers = business_with_item
    uploaded = [
        client.post(
            f"/api/businesses/{business_id}/items/{item_id}/gallery",
            headers=headers,
            files={"file": (f"{i}.jpg", make_image(), "image/jpeg")},
        ).json()
        for i in range(2)
    ]
    keep_id = uploaded[-1]["images"][0]["id"]
    remove_id = uploaded[-1]["images"][1]["id"]

    result = client.delete(
        f"/api/businesses/{business_id}/items/{item_id}/gallery/{remove_id}",
        headers=headers,
    ).json()
    assert [image["id"] for image in result["images"]] == [keep_id]


def test_gallery_reaches_the_public_product_page(
    client: TestClient, db: Session, business_with_item: tuple[str, str, dict[str, str]]
) -> None:
    from app.models.business import BusinessItem

    business_id, item_id, headers = business_with_item
    client.post(
        f"/api/businesses/{business_id}/items/{item_id}/gallery",
        headers=headers,
        files={"file": ("a.jpg", make_image(), "image/jpeg")},
    )
    slug = db.get(BusinessItem, item_id).slug  # type: ignore[union-attr]

    detail = client.get(f"/api/items/{slug}").json()
    assert len(detail["images"]) == 1


def test_a_stranger_cannot_reach_another_owners_item_gallery(
    client: TestClient, business_with_item: tuple[str, str, dict[str, str]]
) -> None:
    business_id, item_id, _ = business_with_item
    stranger_headers = sign_in(client, "03970003")

    response = client.post(
        f"/api/businesses/{business_id}/items/{item_id}/gallery",
        headers=stranger_headers,
        files={"file": ("a.jpg", make_image(), "image/jpeg")},
    )
    assert response.status_code == 404
