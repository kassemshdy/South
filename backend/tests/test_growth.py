"""The admin dashboard's growth chart: running totals per day."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _business(client: TestClient, category: Category, location: Location, phone: str) -> str:
    created = client.post(
        "/api/businesses",
        headers=sign_in(client, phone),
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def test_growth_is_a_running_total_with_older_rows_as_the_starting_point(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    old = _business(client, category, location, "03990901")
    _business(client, category, location, "03990902")
    _business(client, category, location, "03990903")
    # One from before the window and one from three days ago.
    now = datetime.now(UTC)
    db.get(Business, old).created_at = now - timedelta(days=60)  # type: ignore[union-attr]
    ids = [b.id for b in db.query(Business).all() if str(b.id) != old]
    db.get(Business, ids[0]).created_at = now - timedelta(days=3)  # type: ignore[union-attr]
    db.commit()

    body = client.get("/api/admin/stats/growth?days=7", headers=admin_headers(client)).json()

    assert len(body["days"]) == 7
    businesses = body["totals"]["businesses"]
    assert businesses[0] == 1, "rows older than the window start the line"
    assert businesses[3] == 2 and businesses[-1] == 3
    assert businesses == sorted(businesses)


def test_only_administrators_see_growth(client: TestClient, admin: User) -> None:
    assert client.get("/api/admin/stats/growth").status_code == 401
    owner = sign_in(client, "03990904")
    assert client.get("/api/admin/stats/growth", headers=owner).status_code == 403
