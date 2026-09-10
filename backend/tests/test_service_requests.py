"""Service requests: asking a talent profile for a piece of work.

The counterpart to ``test_orders.py``, and it exists because the directory
was asymmetric: a product could be requested and the request reached the
owner's dashboard, while a craftsperson got a WhatsApp link that leaves no
record. What is asserted here is that the two halves now behave the same way
where it matters, plus the three ways this one could quietly betray somebody:

- a request must not be placeable on a profile a visitor **cannot see**;
- one provider must not be able to read or move **another's** request;
- the requester's name and phone must reach **that provider and nobody
  else** -- no public read, no administrator read.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import BusinessStatus, OrderStatus
from app.models.service_request import ServiceRequest
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

PROVIDER_PHONE = "03960001"
OTHER_PROVIDER_PHONE = "03960002"
CUSTOMER_PHONE = "03960100"


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


def _approved_profile(
    client: TestClient,
    db: Session,
    admin: User,
    headers: dict[str, str],
    skill: TalentSkill,
    location: Location,
    *,
    display_name: str,
) -> TalentProfile:
    """A profile pushed all the way to APPROVED.

    Submission needs a photo upload, which is asserted by ``test_talent.py``
    and irrelevant here, so the status is moved directly and only the
    moderation step goes through the API.
    """
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": display_name,
            "headline": ar("talent.designer_headline"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "whatsapp": PROVIDER_PHONE,
        },
    )
    assert created.status_code == 201, created.text

    profile = db.get(TalentProfile, created.json()["id"])
    assert profile is not None
    profile.status = BusinessStatus.PENDING_REVIEW
    db.commit()

    approved = client.post(
        f"/api/admin/talent/{profile.id}/approve", headers=admin_headers(client)
    )
    assert approved.status_code == 200, approved.text
    db.refresh(profile)
    return profile


@pytest.fixture
def provider_headers(client: TestClient) -> dict[str, str]:
    return sign_in(client, PROVIDER_PHONE)


@pytest.fixture
def designer(
    client: TestClient,
    db: Session,
    admin: User,
    provider_headers: dict[str, str],
    skill: TalentSkill,
    location: Location,
) -> TalentProfile:
    return _approved_profile(
        client,
        db,
        admin,
        provider_headers,
        skill,
        location,
        display_name=ar("talent.designer"),
    )


def _ask(client: TestClient, slug: str, **extra: object):
    payload: dict[str, object] = {
        "customer_name": ar("service_request.customer"),
        "customer_phone": CUSTOMER_PHONE,
        "details": ar("service_request.details"),
    }
    payload.update(extra)
    return client.post(f"/api/talent/{slug}/requests", json=payload)


def test_a_visitor_asks_for_work_and_the_provider_sees_it(
    client: TestClient, designer: TalentProfile, provider_headers: dict[str, str]
) -> None:
    placed = _ask(client, designer.slug)
    assert placed.status_code == 201, placed.text

    mine = client.get("/api/my/talent/requests", headers=provider_headers)
    assert mine.status_code == 200, mine.text
    rows = mine.json()
    assert len(rows) == 1
    assert rows[0]["customer_name"] == ar("service_request.customer")
    assert rows[0]["details"] == ar("service_request.details")
    assert rows[0]["status"] == "NEW"


def test_asking_needs_no_account(client: TestClient, designer: TalentProfile) -> None:
    """The whole point: no wall between someone and the one action the
    feature exists to produce."""
    placed = _ask(client, designer.slug)
    assert placed.status_code == 201
    assert "Authorization" not in placed.request.headers


def test_the_provider_moves_a_request_along(
    client: TestClient, db: Session, designer: TalentProfile, provider_headers: dict[str, str]
) -> None:
    _ask(client, designer.slug)
    request_id = client.get("/api/my/talent/requests", headers=provider_headers).json()[0]["id"]

    contacted = client.post(
        f"/api/my/talent/requests/{request_id}/status",
        headers=provider_headers,
        json={"status": "CONTACTED"},
    )
    assert contacted.status_code == 200, contacted.text
    assert contacted.json()["status"] == "CONTACTED"

    done = client.post(
        f"/api/my/talent/requests/{request_id}/status",
        headers=provider_headers,
        json={"status": "DONE"},
    )
    assert done.status_code == 200
    stored = db.get(ServiceRequest, uuid.UUID(request_id))
    assert stored is not None
    db.refresh(stored)
    assert stored.status is OrderStatus.DONE


def test_a_request_cannot_be_placed_on_a_profile_a_visitor_cannot_see(
    client: TestClient, db: Session, designer: TalentProfile
) -> None:
    designer.status = BusinessStatus.SUSPENDED
    db.commit()

    refused = _ask(client, designer.slug)
    assert refused.status_code == 404
    assert db.execute(select(ServiceRequest)).scalars().all() == []


def test_a_request_must_describe_the_work(client: TestClient, designer: TalentProfile) -> None:
    """There are no line items here, so the description is the whole request.
    A name and a phone number with nothing attached is not one."""
    refused = _ask(client, designer.slug, details=ar("service_request.too_short"))
    assert refused.status_code == 422


def test_another_provider_cannot_read_or_move_a_request(
    client: TestClient,
    db: Session,
    admin: User,
    designer: TalentProfile,
    provider_headers: dict[str, str],
    skill: TalentSkill,
    location: Location,
) -> None:
    _ask(client, designer.slug)
    request_id = client.get("/api/my/talent/requests", headers=provider_headers).json()[0]["id"]

    intruder_headers = sign_in(client, OTHER_PROVIDER_PHONE)
    _approved_profile(
        client,
        db,
        admin,
        intruder_headers,
        skill,
        location,
        display_name=ar("talent.photographer"),
    )

    # The list is resolved from the token, so it simply is not there.
    assert client.get("/api/my/talent/requests", headers=intruder_headers).json() == []

    # And the id is a 404, not a 403: nothing here confirms it exists.
    stolen = client.post(
        f"/api/my/talent/requests/{request_id}/status",
        headers=intruder_headers,
        json={"status": "DONE"},
    )
    assert stolen.status_code == 404


def test_a_request_is_never_on_the_public_profile(
    client: TestClient, designer: TalentProfile
) -> None:
    _ask(client, designer.slug)
    public = client.get(f"/api/talent/{designer.slug}")
    assert public.status_code == 200
    body = public.text
    assert ar("service_request.customer") not in body
    assert CUSTOMER_PHONE not in body


def test_no_admin_route_exposes_a_service_request(
    client: TestClient, designer: TalentProfile, admin: User
) -> None:
    """Moderation has no reason to know who asked whom for what, so no admin
    payload carries a request -- the same rule orders live under."""
    _ask(client, designer.slug)
    headers = admin_headers(client)

    detail = client.get(f"/api/admin/talent/{designer.id}", headers=headers)
    assert detail.status_code == 200
    assert ar("service_request.customer") not in detail.text

    routes = [
        route.path
        for route in client.app.routes  # type: ignore[attr-defined]
        if "requests" in getattr(route, "path", "")
    ]
    assert all(not path.startswith("/api/admin") for path in routes)


def test_an_unauthenticated_caller_cannot_read_requests(
    client: TestClient, designer: TalentProfile
) -> None:
    _ask(client, designer.slug)
    assert client.get("/api/my/talent/requests").status_code == 401


def test_one_profile_cannot_be_flooded_from_many_addresses(
    client: TestClient, designer: TalentProfile
) -> None:
    """The per-profile rule is checked first and keyed by the profile, so
    rotating the sender's address does not get round it -- it protects the
    person who would otherwise have to wade through the pile."""
    limit = 15
    for index in range(limit):
        response = client.post(
            f"/api/talent/{designer.slug}/requests",
            json={
                "customer_name": ar("service_request.customer"),
                "customer_phone": CUSTOMER_PHONE,
                "details": ar("service_request.details"),
            },
            headers={"X-Forwarded-For": f"203.0.113.{index}"},
        )
        assert response.status_code == 201, response.text

    flooded = client.post(
        f"/api/talent/{designer.slug}/requests",
        json={
            "customer_name": ar("service_request.customer"),
            "customer_phone": CUSTOMER_PHONE,
            "details": ar("service_request.second_details"),
        },
        headers={"X-Forwarded-For": "203.0.113.200"},
    )
    assert flooded.status_code == 429


def test_deleting_the_profile_takes_its_requests_with_it(
    client: TestClient, db: Session, designer: TalentProfile, provider_headers: dict[str, str]
) -> None:
    """A request only ever existed so one person could answer it. When that
    profile is gone there is nobody left with a reason to hold a stranger's
    phone number."""
    _ask(client, designer.slug)
    assert db.execute(select(ServiceRequest)).scalars().all() != []

    removed = client.delete("/api/my/talent", headers=provider_headers)
    assert removed.status_code == 200, removed.text
    db.expire_all()
    assert db.execute(select(ServiceRequest)).scalars().all() == []
