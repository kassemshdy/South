"""Texting a shop owner through bestsmsbulk.com (the owners' request,
9 Nov 2026). No test talks to the provider: its HTTP API is stood in for."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.business import Business
from app.models.user import User
from app.services import sms
from tests.conftest import admin_headers
from tests.test_views import OWNER_PHONE, approved_business, owner_headers  # noqa: F401

SENT: list[dict[str, Any]] = []


def _provider(answer: dict[str, Any]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("getbalance.php"):
            return httpx.Response(200, text="125.50")
        assert request.url.path.endswith("sendSmsAPIJson.php")
        SENT.append(json.loads(request.content)[0])
        return httpx.Response(200, json=answer)

    return httpx.MockTransport(handle)


@pytest.fixture
def sms_on(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    configured = get_settings().model_copy(
        update={
            "bestsms_api_key": "key-1",
            "bestsms_api_secret": "secret-1",
            "bestsms_sender_id": "Janoubona",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: configured  # type: ignore[attr-defined]
    SENT.clear()
    yield
    client.app.dependency_overrides.pop(get_settings, None)  # type: ignore[attr-defined]


def _answering(monkeypatch: pytest.MonkeyPatch, answer: dict[str, Any]) -> None:
    real = httpx.Client
    monkeypatch.setattr(
        sms.httpx, "Client", lambda **kwargs: real(transport=_provider(answer))
    )


def test_without_keys_there_is_no_sms(
    client: TestClient,
    admin: User,
    approved_business: Business,  # noqa: F811
) -> None:
    headers = admin_headers(client)
    assert client.get("/api/admin/sms", headers=headers).json() == {
        "enabled": False,
        "balance": None,
    }
    refused = client.post(
        f"/api/admin/businesses/{approved_business.id}/sms",
        headers=headers,
        json={"message": "hello"},
    )
    assert refused.status_code == 503


def test_an_sms_goes_to_the_owner_s_account_number(
    client: TestClient,
    admin: User,
    approved_business: Business,  # noqa: F811
    sms_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _answering(
        monkeypatch,
        {
            "status": 201,
            "message": "Messages successfully queued",
            "data": [
                {
                    "status": 201,
                    "confirmationid": 110099887,
                    "recipient": "96103960001",
                    "numberofsmspermsg": 1,
                }
            ],
        },
    )
    headers = admin_headers(client)
    assert client.get("/api/admin/sms", headers=headers).json() == {
        "enabled": True,
        "balance": 125.5,
    }

    sent = client.post(
        f"/api/admin/businesses/{approved_business.id}/sms",
        headers=headers,
        json={"message": "hello"},
    )
    assert sent.status_code == 200, sent.text
    assert sent.json() == {"confirmation_id": "110099887", "parts": 1}
    form = SENT[-1]
    assert form["destination"] == "961" + OWNER_PHONE.lstrip("0")
    assert form["senderid"] == "Janoubona"
    assert form["api_key"] == "key-1" and form["message"] == "hello"


def test_the_provider_s_refusal_reaches_staff(
    client: TestClient,
    admin: User,
    approved_business: Business,  # noqa: F811
    sms_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _answering(monkeypatch, {"status": 300, "message": "No credits"})
    refused = client.post(
        f"/api/admin/businesses/{approved_business.id}/sms",
        headers=admin_headers(client),
        json={"message": "hello"},
    )
    assert refused.status_code == 502
    assert "No credits" in refused.text


def test_an_owner_cannot_send_sms(
    client: TestClient,
    approved_business: Business,  # noqa: F811
    owner_headers: dict[str, str],  # noqa: F811
) -> None:
    refused = client.post(
        f"/api/admin/businesses/{approved_business.id}/sms",
        headers=owner_headers,
        json={"message": "hello"},
    )
    assert refused.status_code == 403
