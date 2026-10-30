"""Newest first, everywhere a list has a default order (the owners'
decision, 30 Oct 2026). The directory lists every product; only the home
rows ask for one per shop, and get it only once more than six shops have a
product to show.
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


def test_newest_products_list_every_product_newest_first(
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
    assert newest["meta"]["total"] == 6
    assert [item["title"] for item in newest["items"][:2]] == [
        quiet_titles[-1],
        busy_titles[-1],
    ]

    # And the shop's own page still shows all of its products.
    shop = client.get(f"/api/businesses/{busy}").json()
    assert len(shop["items"]) == 5


def test_home_rows_show_one_per_shop_only_once_more_than_six_shops_have_products(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _shop(
        client,
        db,
        phone="03960010",
        name_key="business.manakish",
        products=5,
        category=category,
        location=location,
    )
    home_row = {"one_per_shop": "true"}

    # One shop alone: too few to spread out, so the row lists every product.
    assert client.get("/api/items", params=home_row).json()["meta"]["total"] == 5

    for index in range(6):
        _shop(
            client,
            db,
            phone=f"0396002{index}",
            name_key="business.sweets_shop",
            products=1,
            category=category,
            location=location,
        )

    # Seven shops: the home row takes each one's newest product...
    assert client.get("/api/items", params=home_row).json()["meta"]["total"] == 7
    # ...while the directory, which never asks, still lists all of them.
    assert client.get("/api/items").json()["meta"]["total"] == 11


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
    # An application from the public form: pending from creation, with no
    # submitted_at. It is the newest, so it must head the queue.
    applied, _ = _shop(
        client,
        db,
        phone="03960005",
        name_key="business.manakish",
        products=0,
        category=category,
        location=location,
    )
    now = datetime.now(UTC)
    for slug, submitted in (
        (older, now - timedelta(days=2)),
        (newer, now - timedelta(hours=1)),
        (applied, None),
    ):
        record = db.query(Business).filter(Business.slug == slug).one()
        record.status = BusinessStatus.PENDING_REVIEW
        record.submitted_at = submitted
    db.commit()

    queue = client.get("/api/admin/businesses/pending", headers=admin_headers(client)).json()
    assert [row["slug"] for row in queue["items"]] == [applied, newer, older]
