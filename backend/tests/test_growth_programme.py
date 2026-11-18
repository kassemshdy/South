"""The growth programme in admin (the owners' decision, 18 Nov 2026)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers
from tests.test_admin_corrections import _listing
from tests.test_permissions import _invite


def test_staff_enrol_a_shop_move_it_along_and_see_before_and_now(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    business_id, _owner = _listing(client, category, location)
    business = db.get(Business, uuid.UUID(business_id))
    assert business is not None
    business.instagram_followers = 1200
    db.commit()

    manager = admin_headers(client)
    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")
    viewer = _invite(client, manager, "VIEWER", "viewer@example.com")

    # A viewer reads it but does not enrol; a reviewer does.
    assert (
        client.post(
            "/api/admin/growth-programme", headers=viewer, json={"business_id": business_id}
        ).status_code
        == 403
    )
    joined = client.post("/api/admin/growth-programme", headers=reviewer, json={"business_id": business_id})
    assert joined.status_code == 201, joined.text
    row = joined.json()
    assert row["stage"] == "CONTACTED" and row["before"]["instagram"] == 1200
    assert row["enrolled_by_name"]
    again = client.post("/api/admin/growth-programme", headers=reviewer, json={"business_id": business_id})
    assert again.status_code == 409

    # Followers grow; "before" keeps the day it joined.
    business.instagram_followers = 1500
    db.commit()
    moved = client.put(
        f"/api/admin/growth-programme/{business_id}",
        headers=reviewer,
        json={"stage": "SHOPIFY", "note": "ready"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"] == "SHOPIFY" and moved.json()["note"] == "ready"
    listed = client.get("/api/admin/growth-programme", headers=viewer).json()
    assert [(r["before"]["instagram"], r["now"]["instagram"]) for r in listed] == [(1200, 1500)]
    assert (
        client.put(
            f"/api/admin/growth-programme/{business_id}", headers=reviewer, json={"stage": "SOMEWHERE"}
        ).status_code
        == 422
    )

    assert client.delete(f"/api/admin/growth-programme/{business_id}", headers=reviewer).status_code == 200
    assert client.get(f"/api/admin/growth-programme/{business_id}", headers=manager).status_code == 404
