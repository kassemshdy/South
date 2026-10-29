"""Workshops (29 Oct 2026): written and published by administrators, found
by anyone, signed up for anonymously; who signed up is read by staff only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services import telegram_archive
from scripts.seed_data import WORKSHOPS
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_permissions import _invite


def _create(
    client: TestClient, headers: dict[str, str], *, days: int = 7, publish: bool = True, **extra
) -> dict:
    body = {
        "title": ar("business.first"),
        "description": ar("business.applicant_description"),
        "starts_at": (datetime.now(UTC) + timedelta(days=days)).isoformat(),
        **extra,
    }
    created = client.post("/api/admin/workshops", headers=headers, json=body)
    assert created.status_code == 201, created.text
    workshop = created.json()
    if publish:
        published = client.post(f"/api/admin/workshops/{workshop['id']}/publish", headers=headers)
        assert published.status_code == 200, published.text
    return workshop


def test_a_draft_is_invisible_until_published(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    draft = _create(client, headers, publish=False)
    assert client.get("/api/workshops").json() == []
    assert client.get(f"/api/workshops/{draft['slug']}").status_code == 404

    client.post(f"/api/admin/workshops/{draft['id']}/publish", headers=headers)
    assert [w["slug"] for w in client.get("/api/workshops").json()] == [draft["slug"]]
    assert client.get(f"/api/workshops/{draft['slug']}").status_code == 200


def test_upcoming_soonest_first_and_past_apart(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    later = _create(client, headers, days=20, slug="later")
    sooner = _create(client, headers, days=2, slug="sooner")
    over = _create(client, headers, days=-10, slug="over")

    upcoming = [w["slug"] for w in client.get("/api/workshops").json()]
    assert upcoming == [sooner["slug"], later["slug"]]
    assert [w["slug"] for w in client.get("/api/workshops?when=past").json()] == [over["slug"]]


def test_related_by_category_and_town(
    client: TestClient,
    db: Session,
    admin: User,
    category: Category,
    category_other: Category,
    location: Location,
) -> None:
    headers = admin_headers(client)
    town = Location(name_ar=ar("location.tyre"), slug="town-x", type="TOWN", parent_id=location.id)
    db.add(town)
    db.commit()
    general = _create(client, headers, slug="general")
    on_topic = _create(client, headers, slug="on-topic", category_id=str(category.id))
    off_topic = _create(client, headers, slug="off-topic", category_id=str(category_other.id))
    in_district = _create(client, headers, slug="in-district", location_id=str(location.id))
    online = _create(
        client, headers, slug="online", mode="ONLINE", location_id=str(location.id)
    )

    by_category = {w["slug"] for w in client.get(f"/api/workshops?category={category.slug}").json()}
    assert on_topic["slug"] in by_category and general["slug"] in by_category
    assert off_topic["slug"] not in by_category

    by_town = {w["slug"] for w in client.get("/api/workshops?location=town-x").json()}
    assert in_district["slug"] in by_town, "a town's district counts as the town"
    assert online["slug"] in by_town and general["slug"] in by_town


def test_signing_up_is_kept_for_staff_only(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    workshop = _create(client, headers)

    signed = client.post(
        f"/api/workshops/{workshop['slug']}/register",
        json={"full_name": ar("order.customer"), "phone_number": "70 111 444"},
    )
    assert signed.status_code == 201, signed.text

    public = client.get(f"/api/workshops/{workshop['slug']}").text
    assert "111" not in public and ar("order.customer") not in public

    listed = client.get(
        f"/api/admin/workshops/{workshop['id']}/registrations", headers=headers
    ).json()
    assert [row["full_name"] for row in listed] == [ar("order.customer")]
    assert listed[0]["phone_number"].endswith("70111444")
    assert client.get("/api/admin/workshops", headers=headers).json()[0][
        "registration_count"
    ] == 1
    assert client.get(f"/api/admin/workshops/{workshop['id']}/registrations").status_code == 401


def test_no_sign_up_for_a_draft_or_a_started_workshop(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    draft = _create(client, headers, publish=False, slug="draft")
    started = _create(client, headers, days=0, slug="started")
    payload = {"full_name": ar("order.customer"), "phone_number": "70111444"}

    assert client.post(f"/api/workshops/{draft['slug']}/register", json=payload).status_code == 404
    refused = client.post(f"/api/workshops/{started['slug']}/register", json=payload)
    assert refused.status_code == 422


def test_content_editors_write_workshops_and_support_cannot(
    client: TestClient, admin: User
) -> None:
    manager = admin_headers(client)
    editor = _invite(client, manager, "EDITOR", "editor@example.com")
    support = _invite(client, manager, "SUPPORT", "support@example.com")
    _create(client, editor, slug="by-editor")
    body = {
        "title": ar("business.first"),
        "description": ar("business.applicant_description"),
        "starts_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
    }
    assert client.post("/api/admin/workshops", headers=support, json=body).status_code == 403


def test_sign_ups_are_copied_to_the_telegram_archive() -> None:
    assert "workshop_registrations" in telegram_archive.ARCHIVED_TABLES


def test_the_examples_arrive_as_online_drafts_once(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    added = client.post("/api/admin/workshops/examples", headers=headers)
    assert added.status_code == 200, added.text
    examples = added.json()
    assert len(examples) == len(WORKSHOPS)
    assert {w["slug"] for w in examples} == {seed["slug"] for seed in WORKSHOPS}
    assert all(w["mode"] == "ONLINE" and not w["is_published"] for w in examples)
    assert all(w["price"] is None and w["trainer_name"] is None for w in examples)
    assert client.get("/api/workshops").json() == [], "drafts reach nobody"

    assert client.post("/api/admin/workshops/examples", headers=headers).json() == []
    support = _invite(client, headers, "SUPPORT", "support-examples@example.com")
    refused = client.post("/api/admin/workshops/examples", headers=support)
    assert refused.status_code == 403


def test_the_online_section_lists_online_workshops_only(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    online = _create(client, headers, slug="online", mode="ONLINE")
    _create(client, headers, slug="in-person", mode="IN_PERSON")

    listed = client.get("/api/workshops?mode=ONLINE").json()
    assert [w["slug"] for w in listed] == [online["slug"]]
    assert len(client.get("/api/workshops").json()) == 2
