"""Sign-up and password reset by SMS code (the owners' decision, 9 Nov
2026). The SMS provider is stood in for; every code is read from what
would have been sent."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import PhoneCode
from app.models.user import User
from app.services import sms
from tests.conftest import admin_headers

SENT: list[dict[str, Any]] = []
MOBILE = "71 123 456"
MOBILE_E164 = "+96171123456"


def _provider() -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)[0]
        SENT.append(body)
        return httpx.Response(
            200,
            json={
                "status": 201,
                "data": [{"status": 201, "confirmationid": 1, "numberofsmspermsg": 1}],
            },
        )

    return httpx.MockTransport(handle)


@pytest.fixture
def sms_signup(
    client: TestClient, admin: User, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, str]]:
    configured = get_settings().model_copy(
        update={
            "bestsms_api_key": "key-1",
            "bestsms_api_secret": "secret-1",
            "bestsms_sender_id": "Janoubona",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: configured  # type: ignore[attr-defined]
    real = httpx.Client
    monkeypatch.setattr(sms.httpx, "Client", lambda **kwargs: real(transport=_provider()))
    SENT.clear()
    headers = admin_headers(client)
    switched = client.put(
        "/api/admin/site-settings/sms-signup",
        headers=headers,
        json={"enabled": True, "daily_cap": 300},
    )
    assert switched.status_code == 200, switched.text
    yield headers
    client.app.dependency_overrides.pop(get_settings, None)  # type: ignore[attr-defined]


def _last_code() -> str:
    match = re.search(r"\d{6}", SENT[-1]["message"])
    assert match, SENT[-1]
    return match.group(0)


def _age_codes(db: Session) -> None:
    """Move every code past the resend wait."""
    db.execute(
        update(PhoneCode).values(created_at=datetime.now(UTC) - timedelta(minutes=2))
    )
    db.commit()


def test_off_until_an_administrator_switches_it_on(client: TestClient) -> None:
    assert client.get("/api/auth/phone/config").json() == {"enabled": False}
    refused = client.post("/api/auth/phone/code", json={"phone": MOBILE})
    assert refused.status_code == 503


def test_a_code_opens_an_account_and_signs_in(
    client: TestClient, sms_signup: dict[str, str]
) -> None:
    assert client.get("/api/auth/phone/config").json() == {"enabled": True}
    sent = client.post("/api/auth/phone/code", json={"phone": MOBILE})
    assert sent.status_code == 202, sent.text
    assert SENT[-1]["destination"] == "96171123456"
    assert SENT[-1]["senderid"] == "Janoubona"
    code = _last_code()

    wrong = "000000" if code != "000000" else "111111"
    assert client.post(
        "/api/auth/phone/check", json={"phone": MOBILE, "code": wrong}
    ).status_code == 422
    assert client.post(
        "/api/auth/phone/check", json={"phone": MOBILE, "code": code}
    ).status_code == 200

    done = client.post(
        "/api/auth/phone/complete",
        json={"phone": MOBILE, "code": code, "password": "NewPass!2026"},
    )
    assert done.status_code == 200, done.text
    assert done.json()["user"]["role"] == "OWNER"
    assert done.json()["user"]["phone_number"] == MOBILE_E164

    login = client.post(
        "/api/auth/login", json={"identifier": MOBILE, "password": "NewPass!2026"}
    )
    assert login.status_code == 200
    # Used up: the same code cannot set a password twice.
    again = client.post(
        "/api/auth/phone/complete",
        json={"phone": MOBILE, "code": code, "password": "Other!Pass2026"},
    )
    assert again.status_code == 422


def test_a_code_replaces_a_forgotten_password(
    client: TestClient, db: Session, sms_signup: dict[str, str]
) -> None:
    client.post("/api/auth/phone/code", json={"phone": MOBILE})
    client.post(
        "/api/auth/phone/complete",
        json={"phone": MOBILE, "code": _last_code(), "password": "FirstPass!2026"},
    )
    _age_codes(db)

    assert client.post("/api/auth/phone/code", json={"phone": MOBILE}).status_code == 202
    reset = client.post(
        "/api/auth/phone/complete",
        json={"phone": MOBILE, "code": _last_code(), "password": "SecondPass!2026"},
    )
    assert reset.status_code == 200
    assert client.post(
        "/api/auth/login", json={"identifier": MOBILE, "password": "FirstPass!2026"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"identifier": MOBILE, "password": "SecondPass!2026"}
    ).status_code == 200


def test_wrong_guesses_kill_the_code(
    client: TestClient, sms_signup: dict[str, str]
) -> None:
    client.post("/api/auth/phone/code", json={"phone": MOBILE})
    code = _last_code()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        client.post("/api/auth/phone/check", json={"phone": MOBILE, "code": wrong})
    late = client.post("/api/auth/phone/check", json={"phone": MOBILE, "code": code})
    assert late.status_code == 422
    assert late.json()["error"]["code"] == "code_expired"


def test_resend_waits_a_minute(client: TestClient, sms_signup: dict[str, str]) -> None:
    assert client.post("/api/auth/phone/code", json={"phone": MOBILE}).status_code == 202
    assert client.post("/api/auth/phone/code", json={"phone": MOBILE}).status_code == 429
    assert len(SENT) == 1


def test_landlines_are_refused(client: TestClient, sms_signup: dict[str, str]) -> None:
    refused = client.post("/api/auth/phone/code", json={"phone": "01 123 456"})
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "not_mobile"
    assert SENT == []


def test_staff_numbers_get_no_code_and_the_same_answer(
    client: TestClient, db: Session, admin: User, sms_signup: dict[str, str]
) -> None:
    admin.phone_number = MOBILE_E164
    db.commit()
    answer = client.post("/api/auth/phone/code", json={"phone": MOBILE})
    assert answer.status_code == 202
    assert SENT == []


def test_the_daily_cap_stops_sending(
    client: TestClient, sms_signup: dict[str, str]
) -> None:
    client.put(
        "/api/admin/site-settings/sms-signup",
        headers=sms_signup,
        json={"enabled": True, "daily_cap": 1},
    )
    assert client.post("/api/auth/phone/code", json={"phone": "71 000 001"}).status_code == 202
    assert client.post("/api/auth/phone/code", json={"phone": "71 000 002"}).status_code == 429
    settings = client.get("/api/admin/site-settings/sms-signup", headers=sms_signup).json()
    assert settings["sent_today"] == 1 and settings["daily_cap"] == 1
    assert settings["sms_configured"] is True


def test_no_code_is_stored_in_the_clear(
    client: TestClient, db: Session, sms_signup: dict[str, str]
) -> None:
    client.post("/api/auth/phone/code", json={"phone": MOBILE})
    row = db.query(PhoneCode).one()
    assert _last_code() not in row.code_hash
