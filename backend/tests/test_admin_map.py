"""The dashboard's map: every pinned listing, for staff only (the owners'
request, 8 Nov 2026)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.business import Business
from app.models.user import User
from tests.conftest import admin_headers
from tests.test_views import approved_business, owner_headers  # noqa: F401


def test_pinned_shops_are_on_the_staff_map(
    client: TestClient,
    admin: User,
    approved_business: Business,  # noqa: F811
    owner_headers: dict[str, str],  # noqa: F811
) -> None:
    points = client.get("/api/admin/stats/map", headers=admin_headers(client))
    assert points.status_code == 200, points.text
    shop = next(p for p in points.json() if p["id"] == str(approved_business.id))
    assert shop["kind"] == "business"
    assert shop["status"] == "APPROVED"
    assert (shop["latitude"], shop["longitude"]) == (33.27, 35.2)

    # Not for an owner, nor for a visitor.
    assert client.get("/api/admin/stats/map", headers=owner_headers).status_code == 403
    assert client.get("/api/admin/stats/map").status_code == 401
