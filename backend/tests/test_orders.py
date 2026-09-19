"""Order requests (#39).

Not e-commerce: no payment, no stock, no shipping. What is asserted here is
what the feature actually promises, plus the three ways it could quietly
betray somebody:

- an order must not be able to name **another shop's** product, or one a
  visitor cannot see;
- the line items must be **snapshots**, so a later price change or a deleted
  product cannot rewrite what a customer asked for;
- the customer's name and phone must reach **the owner and nobody else** --
  no public read, no administrator read.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, OrderStatus
from app.models.order import Order
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import sign_in
from tests.samples import ar

OWNER_PHONE = "03990001"
OTHER_PHONE = "03990002"
CUSTOMER_PHONE = "03990100"


def _make_business(
    client: TestClient,
    db: Session,
    headers: dict[str, str],
    category: Category,
    location: Location,
    *,
    name: str,
) -> Business:
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": name,
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    entity = db.get(Business, created.json()["id"])
    assert entity is not None
    entity.status = BusinessStatus.APPROVED
    db.commit()
    db.refresh(entity)
    return entity


def _add_item(
    client: TestClient,
    business: Business,
    headers: dict[str, str],
    *,
    title: str,
    price: str = "5.00",
    available: bool = True,
) -> str:
    created = client.post(
        f"/api/businesses/{business.id}/items",
        headers=headers,
        json={
            "title": title,
            "price": price,
            "currency": "USD",
            "is_available": available,
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


@pytest.fixture
def owner_headers(client: TestClient) -> dict[str, str]:
    return sign_in(client, OWNER_PHONE)


@pytest.fixture
def shop(
    client: TestClient,
    db: Session,
    owner_headers: dict[str, str],
    category: Category,
    location: Location,
) -> Business:
    return _make_business(
        client, db, owner_headers, category, location, name=ar("business.sweets_shop")
    )


def _place(client: TestClient, slug: str, lines: list[dict[str, object]], **extra):
    payload = {
        "customer_name": ar("order.customer"),
        "customer_phone": CUSTOMER_PHONE,
        "lines": lines,
    }
    payload.update(extra)
    return client.post(f"/api/businesses/{slug}/orders", json=payload)


# --- The happy path, and what the owner receives ---------------------------


def test_a_visitor_places_an_order_and_the_owner_sees_it(
    client: TestClient, db: Session, shop: Business, owner_headers: dict[str, str]
) -> None:
    item_id = _add_item(client, shop, owner_headers, title=ar("item.zaatar"), price="3.50")

    placed = _place(
        client,
        shop.slug,
        [{"item_id": item_id, "quantity": 2}],
        note=ar("order.note"),
    )
    assert placed.status_code == 201, placed.text

    orders = client.get(f"/api/businesses/{shop.id}/orders", headers=owner_headers).json()

    assert len(orders) == 1
    order = orders[0]
    assert order["status"] == "NEW"
    assert order["customer_name"] == ar("order.customer")
    assert order["note"] == ar("order.note")
    assert order["lines"] == [
        {"title": ar("item.zaatar"), "price": "3.50", "currency": "USD", "quantity": 2}
    ]


def test_ordering_needs_no_account(
    client: TestClient, shop: Business, owner_headers: dict[str, str]
) -> None:
    """Decided on the issue: a junk order costs the owner one message, while
    a sign-in would sit between a real customer and the one action this
    feature exists to produce."""
    item_id = _add_item(client, shop, owner_headers, title=ar("item.generic"))

    assert _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}]).status_code == 201


def test_the_owner_moves_an_order_along(
    client: TestClient, db: Session, shop: Business, owner_headers: dict[str, str]
) -> None:
    item_id = _add_item(client, shop, owner_headers, title=ar("item.generic"))
    _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}])
    order_id = client.get(
        f"/api/businesses/{shop.id}/orders", headers=owner_headers
    ).json()[0]["id"]

    moved = client.post(
        f"/api/businesses/{shop.id}/orders/{order_id}/status",
        headers=owner_headers,
        json={"status": "CONTACTED"},
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "CONTACTED"
    assert db.get(Order, uuid.UUID(order_id)).status is OrderStatus.CONTACTED


# --- What an order may not name --------------------------------------------


def test_an_order_cannot_name_another_shops_product(
    client: TestClient,
    db: Session,
    shop: Business,
    owner_headers: dict[str, str],
    category: Category,
    location: Location,
) -> None:
    """The whole order is rejected rather than the stray line dropped.

    Silently discarding it would have the owner reply about something the
    customer never asked for, or miss something they did.
    """
    stranger = sign_in(client, OTHER_PHONE)
    other = _make_business(
        client, db, stranger, category, location, name=ar("business.other_shop")
    )
    theirs = _add_item(client, other, stranger, title=ar("item.zaatar_local"))
    mine = _add_item(client, shop, owner_headers, title=ar("item.generic"))

    response = _place(
        client,
        shop.slug,
        [{"item_id": mine, "quantity": 1}, {"item_id": theirs, "quantity": 1}],
    )

    assert response.status_code == 422
    assert client.get(f"/api/businesses/{shop.id}/orders", headers=owner_headers).json() == []


def test_an_order_cannot_name_an_unavailable_product(
    client: TestClient, shop: Business, owner_headers: dict[str, str]
) -> None:
    """`public_by_ids` is built on `public_query`, so "what a visitor may
    order" and "what a visitor may see" cannot drift apart."""
    hidden = _add_item(
        client, shop, owner_headers, title=ar("item.generic"), available=False
    )

    assert _place(client, shop.slug, [{"item_id": hidden, "quantity": 1}]).status_code == 422


