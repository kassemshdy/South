"""Applying for a listing without an account, and being let in afterwards.

This is the route onto the site that does not need an SMS or WhatsApp
gateway, so it is the only one that currently works: a visitor applies, an
administrator audits the application, and on approval the administrator issues
a password and relays it themselves. What is pinned here is the handful of
ways that arrangement could quietly betray somebody:

- an application must not be signable-into **before** anyone has looked at it;
- the form must not become a way to ask **which numbers already have
  accounts**, nor to hang a listing inside a stranger's dashboard;
- a password that travelled through a chat message must open the account
  **once** -- everything else stays shut until it is replaced, and replacing it
  ends every session opened with it;
- the plaintext must exist in that one response and **nowhere else**.
"""

from __future__ import annotations

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_password
from app.models.business import Business
from app.models.enums import BusinessStatus, UserRole
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers
from tests.samples import ar

APPLICANT_PHONE = "03970001"
APPLICANT_E164 = "+9613970001"
OTHER_PHONE = "03970002"


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


#: Who the applicant says they are. Required on the public form now: the
#: reviewer is deciding whether this is a real person from the South, and
#: without these they would have to ask over WhatsApp before they could.
IDENTITY: dict[str, object] = {
    "full_name": ar("identity.full_name"),
    "birth_year": 1986,
    "registration_place": ar("identity.registration_place"),
    "residence_place": ar("identity.residence_place"),
}


