"""WhatsApp Cloud API OTP provider.

Delivery is exercised against a stubbed transport rather than Meta: the suite
must not need credentials or the network. What is worth pinning is the request
this provider builds, because a wrong component shape is rejected by Meta with
a message nobody reads until someone goes looking in the logs.
"""

from __future__ import annotations

import httpx
import pytest

from app.auth.otp import WhatsAppOtpProvider
from app.core.config import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "otp_provider": "whatsapp",
        "whatsapp_phone_number_id": "100000000000001",
        "whatsapp_access_token": "test-token",
        "whatsapp_template_name": "janoubona_code",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_incomplete_configuration_refuses_to_construct() -> None:
    with pytest.raises(RuntimeError, match="WHATSAPP_TEMPLATE_NAME"):
        WhatsAppOtpProvider(_settings(whatsapp_template_name=None))


def test_production_requires_complete_whatsapp_credentials() -> None:
    settings = Settings(
        app_env="production", secret_key="a-real-secret", otp_provider="whatsapp"
    )
    with pytest.raises(RuntimeError, match="WhatsApp"):
        settings.enforce_production_safety()


def test_the_request_names_the_template_and_carries_the_code(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("headers")
        return httpx.Response(
            200,
            json={"messages": [{"id": "wamid.TEST"}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    result = WhatsAppOtpProvider(_settings(whatsapp_template_locale="ar")).send(
        "+9613123456", "482913"
    )

    assert result.delivered is True
    assert result.provider == "whatsapp"
    assert result.provider_message_id == "wamid.TEST"

    assert captured["url"] == (
        "https://graph.facebook.com/v21.0/100000000000001/messages"
    )
    headers = captured["headers"]
    assert isinstance(headers, dict) and headers["Authorization"] == "Bearer test-token"

    body = captured["json"]
    assert isinstance(body, dict)
    assert body["messaging_product"] == "whatsapp"
    assert body["to"] == "+9613123456"
    assert body["template"]["name"] == "janoubona_code"
    # An Arabic template, or Arabic-speaking users read an English code message.
    assert body["template"]["language"] == {"code": "ar"}
    # The code twice: once for the sentence, once for the copy-code button.
    assert [component["type"] for component in body["template"]["components"]] == [
        "body",
        "button",
    ]
    assert all(
        component["parameters"][0]["text"] == "482913"
        for component in body["template"]["components"]
    )


def test_a_template_without_a_button_sends_only_the_body(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured["json"] = kwargs.get("json")
        return httpx.Response(
            200, json={"messages": [{"id": "x"}]}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    WhatsAppOtpProvider(_settings(whatsapp_template_has_button=False)).send("+9613123456", "1")

    body = captured["json"]
    assert isinstance(body, dict)
    assert [c["type"] for c in body["template"]["components"]] == ["body"]


def test_a_rejected_send_is_not_reported_as_delivered(monkeypatch, caplog) -> None:  # type: ignore[no-untyped-def]
    """Meta's explanation reaches the log, and the caller learns it failed."""

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(
            400,
            json={"error": {"message": "Template name does not exist", "code": 132001}},
            request=request,
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with caplog.at_level("ERROR"):
        result = WhatsAppOtpProvider(_settings()).send("+9613123456", "482913")

    assert result.delivered is False
    assert result.provider_message_id is None

    # Meta's reason rides on the record's `extra`, which is where the JSON
    # formatter this app deploys with puts it — asserting on the formatted
    # message instead would pass locally and tell us nothing about Railway.
    record = caplog.records[-1]
    assert record.provider_error and "Template name does not exist" in record.provider_error  # type: ignore[attr-defined]
    assert record.status_code == 400  # type: ignore[attr-defined]

    # The token must never reach a log line, formatted or structured.
    assert "test-token" not in caplog.text
    assert "test-token" not in str(record.__dict__)


def test_a_network_failure_is_not_reported_as_delivered(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(httpx, "post", fake_post)
    result = WhatsAppOtpProvider(_settings()).send("+9613123456", "482913")

    assert result.delivered is False


def test_the_provider_never_pins_a_code() -> None:
    """Only development adapters may return a fixed code."""
    assert WhatsAppOtpProvider(_settings()).fixed_code() is None
