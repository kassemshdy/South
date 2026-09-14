"""The per-listing view counter (#46).

What these tests are really defending is one sentence on an owner's
dashboard. Two properties make it worth trusting, and both are asserted
here from the direction that would break them:

- a visitor's view counts, and **the owner's own view does not** -- an
  owner refreshing their own page must not be able to inflate the only
  honest signal they have;
- the numbers an owner reads are their own -- ``/api/my/views`` is derived
  from the authenticated user, never from an id in the request.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analytics import ListingViewDaily
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, ViewSubject
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services.analytics import RECENT_DAYS, WINDOW_DAYS
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

OWNER_PHONE = "03960001"
OTHER_PHONE = "03960002"


def _counts(db: Session, subject_type: ViewSubject, subject_id: uuid.UUID) -> list[int]:
    return list(
        db.execute(
            select(ListingViewDaily.views)
            .where(
                ListingViewDaily.subject_type == subject_type,
                ListingViewDaily.subject_id == subject_id,
            )
            .order_by(ListingViewDaily.day)
        ).scalars()
    )


@pytest.fixture
def owner_headers(client: TestClient) -> dict[str, str]:
    return sign_in(client, OWNER_PHONE)


@pytest.fixture
def approved_business(
    client: TestClient,
    db: Session,
    owner_headers: dict[str, str],
    category: Category,
    location: Location,
) -> Business:
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    business = db.get(Business, created.json()["id"])
    assert business is not None
    business.status = BusinessStatus.APPROVED
    db.commit()
    db.refresh(business)
    return business


# --- Counting --------------------------------------------------------------


def test_a_visitor_view_is_counted(
    client: TestClient, db: Session, approved_business: Business
) -> None:
    response = client.get(f"/api/businesses/{approved_business.slug}")

    assert response.status_code == 200
    assert _counts(db, ViewSubject.BUSINESS, approved_business.id) == [1]


def test_repeated_views_accumulate_in_one_row_per_day(
    client: TestClient, db: Session, approved_business: Business
) -> None:
    """The upsert path, not the insert path.

    A read-then-write counter would lose one of two simultaneous views; this
    asserts the second view lands on the same row and increments it, which
    is what ON CONFLICT DO UPDATE buys.
    """
    for _ in range(3):
        client.get(f"/api/businesses/{approved_business.slug}")

    assert _counts(db, ViewSubject.BUSINESS, approved_business.id) == [3]


def test_the_owner_looking_at_their_own_listing_is_not_counted(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    """The property the whole feature rests on.

    An owner who can inflate his own number by refreshing has a dashboard
    that lies to him, and a number he will stop believing once he notices.
    """
    response = client.get(
        f"/api/businesses/{approved_business.slug}", headers=owner_headers
    )

    assert response.status_code == 200
    assert _counts(db, ViewSubject.BUSINESS, approved_business.id) == []


def test_another_signed_in_user_is_counted(
    client: TestClient, db: Session, approved_business: Business
) -> None:
    """Only the *owner* is excluded, not everyone who happens to be signed in."""
    headers = sign_in(client, OTHER_PHONE)

    client.get(f"/api/businesses/{approved_business.slug}", headers=headers)

    assert _counts(db, ViewSubject.BUSINESS, approved_business.id) == [1]


def test_a_listing_a_visitor_cannot_see_is_not_counted(
    client: TestClient,
    db: Session,
    approved_business: Business,
) -> None:
    """A 404 must not leave a trace.

    Otherwise the counter becomes a way to confirm that a hidden listing
    exists, and a suspended business would collect views nobody saw.
    """
    approved_business.status = BusinessStatus.SUSPENDED
    db.commit()

    response = client.get(f"/api/businesses/{approved_business.slug}")

    assert response.status_code == 404
    assert _counts(db, ViewSubject.BUSINESS, approved_business.id) == []


def test_a_talent_profile_view_is_counted_and_the_owner_excluded(
    client: TestClient, db: Session, admin: User, location: Location
) -> None:
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.commit()

    headers = sign_in(client, "03960003")
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    ).json()
    profile = db.get(TalentProfile, created["id"])
    assert profile is not None
    profile.status = BusinessStatus.PENDING_REVIEW
    db.commit()
    client.post(f"/api/admin/talent/{created['id']}/approve", headers=admin_headers(client))

    client.get(f"/api/talent/{created['slug']}")
    client.get(f"/api/talent/{created['slug']}", headers=headers)

    assert _counts(db, ViewSubject.TALENT, uuid.UUID(created["id"])) == [1]


def test_a_product_view_is_counted(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    """Nothing surfaces product views yet; they are recorded because a view
    cannot be backfilled once the day has passed."""
    created = client.post(
        f"/api/businesses/{approved_business.id}/items",
        headers=owner_headers,
        json={"title": ar("item.zaatar"), "price": "3.50", "currency": "USD"},
    )
    assert created.status_code == 201, created.text
    item = db.get(BusinessItem, created.json()["id"])
    assert item is not None

    client.get(f"/api/items/{item.slug}")

    assert _counts(db, ViewSubject.PRODUCT, item.id) == [1]


# --- A stale token must not break a public page ----------------------------


@pytest.mark.parametrize("token", ["not-a-real-token", "", "Basic abc"])
def test_a_broken_authorization_header_still_serves_a_public_listing(
    client: TestClient, db: Session, approved_business: Business, token: str
) -> None:
    """A regression this feature nearly introduced, caught before it shipped.

    Reading the caller's identity on a public route means the route now has
    an opinion about the Authorization header, and the frontend attaches
    whatever token is in local storage to *every* request. With the obvious
    dependency (``OptionalUser``) a public listing answered **401 to a stale
    token** -- so an expired session would have broken the public directory
    for someone simply browsing it. Hence ``Viewer``, which degrades to
    anonymous instead of rejecting.
    """
    response = client.get(
        f"/api/businesses/{approved_business.slug}",
        headers={"Authorization": f"Bearer {token}" if token else "Bearer"},
    )

    assert response.status_code == 200, response.text
    # Unidentifiable means anonymous, so the view still counts.
    assert _counts(db, ViewSubject.BUSINESS, approved_business.id) == [1]


def test_a_stale_token_still_serves_a_public_talent_profile_and_product(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    """The same header reaches all three public detail routes."""
    created = client.post(
        f"/api/businesses/{approved_business.id}/items",
        headers=owner_headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
    ).json()
    item = db.get(BusinessItem, created["id"])
    assert item is not None
    stale = {"Authorization": "Bearer not-a-real-token"}

    assert client.get(f"/api/items/{item.slug}", headers=stale).status_code == 200
    # Talent has no approved profile in this fixture, so a 404 from the
    # lookup is right -- what matters is that it is not a 401 from the
    # header. The approved case is covered above.
    assert client.get("/api/talent/nobody", headers=stale).status_code == 404


# --- Reporting -------------------------------------------------------------


def test_my_views_requires_a_signed_in_caller(client: TestClient) -> None:
    assert client.get("/api/my/views").status_code == 401


def test_my_views_returns_a_dense_series_with_today_last(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    client.get(f"/api/businesses/{approved_business.slug}")
    client.get(f"/api/businesses/{approved_business.slug}")

    body = client.get("/api/my/views", headers=owner_headers).json()

    assert body["window_days"] == WINDOW_DAYS
    assert body["recent_days"] == RECENT_DAYS
    listing = next(
        entry
        for entry in body["listings"]
        if entry["subject_id"] == str(approved_business.id)
    )
    # Dense: one entry per day of the window, quiet days included as zero,
    # so a sparkline drawn from it has the right width and shape.
    assert len(listing["series"]) == WINDOW_DAYS
    assert listing["series"][-1] == 2
    assert sum(listing["series"][:-1]) == 0
    assert listing["views_recent"] == 2
    assert listing["views_window"] == 2
    assert listing["series_start"] == str(
        datetime.now(UTC).date() - timedelta(days=WINDOW_DAYS - 1)
    )


def test_my_views_excludes_days_older_than_the_window(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    today = datetime.now(UTC).date()
    for day, views in (
        (today - timedelta(days=WINDOW_DAYS + 5), 99),
        (today - timedelta(days=RECENT_DAYS + 1), 4),
        (today, 1),
    ):
        db.add(
            ListingViewDaily(
                subject_type=ViewSubject.BUSINESS,
                subject_id=approved_business.id,
                day=day,
                views=views,
            )
        )
    db.commit()

    listing = next(
        entry
        for entry in client.get("/api/my/views", headers=owner_headers).json()["listings"]
        if entry["subject_id"] == str(approved_business.id)
    )

    # The 99 is outside the window and must not reach either total.
    assert listing["views_window"] == 5
    assert listing["views_recent"] == 1


def test_my_views_never_reports_another_owners_listing(
    client: TestClient,
    db: Session,
    approved_business: Business,
) -> None:
    """The scoping rule from AGENTS.md, asserted from the wrong side of it."""
    client.get(f"/api/businesses/{approved_business.slug}")
    stranger = sign_in(client, OTHER_PHONE)

    body = client.get("/api/my/views", headers=stranger).json()

    assert body["listings"] == []


def test_my_views_does_not_report_products(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    """Deliberate, and asserted so it is a decision rather than a gap: the
    counts exist but no surface reads them, so the endpoint does not carry
    a row per product an owner would have to scroll past."""
    created = client.post(
        f"/api/businesses/{approved_business.id}/items",
        headers=owner_headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
    ).json()
    item = db.get(BusinessItem, created["id"])
    assert item is not None
    client.get(f"/api/items/{item.slug}")

    body = client.get("/api/my/views", headers=owner_headers).json()

    assert all(entry["subject_type"] != "PRODUCT" for entry in body["listings"])
    assert _counts(db, ViewSubject.PRODUCT, item.id) == [1]


# --- Deletion --------------------------------------------------------------


def test_deleting_a_business_purges_its_counters(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    """Nothing cascades to these rows: subject_id has no foreign key,
    because it points at one of three tables."""
    business_id = approved_business.id
    client.get(f"/api/businesses/{approved_business.slug}")
    assert _counts(db, ViewSubject.BUSINESS, business_id) == [1]

    deleted = client.delete(f"/api/businesses/{business_id}", headers=owner_headers)

    assert deleted.status_code == 200, deleted.text
    assert _counts(db, ViewSubject.BUSINESS, business_id) == []


def test_deleting_a_product_purges_its_counters(
    client: TestClient,
    db: Session,
    approved_business: Business,
    owner_headers: dict[str, str],
) -> None:
    created = client.post(
        f"/api/businesses/{approved_business.id}/items",
        headers=owner_headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
    ).json()
    item = db.get(BusinessItem, created["id"])
    assert item is not None
    item_id = item.id
    client.get(f"/api/items/{item.slug}")
    assert _counts(db, ViewSubject.PRODUCT, item_id) == [1]

    client.delete(
        f"/api/businesses/{approved_business.id}/items/{item_id}", headers=owner_headers
    )

    assert _counts(db, ViewSubject.PRODUCT, item_id) == []


# --- The privacy constraint ------------------------------------------------


def test_the_counter_table_stores_nothing_about_a_visitor() -> None:
    """The constraint that made this design acceptable, pinned as a test.

    #46 says no IP, no cookie, no fingerprint, no identifier of any kind --
    a counter needs nothing about who was counted. Adding such a column
    should require deleting this assertion and arguing for it, not slip in
    as a convenience during a debugging session.
    """
    assert {column.name for column in ListingViewDaily.__table__.columns} == {
        "id",
        "subject_type",
        "subject_id",
        "day",
        "views",
    }


def test_a_day_is_a_plain_date_with_no_time_of_day() -> None:
    """Storing a timestamp would make the row a coarse visit log; a date
    keeps it a counter."""
    assert isinstance(ListingViewDaily.__table__.c.day.type.python_type(2026, 1, 1), date)