def _business_payload(
    category: Category, location: Location, *, phone: str = APPLICANT_PHONE
) -> dict[str, object]:
    return {
        "login_phone": phone,
        "identity": dict(IDENTITY),
        "business": {
            "name": ar("business.applicant"),
            "description": ar("business.applicant_description"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "phone": phone,
        },
    }


def _apply(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post("/api/register/business", json=payload)
    assert response.status_code == 202, response.text


def _owner(db: Session, phone: str = APPLICANT_E164) -> User | None:
    return db.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()


# --- The application ------------------------------------------------------


def test_an_application_creates_a_pending_listing_nobody_can_sign_into(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """The account exists so approval has nothing to migrate; it has no
    password, which is what makes creating it before review safe."""
    _apply(client, _business_payload(category, location))

    owner = _owner(db)
    assert owner is not None
    assert owner.role is UserRole.OWNER
    assert owner.password_hash is None
    assert owner.must_change_password is False

    business = db.execute(
        select(Business).where(Business.owner_id == owner.id)
    ).scalar_one()
    assert business.status is BusinessStatus.PENDING_REVIEW
    assert business.name == ar("business.applicant")

    # No password means no way in, however the login route is asked.
    refused = client.post(
        "/api/auth/login", json={"identifier": APPLICANT_PHONE, "password": ""}
    )
    assert refused.status_code in (401, 422)


def test_a_pending_application_is_invisible_to_the_public(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _apply(client, _business_payload(category, location))
    business = db.execute(select(Business)).scalar_one()

    assert client.get(f"/api/businesses/{business.slug}").status_code == 404
    listed = client.get("/api/businesses", params={"q": ar("business.applicant")})
    assert listed.json()["items"] == []


def test_the_applicants_identity_lands_on_their_account(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """On the ``users`` row, which is where identity lives everywhere else.

    One account holds one legal name however many businesses it owns, so the
    application writes it there rather than onto the listing — and the field
    an administrator later reads on the review screen is the same one the
    account page edits.
    """
    _apply(client, _business_payload(category, location))

    owner = _owner(db)
    assert owner is not None
    assert owner.full_name == ar("identity.full_name")
    assert owner.birth_year == 1986
    assert owner.registration_place == ar("identity.registration_place")
    assert owner.residence_place == ar("identity.residence_place")


def test_an_application_without_an_identity_is_refused(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    payload = _business_payload(category, location)
    del payload["identity"]

    response = client.post("/api/register/business", json=payload)

    assert response.status_code == 422
    assert _owner(db) is None


def test_the_identity_never_reaches_the_public_listing(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    """The boundary `tests/test_identity.py` pins, from this direction.

    An application is stored as the listing itself, so it is worth asserting
    here too that collecting identity on a public form did not put it on a
    public payload.
    """
    _apply(client, _business_payload(category, location))
    business = db.execute(select(Business)).scalar_one()

    business.status = BusinessStatus.APPROVED
    db.commit()

    public = client.get(f"/api/businesses/{business.slug}")
    assert public.status_code == 200, public.text
    assert ar("identity.full_name") not in public.text
    assert ar("identity.registration_place") not in public.text

    # The reviewer, who needs it, still reads it through the identity block.
    review = client.get(
        f"/api/admin/businesses/{business.id}", headers=admin_headers(client)
    )
    assert review.status_code == 200, review.text
    assert review.json()["owner_identity"]["full_name"] == ar("identity.full_name")


def test_a_talent_application_lands_in_the_review_queue(
    client: TestClient,
    db: Session,
    skill: TalentSkill,
    location: Location,
    admin: User,
) -> None:
    response = client.post(
        "/api/register/talent",
        json={
            "login_phone": APPLICANT_PHONE,
            "identity": dict(IDENTITY),
            "talent": {
                "display_name": ar("talent.applicant"),
                "skill_id": str(skill.id),
                "location_id": str(location.id),
                "whatsapp": APPLICANT_PHONE,
            },
        },
    )
    assert response.status_code == 202, response.text

    profile = db.execute(select(TalentProfile)).scalar_one()
    assert profile.status is BusinessStatus.PENDING_REVIEW

    # The administrator sees it in the queue they already use.
    queue = client.get(
        "/api/admin/talent",
        params={"status": "PENDING_REVIEW"},
        headers=admin_headers(client),
    )
    assert queue.status_code == 200, queue.text
    assert [item["display_name"] for item in queue.json()["items"]] == [
        ar("talent.applicant")
    ]


def test_the_response_says_only_that_the_application_arrived(
    client: TestClient, category: Category, location: Location
) -> None:
    """No id and no status: an applicant has nothing to do with either, and
    returning them would make this endpoint answerable."""
    body = client.post(
        "/api/register/business", json=_business_payload(category, location)
    ).json()
    assert set(body) == {"message"}


# --- A number that already has an account ---------------------------------


def test_a_known_number_is_answered_identically_and_creates_nothing(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """The form must not be usable to ask whether a number is registered, and
    must not hang a second listing inside a stranger's dashboard."""
    first = client.post(
        "/api/register/business", json=_business_payload(category, location)
    )
    owner = _owner(db)
    assert owner is not None

    second = client.post(
        "/api/register/business",
        json={
            "login_phone": APPLICANT_PHONE,
            "business": {
                "name": ar("business.applicant_second"),
                "category_id": str(category.id),
                "location_id": str(location.id),
            },
        },
    )

    assert second.status_code == first.status_code
    assert second.json() == first.json()
    assert db.execute(select(Business)).scalars().all() == [
        db.execute(select(Business).where(Business.owner_id == owner.id)).scalar_one()
    ]


def test_a_number_written_differently_is_still_the_same_account(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """Normalised to E.164 on the way in, so the second spelling is caught by
    the duplicate rule above rather than creating a twin."""
    _apply(client, _business_payload(category, location))
    _apply(client, _business_payload(category, location, phone=APPLICANT_E164))

    assert len(db.execute(select(User)).scalars().all()) == 1
    assert len(db.execute(select(Business)).scalars().all()) == 1


# --- Rate limiting and captcha --------------------------------------------


def test_the_per_address_rate_limit_bites(
    client: TestClient, category: Category, location: Location
) -> None:
    settings = get_settings()
    for index in range(settings.registration_per_ip_limit):
        payload = _business_payload(category, location, phone=f"0397100{index}")
        assert client.post("/api/register/business", json=payload).status_code == 202

    refused = client.post(
        "/api/register/business",
        json=_business_payload(category, location, phone="03971099"),
    )
    assert refused.status_code == 429
    assert "Retry-After" in refused.headers


def test_no_captcha_is_required_while_turnstile_is_unconfigured(
    client: TestClient, category: Category, location: Location
) -> None:
    """The rule AGENTS.md states for every optional integration: unset means
    inert, so the test suite and local development never touch the network."""
    assert get_settings().turnstile_secret_key is None
    payload = _business_payload(category, location)
    assert "captcha_token" not in payload
    assert client.post("/api/register/business", json=payload).status_code == 202


def test_a_configured_captcha_refuses_a_submission_with_no_token(
    client: TestClient,
    category: Category,
    location: Location,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")

    refused = client.post(
        "/api/register/business", json=_business_payload(category, location)
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "captcha_required"


def test_a_captcha_cloudflare_rejects_refuses_the_submission(
    client: TestClient,
    category: Category,
    location: Location,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import captcha as captcha_module

    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    monkeypatch.setattr(
        captcha_module.httpx,
        "post",
        lambda *args, **kwargs: _FakeResponse({"success": False}),
    )

    payload = _business_payload(category, location) | {"captcha_token": "forged"}
    refused = client.post("/api/register/business", json=payload)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "captcha_failed"


def test_a_captcha_that_cannot_be_checked_refuses_rather_than_admits(
    client: TestClient,
    category: Category,
    location: Location,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloudflare being unreachable closes the form. The alternative is a form
    that stops being protected exactly when someone is attacking it."""
    import httpx

    from app.core import captcha as captcha_module

    def _explode(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    monkeypatch.setattr(captcha_module.httpx, "post", _explode)

    payload = _business_payload(category, location) | {"captcha_token": "anything"}
    refused = client.post("/api/register/business", json=payload)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "captcha_unavailable"


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


# --- Issuing credentials ---------------------------------------------------


def _issue(client: TestClient, user: User) -> str:
    response = client.post(
        f"/api/admin/users/{user.id}/credentials", headers=admin_headers(client)
    )
    assert response.status_code == 200, response.text
    return str(response.json()["password"])


def test_an_issued_password_is_returned_once_and_stored_only_as_a_hash(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None

    password = _issue(client, owner)
    db.refresh(owner)

    assert owner.password_hash is not None
    assert password not in owner.password_hash
    assert verify_password(password, owner.password_hash)
    assert owner.must_change_password is True

    # There is no route that reads it back; a second call replaces it.
    again = _issue(client, owner)
    assert again != password
    db.refresh(owner)
    assert not verify_password(password, owner.password_hash)


def test_the_issued_password_reaches_no_log_record(
    client: TestClient,
    db: Session,
    category: Category,
    location: Location,
    admin: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None

    with caplog.at_level(logging.DEBUG):
        password = _issue(client, owner)

    assert caplog.records
    assert not any(password in record.getMessage() for record in caplog.records)


def test_issuing_credentials_is_administrators_only(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None

    assert client.post(f"/api/admin/users/{owner.id}/credentials").status_code == 401


def test_credentials_are_refused_for_an_administrator_account(
    client: TestClient, admin: User
) -> None:
    """An admin password is not something another admin hands out, and the
    account it is issued to has to be one that signs in at /auth/login."""
    refused = client.post(
        f"/api/admin/users/{admin.id}/credentials", headers=admin_headers(client)
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "admin_account"


def test_credentials_for_an_unknown_account_are_not_found(
    client: TestClient, admin: User
) -> None:
    missing = client.post(
        f"/api/admin/users/{uuid.uuid4()}/credentials", headers=admin_headers(client)
    )
    assert missing.status_code == 404


# --- Signing in and the forced change --------------------------------------


def _sign_in(client: TestClient, phone: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"identifier": phone, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_the_owner_signs_in_with_the_phone_number_and_the_issued_password(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    password = _issue(client, owner)

    body = client.post(
        "/api/auth/login", json={"identifier": APPLICANT_PHONE, "password": password}
    ).json()
    assert body["user"]["must_change_password"] is True


@pytest.mark.parametrize(
    ("phone", "password"),
    [
        (APPLICANT_PHONE, "wrong-password"),
        (OTHER_PHONE, "wrong-password"),
    ],
)
def test_a_failed_sign_in_says_the_same_thing_either_way(
    client: TestClient,
    db: Session,
    category: Category,
    location: Location,
    admin: User,
    phone: str,
    password: str,
) -> None:
    """One error for a wrong password and for a number with no account, so the
    route cannot be used to enumerate who is registered."""
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    _issue(client, owner)

    refused = client.post(
        "/api/auth/login", json={"identifier": phone, "password": password}
    )
    assert refused.status_code == 401
    assert refused.json()["error"]["code"] == "invalid_credentials"


def test_the_guess_budget_for_one_number_runs_out(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    """Password sign-in has no expiring code behind it, so the only thing
    between a guessable password and an account is how many guesses fit in the
    window."""
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    password = _issue(client, owner)

    limit = get_settings().password_login_limit
    for _ in range(limit):
        attempt = client.post(
            "/api/auth/login",
            json={"identifier": APPLICANT_PHONE, "password": "wrong-password"},
        )
        assert attempt.status_code == 401

    refused = client.post(
        "/api/auth/login", json={"identifier": APPLICANT_PHONE, "password": password}
    )
    assert refused.status_code == 429
    assert "Retry-After" in refused.headers

    # Another number is unaffected: the budget is per phone number, so one
    # host cannot lock everybody out by guessing at one account.
    other = client.post(
        "/api/auth/login", json={"identifier": OTHER_PHONE, "password": "anything"}
    )
    assert other.status_code == 401


def test_the_guess_budget_counts_numbers_with_no_account_too(
    client: TestClient, admin: User
) -> None:
    """Counting only real accounts would make the difference measurable."""
    limit = get_settings().password_login_limit
    for _ in range(limit):
        assert (
            client.post(
                "/api/auth/login",
                json={"identifier": OTHER_PHONE, "password": "wrong-password"},
            ).status_code
            == 401
        )

    refused = client.post(
        "/api/auth/login", json={"identifier": OTHER_PHONE, "password": "wrong"}
    )
    assert refused.status_code == 429


def test_an_administrator_cannot_sign_in_on_the_owner_route(
    client: TestClient, db: Session, admin: User
) -> None:
    """Keeping the two forms apart is what stops a leaked owner password from
    ever reaching the admin panel."""
    admin.phone_number = APPLICANT_E164
    from app.core.security import hash_password

    admin.password_hash = hash_password("AdminPass!123")
    db.commit()

    refused = client.post(
        "/api/auth/login",
        json={"identifier": APPLICANT_PHONE, "password": "AdminPass!123"},
    )
    assert refused.status_code == 401


def test_every_owner_route_is_shut_until_the_password_is_replaced(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    headers = _sign_in(client, APPLICANT_PHONE, _issue(client, owner))

    blocked = client.get("/api/my/businesses", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"

    # Except the two the client needs to get out of that state.
    assert client.get("/api/me", headers=headers).status_code == 200


def test_changing_the_password_unblocks_the_account_and_ends_the_session(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    """The point of the forced change: whoever else read that WhatsApp chat is
    signed out the moment the owner picks their own password."""
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    issued = _issue(client, owner)
    headers = _sign_in(client, APPLICANT_PHONE, issued)

    changed = client.post(
        "/api/me/password",
        headers=headers,
        json={"current_password": issued, "new_password": "OwnerChosen9"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False

    assert client.get("/api/me", headers=headers).status_code == 401

    fresh = _sign_in(client, APPLICANT_PHONE, "OwnerChosen9")
    listed = client.get("/api/my/businesses", headers=fresh)
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == [ar("business.applicant")]


def test_the_current_password_is_required_to_replace_it(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    """A borrowed unlocked phone must not be able to take the account over."""
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    headers = _sign_in(client, APPLICANT_PHONE, _issue(client, owner))

    refused = client.post(
        "/api/me/password",
        headers=headers,
        json={"current_password": "not-it", "new_password": "OwnerChosen9"},
    )
    assert refused.status_code == 401
    assert client.get("/api/my/businesses", headers=headers).status_code == 403


def test_an_issued_password_ends_any_session_opened_with_the_previous_one(
    client: TestClient, db: Session, category: Category, location: Location, admin: User
) -> None:
    _apply(client, _business_payload(category, location))
    owner = _owner(db)
    assert owner is not None
    headers = _sign_in(client, APPLICANT_PHONE, _issue(client, owner))

    _issue(client, owner)
    assert client.get("/api/me", headers=headers).status_code == 401
