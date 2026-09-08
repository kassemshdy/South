from __future__ import annotations

import pytest

from south_mcp.client import ApiError, SouthClient
from south_mcp.config import ENV_BASE_URL, ENV_EMAIL, ENV_PASSWORD, ConfigError, load_config
from south_mcp.redaction import REDACTION_NOTE
from tests.stub_api import StubApi


@pytest.fixture
def stub() -> StubApi:
    return StubApi()


def client_for(stub: StubApi) -> SouthClient:
    return SouthClient(stub.config, transport=stub.transport)


def test_signs_in_once_and_reuses_the_token(stub: StubApi) -> None:
    stub.on("GET", "/api/admin/stats", {"total_businesses": 1})
    client = client_for(stub)

    client.get("/api/admin/stats")
    client.get("/api/admin/stats")

    assert stub.sign_ins == 1


def test_a_401_triggers_one_fresh_sign_in_and_a_retry(stub: StubApi) -> None:
    """A 14-day token outlives any agent run, so an expiry is rare enough that
    a single retry is the whole strategy -- but it must not surface as a tool
    failure the first time a routine runs after a fortnight."""
    stub.on("GET", "/api/admin/stats", {"total_businesses": 1})
    stub.expire_once.add("/api/admin/stats")
    client = client_for(stub)

    assert client.get("/api/admin/stats") == {"total_businesses": 1}
    assert stub.sign_ins == 2


def test_an_api_error_carries_the_application_message(stub: StubApi) -> None:
    client = client_for(stub)

    with pytest.raises(ApiError) as raised:
        client.get("/api/admin/nothing-here")

    assert raised.value.status == 404
    assert raised.value.code == "not_found"


def test_unset_filters_are_not_sent_as_the_string_none(stub: StubApi) -> None:
    """`?status=None` is a 422 from FastAPI, not an unfiltered list."""
    captured: list[str] = []
    stub.on("GET", "/api/admin/businesses", {"items": []})
    client = client_for(stub)
    client.sign_in()  # before the hook, so only the real call is captured
    client._http.event_hooks = {"request": [lambda r: captured.append(str(r.url))]}

    client.get("/api/admin/businesses", status=None, q="shop", page=1)

    assert "status" not in captured[0]
    assert "q=shop" in captured[0]


def test_every_response_is_redacted_on_the_way_out(stub: StubApi) -> None:
    stub.on(
        "GET",
        "/api/admin/businesses/b1",
        {"name": "A shop", "owner_identity": {"full_name": "A Person"}},
    )
    client = client_for(stub)

    assert client.get("/api/admin/businesses/b1")["owner_identity"] == REDACTION_NOTE


def test_the_server_refuses_to_start_without_credentials() -> None:
    with pytest.raises(ConfigError) as raised:
        load_config({ENV_BASE_URL: "http://api.test"})

    assert ENV_EMAIL in str(raised.value)
    assert ENV_PASSWORD in str(raised.value)


def test_a_trailing_slash_on_the_base_url_does_not_double_up() -> None:
    config = load_config(
        {ENV_BASE_URL: "http://api.test/", ENV_EMAIL: "a@b.c", ENV_PASSWORD: "x"}
    )

    assert config.base_url == "http://api.test"


def test_localhost_and_develop_are_not_treated_as_live() -> None:
    def config_for(url: str):
        return load_config({ENV_BASE_URL: url, ENV_EMAIL: "a@b.c", ENV_PASSWORD: "x"})

    assert config_for("http://localhost:8000").is_production is False
    assert config_for("https://api-develop.up.railway.app").is_production is False
    assert config_for("https://janoubona.up.railway.app").is_production is True
