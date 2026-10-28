"""The partner form (round 3): anyone may send one, only an administrator reads it."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _payload(**overrides: object) -> dict[str, object]:
    return {
        "name": ar("identity.full_name"),
        "phone": "03 456 789",
        "occupation": ar("talent.specialization"),
        "residence": ar("identity.residence_place"),
        "offer": ar("talent.services_offered"),
        **overrides,
    }


def test_a_visitor_sends_one_and_an_administrator_reads_it(
    client: TestClient, admin: User
) -> None:
    sent = client.post("/api/partners", json=_payload())
    assert sent.status_code == 201, sent.text
    # Nothing about the stored row comes back.
    assert set(sent.json()) == {"message"}

    listed = client.get("/api/admin/partners", headers=admin_headers(client))
    assert listed.status_code == 200, listed.text
    [entry] = listed.json()
    assert entry["name"] == ar("identity.full_name")
    assert entry["phone"] == "+9613456789"
    assert entry["offer"] == ar("talent.services_offered")

    removed = client.delete(
        f"/api/admin/partners/{entry['id']}", headers=admin_headers(client)
    )
    assert removed.status_code == 200, removed.text
    assert client.get("/api/admin/partners", headers=admin_headers(client)).json() == []


def test_every_field_is_required(client: TestClient) -> None:
    for field in ("name", "phone", "occupation", "residence", "offer"):
        response = client.post("/api/partners", json=_payload(**{field: ""}))
        assert response.status_code == 422, (field, response.text)


def test_only_an_administrator_reads_them(client: TestClient) -> None:
    client.post("/api/partners", json=_payload())
    assert client.get("/api/admin/partners").status_code == 401
    assert client.get("/api/admin/partners", headers=sign_in(client, "03993001")).status_code == 403


def test_one_sender_is_rate_limited(client: TestClient) -> None:
    headers = {"X-Forwarded-For": "198.51.100.40"}
    for _ in range(3):
        assert client.post("/api/partners", json=_payload(), headers=headers).status_code == 201
    assert client.post("/api/partners", json=_payload(), headers=headers).status_code == 429


def test_a_solved_request_moves_to_the_archive_and_can_come_back(
    client: TestClient, admin: User
) -> None:
    """The owners asked to keep handled requests rather than delete them."""
    assert client.post("/api/partners", json=_payload()).status_code == 201
    headers = admin_headers(client)
    [entry] = client.get("/api/admin/partners", headers=headers).json()
    assert entry["solved_at"] is None

    solved = client.post(f"/api/admin/partners/{entry['id']}/solve", headers=headers)
    assert solved.status_code == 200, solved.text
    assert solved.json()["solved_at"] is not None
    assert client.get("/api/admin/partners", headers=headers).json() == []
    archive = client.get("/api/admin/partners", params={"solved": True}, headers=headers).json()
    assert [row["id"] for row in archive] == [entry["id"]]

    reopened = client.post(f"/api/admin/partners/{entry['id']}/reopen", headers=headers)
    assert reopened.status_code == 200, reopened.text
    assert [row["id"] for row in client.get("/api/admin/partners", headers=headers).json()] == [
        entry["id"]
    ]


def test_an_owner_cannot_solve_one(client: TestClient, admin: User) -> None:
    assert client.post("/api/partners", json=_payload()).status_code == 201
    [entry] = client.get("/api/admin/partners", headers=admin_headers(client)).json()
    owner = sign_in(client, "03990001")
    assert client.post(f"/api/admin/partners/{entry['id']}/solve", headers=owner).status_code == 403
