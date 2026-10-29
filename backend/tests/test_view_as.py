"""An administrator seeing an owner's account read-only (29 Oct 2026).

The session is the owner's, so every owner route answers as it would for
them; it may change nothing, it dies with either side's sessions, and only
the roles that already read owners' documents may open one.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import admin_headers, make_owner, sign_in
from tests.samples import ar
from tests.test_permissions import _invite


def _view_as(client: TestClient, headers: dict[str, str], user_id: object) -> dict[str, str]:
    opened = client.post(f"/api/admin/users/{user_id}/view-as", headers=headers)
    assert opened.status_code == 200, opened.text
    return {"Authorization": f"Bearer {opened.json()['access_token']}"}


def test_the_admin_sees_the_owners_account_and_can_change_nothing(
    client: TestClient, admin: User
) -> None:
    owner = make_owner("03660601")
    as_owner = _view_as(client, admin_headers(client), owner.id)

    me = client.get("/api/me", headers=as_owner)
    assert me.status_code == 200 and me.json()["id"] == str(owner.id)
    assert client.get("/api/my/businesses", headers=as_owner).status_code == 200

    for method, path, body in (
        ("PATCH", "/api/me", {"display_name": ar("business.first")}),
        ("POST", "/api/businesses", {"name": ar("business.first")}),
        # The two that would hurt most: the owner's password and account.
        ("POST", "/api/me/password", {"current_password": "x", "new_password": "y" * 12}),
        ("POST", "/api/me/delete", {"password": "x"}),
    ):
        refused = client.request(method, path, headers=as_owner, json=body)
        assert refused.status_code == 403, (method, path, refused.text)
        assert refused.json()["error"]["code"] == "view_only"


def test_it_opens_nothing_in_the_admin_area(client: TestClient, admin: User) -> None:
    owner = make_owner("03660602")
    as_owner = _view_as(client, admin_headers(client), owner.id)
    assert client.get("/api/admin/stats", headers=as_owner).status_code == 403


def test_only_reviewers_and_the_manager_may_open_one(client: TestClient, admin: User) -> None:
    owner = make_owner("03660603")
    manager = admin_headers(client)
    support = _invite(client, manager, "SUPPORT", "support@example.com")
    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")

    assert client.post(f"/api/admin/users/{owner.id}/view-as", headers=support).status_code == 403
    assert client.post(f"/api/admin/users/{owner.id}/view-as", headers=reviewer).status_code == 200
    assert client.post(f"/api/admin/users/{owner.id}/view-as").status_code == 401
    assert (
        client.post(f"/api/admin/users/{owner.id}/view-as", headers=sign_in(client, "03660604"))
        .status_code
        == 403
    )


def test_never_for_an_administrators_account(client: TestClient, admin: User) -> None:
    refused = client.post(f"/api/admin/users/{admin.id}/view-as", headers=admin_headers(client))
    assert refused.status_code == 403


def test_it_ends_when_either_side_signs_out_everywhere(
    client: TestClient, db: Session, admin: User
) -> None:
    owner = make_owner("03660605")
    as_owner = _view_as(client, admin_headers(client), owner.id)
    assert client.get("/api/me", headers=as_owner).status_code == 200

    staff = db.get(User, admin.id)
    assert staff is not None
    staff.token_version += 1
    db.commit()
    assert client.get("/api/me", headers=as_owner).status_code == 401

    staff.token_version -= 1
    db.commit()
    account = db.get(User, owner.id)
    assert account is not None
    account.token_version += 1
    db.commit()
    assert client.get("/api/me", headers=as_owner).status_code == 401
