"""The public map of the South (the owners' request, 8 Nov 2026)."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.user import User
from tests.conftest import admin_headers
from tests.test_views import approved_business, owner_headers  # noqa: F401


def test_published_shops_with_a_pin_are_on_the_public_map(
    client: TestClient,
    approved_business: Business,  # noqa: F811
) -> None:
    listed = client.get("/api/map/listings")
    assert listed.status_code == 200, listed.text
    shop = next(row for row in listed.json() if row["slug"] == approved_business.slug)
    assert shop["kind"] == "business"
    assert (shop["latitude"], shop["longitude"]) == (33.27, 35.2)
    # Nothing a visitor should not see.
    assert not {"phone", "owner_phone", "status", "id"} & set(shop)


def test_a_pin_across_the_border_is_shown_nowhere_and_listed_for_staff(
    client: TestClient,
    db: Session,
    admin: User,
    approved_business: Business,  # noqa: F811
) -> None:
    """A pin saved before pins were checked, across the southern border
    (the owners' report, 9 Nov 2026): no public map shows it, and staff
    find it on their list to move."""
    approved_business.latitude = Decimal("33.18972")
    approved_business.longitude = Decimal("35.63578")
    db.commit()

    assert approved_business.slug not in client.get("/api/map/listings").text
    detail = client.get(f"/api/businesses/{approved_business.slug}").json()
    assert detail["latitude"] is None and detail["longitude"] is None

    stray = client.get("/api/admin/stats/stray-pins", headers=admin_headers(client)).json()
    assert [(row["kind"], row["id"]) for row in stray] == [
        ("business", str(approved_business.id))
    ]
    assert client.get("/api/admin/stats/stray-pins").status_code == 401
