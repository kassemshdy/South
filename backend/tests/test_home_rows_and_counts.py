"""The home page's top-rated and most-viewed product rows, and the counts the
directories' filters list and sort by."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analytics import ListingViewDaily
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, TalentKind, ViewSubject
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from tests.conftest import make_owner, post_item, sign_in
from tests.samples import ar


def _shop_with_item(
    client: TestClient,
    db: Session,
    category: Category,
    location: Location,
    phone: str,
    name: str,
    title: str,
) -> tuple[Business, BusinessItem]:
    headers = sign_in(client, phone)
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": name,
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    business_id = created.json()["id"]
    post_item(
        client,
        f"/api/businesses/{business_id}/items",
        headers=headers,
        json={"title": title, "price": "3.00", "currency": "USD"},
    )
    shop = db.get(Business, business_id)
    assert shop is not None
    shop.status = BusinessStatus.APPROVED
    db.commit()
    item = db.execute(
        select(BusinessItem).where(BusinessItem.business_id == shop.id)
    ).scalar_one()
    return shop, item


def test_top_rated_lists_only_rated_shops_best_first(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    good, good_item = _shop_with_item(
        client, db, category, location, "03770701", ar("business.first"), ar("item.zaatar_local")
    )
    better, better_item = _shop_with_item(
        client, db, category, location, "03770702", ar("business.second"), ar("item.generic")
    )
    _shop_with_item(
        client, db, category, location, "03770703", ar("business.other_shop"), ar("item.generic")
    )
    good.rating_average, good.rating_count = Decimal("4.20"), 5
    better.rating_average, better.rating_count = Decimal("4.80"), 2
    db.commit()

    rows = client.get("/api/items/top-rated").json()

    assert [row["slug"] for row in rows] == [better_item.slug, good_item.slug]


def test_top_viewed_orders_products_by_views_in_the_last_30_days(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _, quiet = _shop_with_item(
        client, db, category, location, "03770704", ar("business.first"), ar("item.zaatar_local")
    )
    _, busy = _shop_with_item(
        client, db, category, location, "03770705", ar("business.second"), ar("item.generic")
    )
    _, old_news = _shop_with_item(
        client, db, category, location, "03770706", ar("business.other_shop"), ar("item.generic")
    )
    today = datetime.now(UTC).date()
    db.add_all(
        [
            ListingViewDaily(
                subject_type=ViewSubject.PRODUCT, subject_id=quiet.id, day=today, views=2
            ),
            ListingViewDaily(
                subject_type=ViewSubject.PRODUCT, subject_id=busy.id, day=today, views=9
            ),
            # Popular once, but outside the window.
            ListingViewDaily(
                subject_type=ViewSubject.PRODUCT,
                subject_id=old_news.id,
                day=today - timedelta(days=45),
                views=99,
            ),
        ]
    )
    db.commit()

    rows = client.get("/api/items/top-viewed").json()

    assert [row["slug"] for row in rows] == [busy.slug, quiet.slug]


def test_locations_and_skills_count_each_directory_separately(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _shop_with_item(
        client, db, category, location, "03770707", ar("business.first"), ar("item.generic")
    )
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.flush()
    db.add(
        TalentProfile(
            owner_id=make_owner("03770708").id,
            kind=TalentKind.SERVICE,
            display_name=ar("business.second"),
            slug="counted-service",
            skill_id=skill.id,
            location_id=location.id,
            status=BusinessStatus.APPROVED,
        )
    )
    db.commit()

    place = next(
        row for row in client.get("/api/locations").json() if row["id"] == str(location.id)
    )
    assert place["business_count"] == 1
    assert place["item_count"] == 1
    assert place["service_count"] == 1
    assert place["job_count"] == 0

    counted = next(
        row for row in client.get("/api/talent-skills").json() if row["id"] == str(skill.id)
    )
    assert counted["talent_count"] == 1
    assert counted["service_count"] == 1 and counted["job_count"] == 0
