"""Open service requests (the services redesign, 3 Nov 2026): a visitor asks
the team for a service without picking a provider; staff read and archive."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.talent import TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from app.services import telegram_archive
from app.services.telegram_archive import Change, admin_path
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_permissions import _invite


def _payload(**overrides: object) -> dict[str, object]:
    return {
        "customer_name": ar("identity.full_name"),
        "customer_phone": "03 456 789",
        "details": ar("talent.services_offered"),
        **overrides,
    }


def test_a_visitor_asks_and_staff_read_archive_and_reopen(
    client: TestClient, db: Session, admin: User, location: Location
) -> None:
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.commit()
    sent = client.post(
        "/api/service-requests",
        json=_payload(skill_id=str(skill.id), location_id=str(location.id)),
    )
    assert sent.status_code == 201, sent.text
    assert set(sent.json()) == {"message"}

    headers = admin_headers(client)
    [entry] = client.get("/api/admin/service-requests", headers=headers).json()
    assert entry["customer_phone"] == "+9613456789"
    assert (entry["skill_slug"], entry["location_slug"]) == ("design", location.slug)

    solved = client.post(f"/api/admin/service-requests/{entry['id']}/solve", headers=headers)
    assert solved.status_code == 200 and solved.json()["solved_at"] is not None
    assert client.get("/api/admin/service-requests", headers=headers).json() == []
    archived = client.get("/api/admin/service-requests?solved=true", headers=headers).json()
    assert [row["id"] for row in archived] == [entry["id"]]
    client.post(f"/api/admin/service-requests/{entry['id']}/reopen", headers=headers)
    assert len(client.get("/api/admin/service-requests", headers=headers).json()) == 1


def test_the_skill_and_town_are_optional_but_must_exist(client: TestClient) -> None:
    assert client.post("/api/service-requests", json=_payload()).status_code == 201
    unknown = client.post("/api/service-requests", json=_payload(skill_id=str(uuid.uuid4())))
    assert unknown.status_code == 422
    assert client.post("/api/service-requests", json=_payload(details="short")).status_code == 422


def test_nobody_but_staff_reads_them_and_viewers_cannot_archive(
    client: TestClient, admin: User
) -> None:
    client.post("/api/service-requests", json=_payload())
    assert client.get("/api/admin/service-requests").status_code == 401
    manager = admin_headers(client)
    viewer = _invite(client, manager, "VIEWER", "viewer-open@example.com")
    support = _invite(client, manager, "SUPPORT", "support-open@example.com")
    [entry] = client.get("/api/admin/service-requests", headers=viewer).json()
    url = f"/api/admin/service-requests/{entry['id']}/solve"
    assert client.post(url, headers=viewer).status_code == 403
    assert client.post(url, headers=support).status_code == 200


def test_one_sender_is_rate_limited(client: TestClient) -> None:
    codes = [client.post("/api/service-requests", json=_payload()).status_code for _ in range(7)]
    assert 429 in codes


def test_they_are_archived_to_telegram_and_link_to_their_page() -> None:
    assert "open_service_requests" in telegram_archive.ARCHIVED_TABLES
    change = Change(action="created", table="open_service_requests", row_id="x")
    assert admin_path(change, lambda _: None) == "/admin/service-requests"
