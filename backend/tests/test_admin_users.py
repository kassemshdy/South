"""The admin user detail: everything one account owns, in any status.

Unlike the aggregate list (``admin/stats.py``), this exists so an
administrator can go straight from a user to reviewing what they've listed —
including a business/talent website link — without hunting through
/admin/businesses by owner phone number.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def test_admin_sees_a_users_businesses_including_the_website_link(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03980001")
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.seo_name"),
            "short_description": ar("business.seo_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "website": "https://example.com",
        },
    ).json()

    me = client.get("/api/me", headers=owner_headers).json()

    detail = client.get(f"/api/admin/users/{me['id']}", headers=admin_headers(client))
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["business_count"] == 1
    assert len(body["businesses"]) == 1
    assert body["businesses"][0]["id"] == created["id"]
    assert body["businesses"][0]["website"] == "https://example.com"
    assert body["businesses"][0]["status"] == "DRAFT"
    assert body["talent_profile"] is None


def test_admin_sees_a_users_talent_profile(
    client: TestClient, admin: User, location: Location
) -> None:
    owner_headers = sign_in(client, "03980002")

    # A minimal skill row, the same way test_talent.py's own fixture does it.
    skill_response = client.get("/api/talent-skills").json()
    skill_id = skill_response[0]["id"] if skill_response else None
    payload = {
        "display_name": ar("talent.designer"),
        "location_id": str(location.id),
    }
    if skill_id:
        payload["skill_id"] = skill_id
    created = client.post("/api/talent", headers=owner_headers, json=payload)
    assert created.status_code == 201, created.text
    profile = created.json()

    me = client.get("/api/me", headers=owner_headers).json()

    detail = client.get(f"/api/admin/users/{me['id']}", headers=admin_headers(client))
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["talent_profile"] is not None
    assert body["talent_profile"]["id"] == profile["id"]
    assert body["businesses"] == []


def test_unknown_user_id_404s(client: TestClient, admin: User) -> None:
    response = client.get(
        f"/api/admin/users/{uuid.uuid4()}", headers=admin_headers(client)
    )
    assert response.status_code == 404


def test_owner_cannot_reach_another_users_detail(
    client: TestClient, admin: User
) -> None:
    owner_headers = sign_in(client, "03980003")
    me = client.get("/api/me", headers=owner_headers).json()

    assert (
        client.get(f"/api/admin/users/{me['id']}", headers=owner_headers).status_code
        == 403
    )


def test_unauthenticated_is_rejected(client: TestClient, admin: User) -> None:
    assert client.get(f"/api/admin/users/{admin.id}").status_code == 401
