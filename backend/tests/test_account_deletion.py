"""An owner can delete their own account, and "delete" means everything.

Listings, products and the talent profile go with the account, and so do the
files: an identity scan left in storage after its owner deleted the account
is the leftover nobody would think to look for.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.business import Business
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import OWNER_PASSWORD, admin_headers, sign_in
from tests.samples import ar

PHONE = "03990001"


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for tests\n"


def test_deleting_an_account_removes_its_listings_and_its_files(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, PHONE)
    me = client.get("/api/me", headers=headers).json()
    uploaded = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("id.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    scans = Path(get_settings().storage_local_dir) / "owner-verification" / me["id"]
    assert any(scans.iterdir())

    # The password again, not just the session.
    refused = client.post("/api/me/delete", headers=headers, json={"password": "wrong-password"})
    assert refused.status_code == 403, refused.text  # not 401: that signs the client out
    assert db.scalars(select(User).where(User.id == me["id"])).first() is not None

    deleted = client.post("/api/me/delete", headers=headers, json={"password": OWNER_PASSWORD})
    assert deleted.status_code == 200, deleted.text

    db.expire_all()
    assert db.scalars(select(User).where(User.id == me["id"])).first() is None
    assert db.scalars(select(Business).where(Business.id == created.json()["id"])).first() is None
    assert not scans.exists() or not any(scans.iterdir())
    # And the session it was deleted from no longer opens anything.
    assert client.get("/api/me", headers=headers).status_code == 401
    login = client.post("/api/auth/login", json={"identifier": PHONE, "password": OWNER_PASSWORD})
    assert login.status_code == 401


def test_an_administrator_account_cannot_be_deleted_this_way(
    client: TestClient, db: Session, admin: User
) -> None:
    response = client.post(
        "/api/me/delete", headers=admin_headers(client), json={"password": "AdminPass!123"}
    )
    assert response.status_code == 403, response.text
    db.expire_all()
    assert db.get(User, admin.id) is not None
