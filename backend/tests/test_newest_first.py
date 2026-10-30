"""Newest first, everywhere a list has a default order (the owners'
decision, 30 Oct 2026) -- and one product per shop on the newest products
listing, so a shop that adds many products at once does not fill the page
and the home rows on its own.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, post_item, sign_in
from tests.samples import ar


def _shop(
    client: TestClient,
    db: Session,
    *,
    phone: str,
    name_key: str,
    products: int,
    category: Category,
    location: Location,
) -> tuple[str, list[str]]:
    headers = sign_in(client, phone)
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar(name_key),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    business = created.json()
    titles = []
    for index in range(products):
        title = f"{ar('item.zaatar_local')} {phone} {index}"
        post_item(
            client,
            f"/api/businesses/{business['id']}/items",
            headers=headers,
            json={"title": title, "price": f"{index + 1}.00", "currency": "USD"},
        )
        titles.append(title)
    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return str(business["slug"]), titles


def test_newest_products_show_one_per_shop_but_other_orders_show_all(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    busy, busy_titles = _shop(
        client,
        db,
        phone="03960001",
        name_key="business.manakish",
        products=5,
        category=category,
        location=location,
    )
    quiet, quiet_titles = _shop(
        client,
        db,
        phone="03960002",
        name_key="business.sweets_shop",
        products=1,
        category=category,
        location=location,
    )

    newest = client.get("/api/items").json()
    assert newest["meta"]["total"] == 2
    assert [item["business"]["slug"] for item in newest["items"]] == [quiet, busy]
    assert [item["title"] for item in newest["items"]] == [quiet_titles[-1], busy_titles[-1]]

    # A filter that is not a search still gets one per shop...
    in_category = client.get("/api/items", params={"category": category.slug}).json()
    assert in_category["meta"]["total"] == 2

    # ...while any other order, or a text search, lists every product.
    by_price = client.get("/api/items", params={"sort": "price_asc"}).json()
    assert by_price["meta"]["total"] == 6
    searched = client.get("/api/items", params={"q": ar("item.zaatar_local")}).json()
    assert searched["meta"]["total"] == 6

    # And the shop's own page still shows all of its products.
    shop = client.get(f"/api/businesses/{busy}").json()
    assert len(shop["items"]) == 5


def test_review_queue_lists_the_newest_submission_first(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    older, _ = _shop(
        client,
        db,
        phone="03960003",
        name_key="business.manakish",
        products=0,
        category=category,
        location=location,
    )
    newer, _ = _shop(
        client,
        db,
        phone="03960004",
        name_key="business.sweets_shop",
        products=0,
        category=category,
        location=location,
    )
    now = datetime.now(UTC)
    for slug, submitted in ((older, now - timedelta(days=2)), (newer, now - timedelta(hours=1))):
        record = db.query(Business).filter(Business.slug == slug).one()
        record.status = BusinessStatus.PENDING_REVIEW
        record.submitted_at = submitted
    db.commit()

    queue = client.get("/api/admin/businesses/pending", headers=admin_headers(client)).json()
    assert [row["slug"] for row in queue["items"]] == [newer, older]
