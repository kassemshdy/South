"""Staff roles: who may do what in the admin area.

The policy is one table (``app/core/permissions.py``) applied by
``require_admin``. These tests pin that every admin write was decided on
explicitly, and walk each role through the things it may and may not do.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.permissions import WRITES
from app.main import create_app
from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _admin_writes() -> set[tuple[str, str]]:
    def uses_admin(dependant) -> bool:  # type: ignore[no-untyped-def]
        return any(d.call is require_admin or uses_admin(d) for d in dependant.dependencies)

    return {
        (method, route.path)
        for route in create_app().routes
        if hasattr(route, "dependant") and uses_admin(route.dependant)
        for method in route.methods
        if method not in ("GET", "HEAD")
    }


def test_every_admin_write_has_an_explicit_decision() -> None:
    """A new admin route falls back to manager-only; this makes that a
    visible choice rather than an accident."""
    undecided = _admin_writes() - set(WRITES)
    assert not undecided, f"add these to WRITES in app/core/permissions.py: {sorted(undecided)}"


def _invite(client: TestClient, manager: dict[str, str], role: str, email: str) -> dict[str, str]:
    invited = client.post(
        "/api/admin/staff",
        headers=manager,
        json={"email": email, "display_name": ar("user.admin_name"), "staff_role": role},
    )
    assert invited.status_code == 201, invited.text
    login = client.post(
        "/api/auth/login",
        json={"identifier": email, "password": invited.json()["password"]},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _pending_business(
    client: TestClient, db: Session, category: Category, location: Location
) -> str:
    created = client.post(
        "/api/businesses",
        headers=sign_in(client, "03991001"),
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    entity = db.get(Business, created.json()["id"])
    assert entity is not None
    entity.status = BusinessStatus.PENDING_REVIEW
    entity.logo_url = "/media/test/logo.jpg"  # approval needs one
    db.commit()
    return str(entity.id)


def test_each_role_can_do_its_work_and_nothing_else(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    manager = admin_headers(client)
    viewer = _invite(client, manager, "VIEWER", "viewer@example.com")
    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")
    support = _invite(client, manager, "SUPPORT", "support@example.com")
    editor = _invite(client, manager, "EDITOR", "editor@example.com")
    business_id = _pending_business(client, db, category, location)
    owner_id = str(db.get(Business, business_id).owner_id)  # type: ignore[union-attr]

    # Everyone reads the admin area.
    for headers in (viewer, reviewer, support, editor):
        assert client.get("/api/admin/stats", headers=headers).status_code == 200

    # Only reviewers (and the manager) approve, or read an ID scan.
    approve = f"/api/admin/businesses/{business_id}/approve"
    for headers in (viewer, support, editor):
        assert client.post(approve, headers=headers).status_code == 403
    assert client.post(approve, headers=reviewer).status_code == 200
    document = f"/api/admin/users/{owner_id}/verification-document"
    for headers in (viewer, support, editor):
        assert client.get(document, headers=headers).status_code == 403

    # Support and reviewers issue owners' passwords; editors and viewers do not.
    credentials = f"/api/admin/users/{owner_id}/credentials"
    assert client.post(credentials, headers=editor).status_code == 403
    assert client.post(credentials, headers=viewer).status_code == 403
    assert client.post(credentials, headers=support).status_code == 200

    # The manager's alone: export, staff, site settings, permanent deletes.
    for headers in (viewer, reviewer, support, editor):
        assert client.get("/api/admin/export/users.csv", headers=headers).status_code == 403
        assert client.get("/api/admin/staff", headers=headers).status_code == 403
        assert client.put("/api/admin/site-settings", headers=headers, json={}).status_code == 403
        assert (
            client.delete(f"/api/admin/businesses/{business_id}", headers=headers).status_code
            == 403
        )
    assert client.get("/api/admin/export/users.csv", headers=manager).status_code == 200


def test_the_manager_cannot_lock_the_admin_area(client: TestClient, admin: User) -> None:
    manager = admin_headers(client)
    me = client.get("/api/admin/staff", headers=manager).json()[0]

    # Not themselves...
    assert (
        client.patch(
            f"/api/admin/staff/{me['id']}", headers=manager, json={"staff_role": "VIEWER"}
        ).status_code
        == 422
    )
    # ...and never the last active manager.
    second = client.post(
        "/api/admin/staff",
        headers=manager,
        json={"email": "second@example.com", "display_name": "Second", "staff_role": "MANAGER"},
    ).json()["staff"]
    second_headers = {
        "Authorization": "Bearer "
        + client.post(
            "/api/auth/login",
            json={
                "identifier": "second@example.com",
                "password": client.post(
                    f"/api/admin/staff/{second['id']}/password", headers=manager
                ).json()["password"],
            },
        ).json()["access_token"]
    }
    disabled = client.patch(
        f"/api/admin/staff/{me['id']}", headers=second_headers, json={"is_active": False}
    )
    assert disabled.status_code == 200, disabled.text
    assert client.get("/api/admin/stats", headers=manager).status_code == 401, (
        "a disabled account's session ends at once"
    )
    assert (
        client.patch(
            f"/api/admin/staff/{second['id']}", headers=second_headers, json={"is_active": False}
        ).status_code
        == 422
    )


def test_an_invited_email_must_be_new(client: TestClient, admin: User) -> None:
    manager = admin_headers(client)
    taken = client.post(
        "/api/admin/staff",
        headers=manager,
        json={"email": "ADMIN@example.com", "display_name": "Dup", "staff_role": "VIEWER"},
    )
    assert taken.status_code == 409
