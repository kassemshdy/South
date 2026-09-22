"""Made in the South, or imported: one mark per business, and a filter on it.

The offering and the looking-for pages each have a door for goods made in the
South and a separate door for imported goods sold by southern stores. These
tests pin the three things that make those doors mean anything:

- the mark is set by the application and defaults to local, so every listing
  that predates the split, and every form that does not send it, stays local;
- it is public, because it is what a visitor chooses between;
- the two directories filter on it, and without the filter they show both.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus, GoodsOrigin
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar


def _approved_business(
    client: TestClient,
    db: Session,
    *,
    phone: str,
    name_key: str,
    item_key: str,
    category: Category,
    location: Location,
    origin: str | None,
) -> str:
    headers = sign_in(client, phone)
    body: dict[str, object] = {
        "name": ar(name_key),
        "short_description": ar("business.sweets_short"),
        "category_id": str(category.id),
        "location_id": str(location.id),
    }
    if origin is not None:
        body["goods_origin"] = origin
    response = client.post("/api/businesses", headers=headers, json=body)
    assert response.status_code == 201, response.text
    business = response.json()
    client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar(item_key), "price": "1.00", "currency": "USD"},
    )
    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return str(business["id"])


@pytest.fixture
def one_of_each(client: TestClient, db: Session, category: Category, location: Location) -> None:
    _approved_business(
        client,
        db,
        phone="03980001",
        name_key="business.manakish",
        item_key="item.zaatar_local",
        category=category,
        location=location,
        origin=None,
    )
    _approved_business(
        client,
        db,
        phone="03980002",
        name_key="business.sweets_shop",
        item_key="item.generic",
        category=category,
        location=location,
        origin="IMPORTED",
    )


def test_a_business_is_local_unless_it_says_otherwise(
    client: TestClient, db: Session, one_of_each: None
) -> None:
    origins = {
        business.name: business.goods_origin for business in db.execute(select(Business)).scalars()
    }
    assert origins == {
        ar("business.manakish"): GoodsOrigin.LOCAL,
        ar("business.sweets_shop"): GoodsOrigin.IMPORTED,
    }


def test_the_mark_is_public(client: TestClient, one_of_each: None) -> None:
    listed = client.get("/api/businesses").json()["items"]
    assert {b["name"]: b["goods_origin"] for b in listed} == {
        ar("business.manakish"): "LOCAL",
        ar("business.sweets_shop"): "IMPORTED",
    }


def test_the_businesses_directory_filters_on_it(client: TestClient, one_of_each: None) -> None:
    def names(query: str) -> set[str]:
        return {b["name"] for b in client.get(f"/api/businesses{query}").json()["items"]}

    assert names("") == {ar("business.manakish"), ar("business.sweets_shop")}
    assert names("?origin=LOCAL") == {ar("business.manakish")}
    assert names("?origin=IMPORTED") == {ar("business.sweets_shop")}


def test_the_products_directory_filters_on_its_business(
    client: TestClient, one_of_each: None
) -> None:
    def titles(query: str) -> set[str]:
        return {i["title"] for i in client.get(f"/api/items{query}").json()["items"]}

    assert titles("") == {ar("item.zaatar_local"), ar("item.generic")}
    assert titles("?origin=LOCAL") == {ar("item.zaatar_local")}
    assert titles("?origin=IMPORTED") == {ar("item.generic")}


def test_an_unknown_origin_is_refused_rather_than_ignored(client: TestClient) -> None:
    # Ignoring it would show everything under a door that promised a subset.
    assert client.get("/api/items?origin=ELSEWHERE").status_code == 422
    assert client.get("/api/businesses?origin=ELSEWHERE").status_code == 422


def test_the_owner_can_change_it_but_not_clear_it(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03980003")
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={"name": ar("business.manakish"), "category_id": str(category.id)},
    ).json()

    changed = client.put(
        f"/api/businesses/{business['id']}",
        headers=headers,
        json={"goods_origin": "IMPORTED"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["goods_origin"] == "IMPORTED"

    cleared = client.put(
        f"/api/businesses/{business['id']}",
        headers=headers,
        json={"goods_origin": None},
    )
    assert cleared.status_code == 422

    # Another field saved alone leaves the mark where it was.
    client.put(
        f"/api/businesses/{business['id']}",
        headers=headers,
        json={"short_description": ar("business.sweets_short")},
    )
    record = db.get(Business, business["id"])
    assert record is not None
    db.refresh(record)
    assert record.goods_origin is GoodsOrigin.IMPORTED


def test_the_public_application_carries_it(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    payload = {
        "login_phone": "03980004",
        "identity": {
            "full_name": ar("identity.full_name"),
            "birth_year": 1986,
            "registration_place": ar("identity.registration_place"),
            "residence_place": ar("identity.residence_place"),
        },
        "business": {
            "name": ar("business.applicant"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "goods_origin": "IMPORTED",
        },
    }
    response = client.post("/api/register/business", data={"application": json.dumps(payload)})
    assert response.status_code == 202, response.text

    business = db.execute(select(Business)).scalar_one()
    assert business.goods_origin is GoodsOrigin.IMPORTED
    assert business.status is BusinessStatus.PENDING_REVIEW