def test_an_order_cannot_be_placed_on_a_listing_a_visitor_cannot_see(
    client: TestClient, db: Session, shop: Business, owner_headers: dict[str, str]
) -> None:
    item_id = _add_item(client, shop, owner_headers, title=ar("item.generic"))
    shop.status = BusinessStatus.SUSPENDED
    db.commit()

    assert _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}]).status_code == 404


def test_an_order_must_have_at_least_one_line(
    client: TestClient, shop: Business
) -> None:
    assert _place(client, shop.slug, []).status_code == 422


# --- Snapshots -------------------------------------------------------------


def test_a_later_price_change_does_not_rewrite_the_order(
    client: TestClient, db: Session, shop: Business, owner_headers: dict[str, str]
) -> None:
    """What the customer asked for is a fact about the past."""
    item_id = _add_item(client, shop, owner_headers, title=ar("item.zaatar"), price="3.50")
    _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}])

    client.put(
        f"/api/businesses/{shop.id}/items/{item_id}",
        headers=owner_headers,
        json={"price": "9.99"},
    )

    order = client.get(f"/api/businesses/{shop.id}/orders", headers=owner_headers).json()[0]
    assert order["lines"][0]["price"] == "3.50"
    assert db.get(BusinessItem, uuid.UUID(item_id)).price == Decimal("9.99")


def test_deleting_the_product_keeps_the_order_and_its_line(
    client: TestClient, db: Session, shop: Business, owner_headers: dict[str, str]
) -> None:
    """ON DELETE SET NULL, not CASCADE: removing a product must not delete
    the record that somebody once asked for it."""
    item_id = _add_item(client, shop, owner_headers, title=ar("item.zaatar"), price="3.50")
    _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}])

    deleted = client.delete(
        f"/api/businesses/{shop.id}/items/{item_id}", headers=owner_headers
    )
    assert deleted.status_code == 200, deleted.text

    order = client.get(f"/api/businesses/{shop.id}/orders", headers=owner_headers).json()[0]
    assert order["lines"] == [
        {"title": ar("item.zaatar"), "price": "3.50", "currency": "USD", "quantity": 1}
    ]


# --- Who may read one ------------------------------------------------------


def test_an_order_is_never_on_the_public_profile(
    client: TestClient, shop: Business, owner_headers: dict[str, str]
) -> None:
    """A customer's name and phone must not be published by a payload that
    grew a field. Asserted against the whole body, not one key."""
    item_id = _add_item(client, shop, owner_headers, title=ar("item.generic"))
    _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}])

    body = client.get(f"/api/businesses/{shop.slug}").text

    assert CUSTOMER_PHONE not in body
    assert ar("order.customer") not in body
    assert "orders" not in client.get(f"/api/businesses/{shop.slug}").json()


def test_another_owner_cannot_read_or_move_an_order(
    client: TestClient, db: Session, shop: Business, owner_headers: dict[str, str]
) -> None:
    item_id = _add_item(client, shop, owner_headers, title=ar("item.generic"))
    _place(client, shop.slug, [{"item_id": item_id, "quantity": 1}])
    order_id = client.get(
        f"/api/businesses/{shop.id}/orders", headers=owner_headers
    ).json()[0]["id"]

    stranger = sign_in(client, OTHER_PHONE)

    assert client.get(f"/api/businesses/{shop.id}/orders", headers=stranger).status_code == 404
    assert (
        client.post(
            f"/api/businesses/{shop.id}/orders/{order_id}/status",
            headers=stranger,
            json={"status": "DONE"},
        ).status_code
        == 404
    )


def test_no_admin_route_exposes_an_order(client: TestClient, admin: User) -> None:
    """Decided on the issue: moderation needs neither a customer's name nor
    their phone number, so no administrator payload carries an order. This
    asserts the absence, so adding such a route is a deliberate act.
    """
    from app.main import create_app

    paths = [
        route.path  # type: ignore[attr-defined]
        for route in create_app().routes
        if "/admin" in getattr(route, "path", "")
    ]

    assert not [path for path in paths if "order" in path]


# --- Rate limiting ---------------------------------------------------------


def test_one_listing_cannot_be_flooded_from_many_addresses(
    client: TestClient, shop: Business, owner_headers: dict[str, str]
) -> None:
    """The per-listing rule. Each request comes from a fresh address, so the
    per-address rule never binds -- if they were one rule this would stop at
    ten."""
    item_id = _add_item(client, shop, owner_headers, title=ar("item.generic"))
    limit = 40

    for index in range(limit):
        response = client.post(
            f"/api/businesses/{shop.slug}/orders",
            headers={"X-Forwarded-For": f"203.0.113.{index}"},
            json={
                "customer_name": ar("order.customer"),
                "customer_phone": CUSTOMER_PHONE,
                "lines": [{"item_id": item_id, "quantity": 1}],
            },
        )
        assert response.status_code == 201, f"order {index} should not be limited"

    blocked = client.post(
        f"/api/businesses/{shop.slug}/orders",
        headers={"X-Forwarded-For": "198.51.100.9"},
        json={
            "customer_name": ar("order.customer"),
            "customer_phone": CUSTOMER_PHONE,
            "lines": [{"item_id": item_id, "quantity": 1}],
        },
    )

    assert blocked.status_code == 429
    assert blocked.json()["error"]["details"]["retry_after_seconds"] > 0
