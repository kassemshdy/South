"""The partner feed (Yalla Pay, AdsTalk): keys, scope, and what it publishes.

The feed is a machine-readable copy of what any visitor can already read,
so the assertions mirror the public ones: approved listings only, available
products only, and nothing of the owner's identity -- the counterpart, for
this surface, of ``tests/test_identity.py``.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus, StaffRole
from app.models.integration import ApiPartner
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services.api_partner import hash_key
from tests.conftest import admin_headers, sign_in
from tests.test_shopify import add_item, approved_business

OWNER_PHONE = "03770001"
OTHER_PHONE = "03770002"

#: Keys of the owner's identity (see ``OwnerIdentityOut``) that must never
#: appear anywhere in the feed.
IDENTITY_KEYS = (
    "legal_name",
    "birth_year",
    "gender",
    "marital_status",
    "registration_place",
    "residence_place",
    "pre_displacement_place",
    "phone_number",
    "owner_identity",
)


def issue_key(client: TestClient, headers: dict[str, str], **body: object) -> str:
    response = client.post(
        "/api/admin/api-partners", headers=headers, json={"name": "Yalla Pay", **body}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["api_key"])


def bearer(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def test_the_feed_needs_a_live_key(client: TestClient, db: Session, admin: User) -> None:
    assert client.get("/api/partner/v1/stores").status_code == 401
    assert client.get("/api/partner/v1/stores", headers=bearer("jnb_nope")).status_code == 401

    headers = admin_headers(client)
    key = issue_key(client, headers)
    assert client.get("/api/partner/v1/stores", headers=bearer(key)).status_code == 200

    partner = db.scalars(select(ApiPartner)).one()
    # Shown once, kept as a hash only.
    assert partner.key_hash == hash_key(key)
    assert key not in json.dumps(client.get("/api/admin/api-partners", headers=headers).json())

    revoked = client.post(f"/api/admin/api-partners/{partner.id}/revoke", headers=headers)
    assert revoked.status_code == 200
    assert client.get("/api/partner/v1/stores", headers=bearer(key)).status_code == 401


def test_rotating_a_key_retires_the_old_one(client: TestClient, db: Session, admin: User) -> None:
    headers = admin_headers(client)
    old = issue_key(client, headers)
    partner = db.scalars(select(ApiPartner)).one()
    new = client.post(f"/api/admin/api-partners/{partner.id}/rotate", headers=headers).json()[
        "api_key"
    ]
    assert client.get("/api/partner/v1/stores", headers=bearer(old)).status_code == 401
    assert client.get("/api/partner/v1/stores", headers=bearer(new)).status_code == 200


def test_only_the_manager_issues_keys(client: TestClient, db: Session, admin: User) -> None:
    admin.staff_role = StaffRole.REVIEWER
    db.commit()
    response = client.post(
        "/api/admin/api-partners", headers=admin_headers(client), json={"name": "AdsTalk"}
    )
    assert response.status_code == 403


def test_a_key_reads_only_what_its_scope_allows(
    client: TestClient, admin: User
) -> None:
    key = issue_key(client, admin_headers(client), scopes=["stores:read"])
    assert client.get("/api/partner/v1/stores", headers=bearer(key)).status_code == 200
    assert client.get("/api/partner/v1/products", headers=bearer(key)).status_code == 403


def test_the_feed_carries_approved_listings_and_no_identity(
    client: TestClient,
    db: Session,
    admin: User,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(client, OWNER_PHONE)
    shown = approved_business(client, db, headers, category, location)
    add_item(client, shown, headers)
    other_headers = sign_in(client, OTHER_PHONE)
    hidden = approved_business(client, db, other_headers, category, location)
    add_item(client, hidden, other_headers)
    hidden_row = db.get(Business, hidden.id)
    assert hidden_row is not None
    hidden_row.status = BusinessStatus.SUSPENDED
    db.commit()

    key = issue_key(client, admin_headers(client))
    stores = client.get("/api/partner/v1/stores", headers=bearer(key)).json()
    assert [s["slug"] for s in stores["items"]] == [shown.slug]
    assert stores["items"][0]["page_url"].endswith(f"/business/{shown.slug}")
    assert stores["items"][0]["online_store_url"] is None
    products = client.get("/api/partner/v1/products", headers=bearer(key)).json()
    assert [p["store_slug"] for p in products["items"]] == [shown.slug]
    assert client.get(f"/api/partner/v1/stores/{hidden.slug}", headers=bearer(key)).status_code == 404

    dumped = json.dumps([stores, products])
    for field in IDENTITY_KEYS:
        assert f'"{field}"' not in dumped


def test_paging_by_cursor_returns_every_row_once(
    client: TestClient,
    db: Session,
    admin: User,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(client, OWNER_PHONE)
    business = approved_business(client, db, headers, category, location)
    for _ in range(5):
        add_item(client, business, headers)
    key = issue_key(client, admin_headers(client))

    seen: list[str] = []
    cursor: str | None = None
    while True:
        params: dict[str, str | int] = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        page = client.get("/api/partner/v1/products", headers=bearer(key), params=params).json()
        seen += [p["id"] for p in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 5 == len(set(seen))
    assert (
        client.get(
            "/api/partner/v1/products", headers=bearer(key), params={"cursor": "%%%"}
        ).status_code
        == 422
    )
