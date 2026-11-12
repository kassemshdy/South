"""Admin screens name the staff member behind each decision (the owners'
request, 12 Nov 2026): who approved a shop, who took each step in its
history, and who contacted it about adding products. Never an owner."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.serializers import staff_name
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_permissions import _invite, _pending_business


def test_admin_payloads_name_who_approved_and_who_contacted(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    manager = admin_headers(client)
    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")
    reviewer_name = ar("user.admin_name")
    business_id = _pending_business(client, db, category, location)

    approved = client.post(f"/api/admin/businesses/{business_id}/approve", headers=reviewer)
    assert approved.status_code == 200, approved.text
    assert approved.json()["approved_by_name"] == reviewer_name

    detail = client.get(f"/api/admin/businesses/{business_id}", headers=manager).json()
    assert detail["approved_by_name"] == reviewer_name
    decided = [a for a in detail["moderation_actions"] if a["to_status"] == "APPROVED"]
    assert decided and decided[-1]["actor_name"] == reviewer_name

    contacted = client.put(
        f"/api/admin/businesses/{business_id}/outreach",
        headers=reviewer,
        json={"contacted": True, "note": None},
    )
    assert contacted.status_code == 200, contacted.text
    listed = client.get(
        "/api/admin/businesses?status=APPROVED&without_products=true", headers=manager
    ).json()["items"][0]
    assert listed["approved_by_name"] == reviewer_name
    assert listed["outreach_contacted_by_name"] == reviewer_name


def test_an_owner_is_never_named_as_the_one_who_decided(db: Session, admin: User) -> None:
    owner = User(phone_number="+96103991002", display_name=ar("user.admin_name"))
    db.add(owner)
    db.commit()
    assert staff_name(owner) is None
    assert staff_name(None) is None
    assert staff_name(admin) == (admin.display_name or admin.email)
