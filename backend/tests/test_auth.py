"""Authentication, OTP lifecycle and rate limiting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.phone import normalize_phone
from app.models.user import User
from app.repositories.user import UserRepository
from tests.conftest import sign_in


def test_phone_variants_resolve_to_one_account(client: TestClient, db: Session) -> None:
    """03123456, +961 3 123 456 and 0096131234... must be the same person."""
    sign_in(client, "03123456")
    sign_in(client, "+961 3 123 456")

    users = db.query(User).filter(User.phone_number == "+9613123456").all()
    assert len(users) == 1


def test_account_is_created_on_first_verification(client: TestClient, db: Session) -> None:
    assert UserRepository(db).get_by_phone("+9613555111") is None

    headers = sign_in(client, "03555111")
    me = client.get("/api/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["phone_number"] == "+9613555111"
    assert me.json()["role"] == "OWNER"


def test_invalid_phone_is_rejected(client: TestClient) -> None:
    response = client.post("/api/auth/request-otp", json={"phone_number": "123"})
    assert response.status_code == 422


def test_wrong_code_is_rejected(client: TestClient) -> None:
    client.post("/api/auth/request-otp", json={"phone_number": "03555222"})
    response = client.post(
        "/api/auth/verify-otp", json={"phone_number": "03555222", "code": "000000"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "otp_invalid"


def test_code_cannot_be_replayed(client: TestClient) -> None:
    request = client.post("/api/auth/request-otp", json={"phone_number": "03555333"})
    code = request.json()["debug_code"]

    first = client.post("/api/auth/verify-otp", json={"phone_number": "03555333", "code": code})
    second = client.post("/api/auth/verify-otp", json={"phone_number": "03555333", "code": code})

    assert first.status_code == 200
    assert second.status_code == 401


def test_otp_send_is_rate_limited(client: TestClient) -> None:
    """Three sends are allowed per phone; the fourth is refused."""
    for attempt in range(3):
        allowed = client.post("/api/auth/request-otp", json={"phone_number": "03555444"})
        assert allowed.status_code == 200, f"send #{attempt + 1} should be allowed"

    refused = client.post("/api/auth/request-otp", json={"phone_number": "03555444"})
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "rate_limited"
    assert int(refused.headers["retry-after"]) > 0


def test_verify_attempts_are_capped(client: TestClient) -> None:
    client.post("/api/auth/request-otp", json={"phone_number": "03555555"})

    for _ in range(5):
        client.post("/api/auth/verify-otp", json={"phone_number": "03555555", "code": "999999"})

    blocked = client.post(
        "/api/auth/verify-otp", json={"phone_number": "03555555", "code": "999999"}
    )
    assert blocked.status_code == 429


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


def test_owner_cannot_use_the_admin_login(client: TestClient, db: Session) -> None:
    sign_in(client, "03555666")
    response = client.post(
        "/api/auth/admin/login", json={"email": "owner@example.com", "password": "AdminPass!123"}
    )
    assert response.status_code == 401


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_bumping_token_version_revokes_existing_sessions(
    client: TestClient, db: Session
) -> None:
    headers = sign_in(client, "03555777")
    assert client.get("/api/me", headers=headers).status_code == 200

    user = UserRepository(db).get_by_phone("+9613555777")
    assert user is not None
    user.token_version += 1
    db.commit()

    revoked = client.get("/api/me", headers=headers)
    assert revoked.status_code == 401
    assert revoked.json()["error"]["code"] == "token_revoked"


def test_production_refuses_the_mock_otp_provider() -> None:
    """The development shortcut must be impossible to ship."""
    settings = Settings(
        app_env="production",
        secret_key="a-real-secret",
        otp_provider="mock",
        admin_email="admin@example.com",
    )
    with pytest.raises(RuntimeError, match="mock"):
        settings.enforce_production_safety()


def test_production_requires_a_real_secret_key() -> None:
    settings = Settings(
        app_env="production",
        secret_key="dev-insecure-secret-change-me",
        otp_provider="twilio",
        twilio_account_sid="sid",
        twilio_auth_token="token",
        twilio_from_number="+15550000000",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.enforce_production_safety()


def test_production_requires_complete_twilio_credentials() -> None:
    settings = Settings(app_env="production", secret_key="a-real-secret", otp_provider="twilio")
    with pytest.raises(RuntimeError, match="Twilio"):
        settings.enforce_production_safety()


def test_dev_fixed_code_is_ignored_outside_development() -> None:
    assert Settings(app_env="development", otp_dev_fixed_code="123456").dev_fixed_otp_code == "123456"
    assert Settings(app_env="production", otp_dev_fixed_code="123456").dev_fixed_otp_code is None


def test_phone_normalization() -> None:
    assert normalize_phone("03123456") == "+9613123456"
    assert normalize_phone("+961 3 123 456") == "+9613123456"
    assert normalize_phone("٧١٢٣٤٥٦٧") == "+96171234567"
