"""The admin growth report: the value equation, read off the live data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analytics import ListingViewDaily
from app.models.business import Business
from app.models.enums import BusinessStatus, Currency, OrderStatus, ViewSubject
from app.models.order import Order, OrderLine
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.schemas.growth_report import GrowthReportOut, SellerHealth, WeeklySeries
from app.services.growth_report import recommend
from tests.conftest import admin_headers, sign_in
from tests.samples import ar
from tests.test_permissions import _invite

CUSTOMER_PHONE = "+96170111222"


def _shop(
    client: TestClient, db: Session, category: Category, location: Location, phone: str, name: str
) -> Business:
    created = client.post(
        "/api/businesses",
        headers=sign_in(client, phone),
        json={
            "name": name,
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    shop = db.get(Business, created.json()["id"])
    assert shop is not None
    shop.status = BusinessStatus.APPROVED
    shop.approved_at = shop.created_at + timedelta(hours=6)
    db.commit()
    return shop


def test_the_report_sorts_every_approved_shop_by_what_it_got(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    selling = _shop(client, db, category, location, "03880801", ar("business.first"))
    looked_at = _shop(client, db, category, location, "03880802", ar("business.second"))
    _shop(client, db, category, location, "03880803", ar("business.other_shop"))
    db.add(
        Order(
            business_id=selling.id,
            customer_name=ar("order.customer"),
            customer_phone=CUSTOMER_PHONE,
            status=OrderStatus.NEW,
        )
    )
    db.add(
        ListingViewDaily(
            subject_type=ViewSubject.BUSINESS,
            subject_id=looked_at.id,
            day=datetime.now(UTC).date(),
            views=7,
        )
    )
    db.commit()

    response = client.get("/api/admin/growth-report", headers=admin_headers(client))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["approved_shops"] == 3
    assert body["health"] == {"with_orders": 1, "viewed_no_orders": 1, "unseen": 1}
    assert body["shops_with_order_7d"] == 1 and body["orders_7d"] == 1
    assert body["weekly"]["orders"][-1] == 1 and len(body["weekly"]["orders"]) == 8
    assert body["views_30d"] == 7 and body["orders_per_1000_views"] == 142.9
    assert body["median_approval_hours"] == 6.0
    assert [shop["slug"] for shop in body["top_shops"]] == [selling.slug]
    assert [shop["name"] for shop in body["quiet_shops"]] == [ar("business.other_shop")]
    keys = [rec["key"] for rec in body["recommendations"]]
    assert "unseenShops" in keys and "viewsNoOrders" in keys
    assert "proof" not in keys, "one shop in three with an order is above the bar"


def test_the_report_carries_no_customer_or_owner_details(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    shop = _shop(client, db, category, location, "03880804", ar("business.first"))
    db.add(
        Order(
            business_id=shop.id,
            customer_name=ar("order.customer"),
            customer_phone=CUSTOMER_PHONE,
            status=OrderStatus.NEW,
        )
    )
    db.commit()

    text = client.get("/api/admin/growth-report", headers=admin_headers(client)).text

    assert CUSTOMER_PHONE not in text
    assert ar("order.customer") not in text
    assert "03880804" not in text and "880804" not in text


def test_every_staff_role_reads_it_and_nobody_else(client: TestClient, admin: User) -> None:
    assert client.get("/api/admin/growth-report").status_code == 401
    owner = sign_in(client, "03880805")
    assert client.get("/api/admin/growth-report", headers=owner).status_code == 403
    viewer = _invite(client, admin_headers(client), "VIEWER", "viewer@example.com")
    assert client.get("/api/admin/growth-report", headers=viewer).status_code == 200


def _report(**changes: object) -> GrowthReportOut:
    base: dict[str, object] = {
        "generated_at": datetime.now(UTC),
        "week_starts": [date(2026, 1, 1)] * 2,
        "approved_shops": 10,
        "approved_talents": 0,
        "public_products": 50,
        "pending_reviews": 0,
        "pending_over_48h": 0,
        "shops_with_order_7d": 5,
        "shops_with_order_30d": 5,
        "orders_7d": 5,
        "orders_30d": 9,
        "service_requests_30d": 0,
        "views_30d": 100,
        "orders_per_1000_views": 90.0,
        "median_approval_hours": 10.0,
        "approved_testimonials": 20,
        "goal_usd": 100_000_000,
        "order_value_usd": 0.0,
        "order_value_usd_30d": 0.0,
        "order_value_lbp": 0.0,
        "thin_catalogue_shops": 0,
        "shops_without_logo": 0,
        "weekly": WeeklySeries(
            orders=[4, 5], service_requests=[0, 0], views=[50, 50],
            new_sellers=[1, 1], new_products=[3, 3],
        ),
        "health": SellerHealth(with_orders=10, viewed_no_orders=0, unseen=0),
        "top_shops": [],
        "quiet_shops": [],
        "recommendations": [],
    }
    base.update(changes)
    return GrowthReportOut.model_validate(base)


def test_a_healthy_platform_is_told_to_keep_going() -> None:
    assert [rec.key for rec in recommend(_report())] == ["keepGoing"]


def test_the_most_urgent_steps_come_first() -> None:
    report = _report(
        shops_without_logo=2,
        pending_over_48h=3,
        median_approval_hours=60.0,
        weekly=WeeklySeries(
            orders=[6, 2], service_requests=[0, 0], views=[50, 50],
            new_sellers=[1, 1], new_products=[3, 3],
        ),
    )
    steps = recommend(report)
    assert [rec.key for rec in steps] == [
        "ordersDown", "reviewBacklog", "slowApproval", "missingLogo",
    ]
    assert steps[0].count == 4 and steps[1].lever == "time"


def test_progress_to_the_goal_counts_what_orders_asked_for_by_currency(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    shop = _shop(client, db, category, location, "03880806", ar("business.first"))
    order = Order(
        business_id=shop.id,
        customer_name=ar("order.customer"),
        customer_phone=CUSTOMER_PHONE,
        status=OrderStatus.NEW,
    )
    order.lines = [
        OrderLine(title=ar("business.first"), price=Decimal("12.50"), currency=Currency.USD, quantity=2),
        OrderLine(title=ar("business.first"), price=Decimal("90000"), currency=Currency.LBP, quantity=1),
        OrderLine(title=ar("business.first"), price=None, currency=Currency.USD, quantity=3),
    ]
    db.add(order)
    db.commit()

    body = client.get("/api/admin/growth-report", headers=admin_headers(client)).json()

    assert body["goal_usd"] == 100_000_000
    assert body["order_value_usd"] == 25.0 and body["order_value_usd_30d"] == 25.0
    assert body["order_value_lbp"] == 90000.0, "pounds are kept apart, never converted"


def test_the_manager_sets_the_goal_and_the_offer_and_other_staff_only_read_them(
    client: TestClient, admin: User
) -> None:
    manager = admin_headers(client)
    assert client.get("/api/admin/growth-plan", headers=manager).json() == {
        "goal_usd": 100_000_000,
        "offer": None,
    }

    saved = client.put(
        "/api/admin/growth-plan",
        headers=manager,
        json={"goal_usd": 5_000_000, "offer": f"  {ar('business.generic_short')}  "},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"goal_usd": 5_000_000, "offer": ar("business.generic_short")}
    report = client.get("/api/admin/growth-report", headers=manager).json()
    assert report["goal_usd"] == 5_000_000

    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")
    assert client.get("/api/admin/growth-plan", headers=reviewer).status_code == 200
    refused = client.put(
        "/api/admin/growth-plan", headers=reviewer, json={"goal_usd": 1, "offer": None}
    )
    assert refused.status_code == 403

    reset = client.put(
        "/api/admin/growth-plan", headers=manager, json={"goal_usd": 100_000_000, "offer": " "}
    )
    assert reset.json() == {"goal_usd": 100_000_000, "offer": None}
