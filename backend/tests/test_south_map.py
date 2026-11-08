"""The public map of the South (the owners' request, 8 Nov 2026)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.business import Business
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
