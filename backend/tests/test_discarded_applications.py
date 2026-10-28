"""Applications for a number that already has an account: kept, not acted on.

The public form still answers them exactly like any other and still creates
nothing on the existing account -- `test_registration.py` pins both. What
these tests add is the CEO's change: the application is no longer thrown
away, but set aside where only an administrator can read it, without the
ID scan, which is never stored against a number the applicant does not own.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import DiscardedApplication
from app.models.business import Business
from app.models.enums import ApplicationKind, BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.models.verification import OwnerVerificationDocument
from tests.conftest import admin_headers, sign_in
from tests.samples import ar
from tests.test_registration import (
    APPLICANT_PHONE,
    IDENTITY,
    PNG_BYTES,
    _business_payload,
    _owner,
    _register,
    skill,  # noqa: F401 -- the fixture, used by name
)


def _apply_twice(client: TestClient, db: Session, category: Category, location: Location) -> User:
    first = _register(client, "business", _business_payload(category, location))
    assert first.status_code == 202, first.text
    owner = _owner(db)
    assert owner is not None

    second = _register(
        client,
        "business",
        _business_payload(category, location),
        document=("id.png", PNG_BYTES, "image/png"),
    )
    # Answered exactly like the first: the form is not a way to ask which
    # numbers are registered.
    assert second.status_code == 202, second.text
    assert second.json() == first.json()
    return owner


def test_a_repeat_application_is_set_aside_rather_than_lost(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    owner = _apply_twice(client, db, category, location)

    row = db.execute(select(DiscardedApplication)).scalar_one()
    assert row.kind is ApplicationKind.BUSINESS
    assert row.existing_user_id == owner.id
    assert row.login_phone == owner.phone_number
    assert row.payload["business"]["name"] == ar("business.applicant")
    assert "captcha_token" not in row.payload

    # And still nothing on the existing account: one listing, not two.
    listings = db.execute(
        select(func.count()).select_from(Business).where(Business.owner_id == owner.id)
    ).scalar_one()
    assert listings == 1


def test_the_scan_sent_with_it_is_never_stored(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _apply_twice(client, db, category, location)
    documents = db.execute(select(func.count()).select_from(OwnerVerificationDocument)).scalar_one()
    assert documents == 0


def test_an_administrator_reads_them_and_can_dismiss_one(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    _apply_twice(client, db, category, location)
    headers = admin_headers(client)

    listed = client.get("/api/admin/discarded-applications", headers=headers)
    assert listed.status_code == 200, listed.text
    [entry] = listed.json()
    assert entry["kind"] == "BUSINESS"
    assert entry["payload"]["identity"]["full_name"] == ar("identity.full_name")

    dismissed = client.post(
        f"/api/admin/discarded-applications/{entry['id']}/dismiss", headers=headers
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["dismissed_at"] is not None

    # Gone from the working list, still there when asked for.
    assert client.get("/api/admin/discarded-applications", headers=headers).json() == []
    everything = client.get(
        "/api/admin/discarded-applications?include_dismissed=true", headers=headers
    ).json()
    assert [e["id"] for e in everything] == [entry["id"]]


def test_nobody_but_an_administrator_can_read_them(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """They carry an applicant's identity, so the boundary is the admin role."""
    _apply_twice(client, db, category, location)

    assert client.get("/api/admin/discarded-applications").status_code == 401

    owner_headers = sign_in(client, "03990001")
    assert (
        client.get("/api/admin/discarded-applications", headers=owner_headers).status_code == 403
    )


def test_a_first_application_is_not_set_aside(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    response = _register(client, "business", _business_payload(category, location))
    assert response.status_code == 202, response.text
    assert db.execute(select(func.count()).select_from(DiscardedApplication)).scalar_one() == 0


def _talent_payload(skill: TalentSkill, location: Location) -> dict:  # noqa: F811
    return {
        "login_phone": APPLICANT_PHONE,
        "identity": dict(IDENTITY),
        "talent": {
            "display_name": ar("talent.applicant"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
            "whatsapp": APPLICANT_PHONE,
            "years_experience": 3,
            "kind": "SERVICE",
            "work_mode": "BOTH",
        },
    }


def _only_entry(client: TestClient, headers: dict[str, str]) -> dict:
    [entry] = client.get("/api/admin/discarded-applications", headers=headers).json()
    return entry


def test_a_shop_after_a_services_profile_is_added_to_the_account_by_an_administrator(
    client: TestClient,
    db: Session,
    admin: User,
    skill: TalentSkill,  # noqa: F811
    category: Category,
    location: Location,
) -> None:
    """The case that prompted it: services first, then a shop on the same
    number. An administrator adds the shop to that account, pending review."""
    assert _register(client, "talent", _talent_payload(skill, location)).status_code == 202
    assert _register(client, "business", _business_payload(category, location)).status_code == 202
    owner = _owner(db)
    assert owner is not None
    headers = admin_headers(client)
    entry = _only_entry(client, headers)

    response = client.post(
        f"/api/admin/discarded-applications/{entry['id']}/attach", headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "BUSINESS"
    assert body["application"]["dismissed_at"] is not None

    business = db.get(Business, body["listing_id"])
    assert business is not None
    assert business.owner_id == owner.id
    assert business.status is BusinessStatus.PENDING_REVIEW
    assert client.get("/api/admin/discarded-applications", headers=headers).json() == []

    again = client.post(f"/api/admin/discarded-applications/{entry['id']}/attach", headers=headers)
    assert again.status_code == 409


def test_a_second_shop_is_added_beside_the_first(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    owner = _apply_twice(client, db, category, location)
    headers = admin_headers(client)
    entry = _only_entry(client, headers)

    response = client.post(
        f"/api/admin/discarded-applications/{entry['id']}/attach", headers=headers
    )
    assert response.status_code == 200, response.text
    listings = db.execute(
        select(func.count()).select_from(Business).where(Business.owner_id == owner.id)
    ).scalar_one()
    assert listings == 2


def test_a_second_services_profile_is_refused_and_the_application_kept(
    client: TestClient,
    db: Session,
    admin: User,
    skill: TalentSkill,  # noqa: F811
    location: Location,
) -> None:
    """An account holds one services profile, so a second cannot be added."""
    assert _register(client, "talent", _talent_payload(skill, location)).status_code == 202
    assert _register(client, "talent", _talent_payload(skill, location)).status_code == 202
    headers = admin_headers(client)
    entry = _only_entry(client, headers)

    response = client.post(
        f"/api/admin/discarded-applications/{entry['id']}/attach", headers=headers
    )
    assert response.status_code == 409
    assert db.execute(select(func.count()).select_from(TalentProfile)).scalar_one() == 1
    assert _only_entry(client, headers)["id"] == entry["id"]


def test_only_an_administrator_can_add_one(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _apply_twice(client, db, category, location)
    row = db.execute(select(DiscardedApplication)).scalar_one()
    path = f"/api/admin/discarded-applications/{row.id}/attach"

    assert client.post(path).status_code == 401
    assert client.post(path, headers=sign_in(client, "03990001")).status_code == 403

