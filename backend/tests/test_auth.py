"""Signing in: one form, two kinds of identifier, and what it refuses."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.phone import normalize_phone
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository
from tests.conftest import OWNER_PASSWORD, make_owner, sign_in
from tests.samples import ar


def test_phone_variants_all_reach_the_one_account(client: TestClient) -> None:
    """03123456, +961 3 123 456 and 00961… must be the same person.

    Asserted through the login route rather than by counting rows, because
    the route is where it matters: somebody who applied as "03 123 456" and
    types "+9613123456" three months later is the same person, and a sign-in
    that did not think so would look to them exactly like a wrong password.
    """
    owner = make_owner("03123456")

    for spelling in ("03123456", "+961 3 123 456", "00961 3 123 456", "3 123 456"):
        response = client.post(
            "/api/auth/login", json={"identifier": spelling, "password": OWNER_PASSWORD}
        )
        assert response.status_code == 200, f"{spelling}: {response.text}"
        assert response.json()["user"]["id"] == str(owner.id)


def test_signing_in_never_creates_an_account(client: TestClient, db: Session) -> None:
    """The only way onto this site is an administrator approving you.

    Signing in used to create the account it could not find, which is what a
    one-time code to your own phone can honestly mean. A password cannot mean
    it, and an account nobody audited is exactly what the review queue exists
    to prevent — so an unknown number is a failed sign-in and nothing else.
    """
    response = client.post(
        "/api/auth/login",
        json={"identifier": "03555111", "password": OWNER_PASSWORD},
    )

    assert response.status_code == 401
    assert UserRepository(db).get_by_phone("+9613555111") is None


def test_an_owner_signs_in_with_their_phone_number(client: TestClient) -> None:
    make_owner("03555111")

    headers = sign_in(client, "03555111")
    me = client.get("/api/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["phone_number"] == "+9613555111"
    assert me.json()["role"] == "OWNER"


def test_personal_phone_number_round_trips_and_is_never_public(client: TestClient) -> None:
    headers = sign_in(client, "03555222")

    updated = client.patch(
        "/api/me", json={"personal_phone_number": "03123456"}, headers=headers
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["personal_phone_number"] == "+9613123456"

    me = client.get("/api/me", headers=headers)
    assert me.json()["personal_phone_number"] == "+9613123456"

    # Clearing it explicitly (not "field not sent") must actually clear it.
    cleared = client.patch(
        "/api/me", json={"personal_phone_number": None}, headers=headers
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["personal_phone_number"] is None


def test_a_malformed_identifier_fails_like_a_wrong_password(client: TestClient) -> None:
    """Not a 422.

    "That is not a Lebanese phone number" and "wrong password" are different
    answers to the same question, and telling them apart is how somebody maps
    which numbers are worth guessing at. The client checks the shape before
    sending; the server just refuses.
    """
    make_owner("03555222")

    malformed = client.post(
        "/api/auth/login", json={"identifier": "123", "password": OWNER_PASSWORD}
    )
    wrong_password = client.post(
        "/api/auth/login", json={"identifier": "03555222", "password": "not-the-password"}
    )

    assert malformed.status_code == wrong_password.status_code == 401
    assert malformed.json()["error"] == wrong_password.json()["error"]


def test_an_account_with_no_password_yet_cannot_be_signed_into(
    client: TestClient, db: Session
) -> None:
    """The state every application sits in until an administrator acts."""
    user = User(phone_number=normalize_phone("03555333"), role=UserRole.OWNER)
    db.add(user)
    db.commit()

    response = client.post(
        "/api/auth/login", json={"identifier": "03555333", "password": ""}
    )
    assert response.status_code == 422, response.text

    response = client.post(
        "/api/auth/login", json={"identifier": "03555333", "password": "anything-at-all"}
    )
    assert response.status_code == 401


def test_an_administrator_signs_in_on_the_same_form(
    client: TestClient, admin: User
) -> None:
    """One form for everybody — the account's role decides what opens."""
    response = client.post(
        "/api/auth/login", json={"identifier": admin.email, "password": "AdminPass!123"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "ADMIN"


def test_the_email_is_matched_however_it_is_typed(
    client: TestClient, admin: User
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"identifier": f"  {admin.email.upper()}  ", "password": "AdminPass!123"},
    )
    assert response.status_code == 200, response.text


def test_a_disabled_account_cannot_sign_in(client: TestClient, db: Session) -> None:
    user = make_owner("03555444")
    db.query(User).filter(User.id == user.id).update({"is_active": False})
    db.commit()

    response = client.post(
        "/api/auth/login", json={"identifier": "03555444", "password": OWNER_PASSWORD}
    )
    assert response.status_code == 401


def test_guessing_is_capped_per_identifier(client: TestClient) -> None:
    """The whole of the protection, now that a password is the only factor."""
    make_owner("03555555")
    limit = get_settings().password_login_limit

    for _ in range(limit):
        refused = client.post(
            "/api/auth/login", json={"identifier": "03555555", "password": "wrong"}
        )
        assert refused.status_code == 401

    capped = client.post(
        "/api/auth/login", json={"identifier": "03555555", "password": "wrong"}
    )
    assert capped.status_code == 429

    # And the cap holds even once the right password is offered, or it would
    # only be slowing an attacker down until they arrived at it.
    correct = client.post(
        "/api/auth/login", json={"identifier": "03555555", "password": OWNER_PASSWORD}
    )
    assert correct.status_code == 429


def test_a_successful_sign_in_spends_nothing(client: TestClient) -> None:
    make_owner("03555666")
    limit = get_settings().password_login_limit

    for _ in range(limit + 2):
        ok = client.post(
            "/api/auth/login",
            json={"identifier": "03555666", "password": OWNER_PASSWORD},
        )
        assert ok.status_code == 200, ok.text


def test_admin_login_requires_correct_password(client: TestClient, admin: User) -> None:
    ok = client.post(
        "/api/auth/admin/login", json={"email": admin.email, "password": "AdminPass!123"}
    )
    bad = client.post(
        "/api/auth/admin/login", json={"email": admin.email, "password": "wrong-password"}
    )

    assert ok.status_code == 200
    assert ok.json()["user"]["role"] == "ADMIN"
    assert bad.status_code == 401


def test_admin_login_does_not_reveal_whether_the_email_exists(
    client: TestClient, admin: User
) -> None:
    unknown = client.post(
        "/api/auth/admin/login", json={"email": "nobody@example.com", "password": "AdminPass!123"}
    )
    wrong_password = client.post(
        "/api/auth/admin/login", json={"email": admin.email, "password": "wrong-password"}
    )

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["error"] == wrong_password.json()["error"]


def test_the_admin_door_still_refuses_an_owner(client: TestClient, db: Session) -> None:
    """/auth/login takes everybody; /auth/admin/login takes administrators.

    It is the unlinked way back in when the main form is broken, so what it
    accepts stays narrow.
    """
    owner = make_owner("03555777", email="owner@example.com")
    assert owner.email == "owner@example.com"

    response = client.post(
        "/api/auth/admin/login",
        json={"email": "owner@example.com", "password": OWNER_PASSWORD},
    )
    assert response.status_code == 401


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_bumping_token_version_revokes_existing_sessions(
    client: TestClient, db: Session
) -> None:
    make_owner("03555888")
    headers = sign_in(client, "03555888")
    assert client.get("/api/me", headers=headers).status_code == 200

    user = UserRepository(db).get_by_phone("+9613555888")
    assert user is not None
    user.token_version += 1
    db.commit()

    revoked = client.get("/api/me", headers=headers)
    assert revoked.status_code == 401
    assert revoked.json()["error"]["code"] == "token_revoked"


def test_production_requires_a_real_secret_key() -> None:
    settings = Settings(
        app_env="production",
        secret_key="dev-insecure-secret-change-me",
        admin_email="admin@example.com",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.enforce_production_safety()


def test_production_refuses_a_seeded_owner_password() -> None:
    """The demo accounts' password is in this repository. So it is a shortcut.

    Staging may set it, because a deployed build has to be signed into before
    anybody has issued credentials by hand. Production may not, for the same
    reason the fixed OTP code was never allowed there.
    """
    settings = Settings(
        app_env="production",
        secret_key="a-real-secret",
        seed_owner_password="demo-password",
    )
    with pytest.raises(RuntimeError, match="SEED_OWNER_PASSWORD"):
        settings.enforce_production_safety()

    staging = Settings(
        app_env="staging",
        secret_key="a-real-secret",
        seed_owner_password="demo-password",
    )
    staging.enforce_production_safety()


def test_nothing_answers_the_old_otp_routes(client: TestClient) -> None:
    """A removal, not a disabling.

    Leaving them mounted with the development provider behind them is an
    authentication bypass for anyone who knows a phone number, which is how
    this got removed rather than switched off.
    """
    assert client.post("/api/auth/request-otp", json={"phone_number": "03555999"}).status_code == 404
    assert (
        client.post(
            "/api/auth/verify-otp", json={"phone_number": "03555999", "code": "123456"}
        ).status_code
        == 404
    )


def test_phone_normalization() -> None:
    assert normalize_phone("03123456") == "+9613123456"
    assert normalize_phone("+961 3 123 456") == "+9613123456"
    assert normalize_phone(ar("phone.arabic_indic")) == "+96171234567"
