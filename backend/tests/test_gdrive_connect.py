"""The admin panel's «Connect Google Drive» button (the owners' choice, 13 Nov 2026).

Google is simulated with ``httpx.MockTransport``. These pin who may connect,
that the round trip is bound to the manager who started it, that the refresh
token is never stored in the clear, and that the copy then signs in with it.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.admin import gdrive as gdrive_routes
from app.core.config import Settings, get_settings
from app.models.site_setting import SiteSetting
from app.models.user import User
from app.services import drive_replica, gdrive_oauth
from tests.conftest import admin_headers
from tests.test_permissions import _invite

REFRESH = "1//refresh-token-from-google"


@pytest.fixture
def configured(client: TestClient) -> Iterator[Settings]:
    settings = get_settings().model_copy(
        update={
            "gdrive_oauth_client_id": "client-id.apps.googleusercontent.com",
            "gdrive_oauth_client_secret": "client-secret",
            "public_base_url": "https://janoubona.example",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: settings  # type: ignore[attr-defined]
    yield settings
    client.app.dependency_overrides.pop(get_settings, None)  # type: ignore[attr-defined]


def _google(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.startswith(gdrive_oauth.TOKEN_URL):
        form = parse_qs(request.content.decode())
        if form["grant_type"] == ["authorization_code"]:
            assert form["code"] == ["the-code"]
            assert form["redirect_uri"] == [
                "https://janoubona.example/api/integrations/gdrive/callback"
            ]
            return httpx.Response(200, json={"access_token": "a1", "refresh_token": REFRESH})
        assert form["refresh_token"] == [REFRESH]
        return httpx.Response(200, json={"access_token": "a2", "expires_in": 3600})
    if url.startswith(gdrive_oauth.USERINFO_URL):
        return httpx.Response(200, json={"email": "admin@janoubona.net"})
    if url.startswith(gdrive_oauth.DRIVE_FILES) and request.method == "POST":
        assert json.loads(request.content)["name"] == gdrive_oauth.FOLDER_NAME
        return httpx.Response(200, json={"id": "backup-folder"})
    if url.startswith(gdrive_oauth.REVOKE_URL):
        return httpx.Response(200)
    raise AssertionError(f"unexpected {request.method} {url}")


@pytest.fixture
def fake_google(monkeypatch: pytest.MonkeyPatch) -> None:
    real = httpx.Client

    def client_factory(*args: object, **kwargs: object) -> httpx.Client:
        return real(transport=httpx.MockTransport(_google))

    monkeypatch.setattr(gdrive_routes.httpx, "Client", client_factory)


def _state_from(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == [gdrive_oauth.SCOPES]
    assert query["access_type"] == ["offline"]
    assert query["client_id"] == ["client-id.apps.googleusercontent.com"]
    return query["state"][0]


def test_a_manager_connects_and_the_token_is_stored_sealed(
    client: TestClient,
    db: Session,
    admin: User,
    configured: Settings,
    fake_google: None,
) -> None:
    manager = admin_headers(client)
    status = client.get("/api/admin/gdrive", headers=manager).json()
    assert status["available"] is True and status["connected"] is False

    started = client.post("/api/admin/gdrive/connect", headers=manager)
    assert started.status_code == 200, started.text
    state = _state_from(started.json()["url"])

    back = client.get(
        "/api/integrations/gdrive/callback",
        params={"code": "the-code", "state": state},
        follow_redirects=False,
    )
    assert back.status_code == 303
    assert back.headers["location"].endswith("/admin/site-settings?gdrive=connected")

    status = client.get("/api/admin/gdrive", headers=manager).json()
    assert status["connected"] is True
    assert status["email"] == "admin@janoubona.net"
    assert status["folder_url"].endswith("/folders/backup-folder")

    # Never in the clear: the table travels to Telegram and into every backup.
    db.expire_all()
    stored = db.get(SiteSetting, gdrive_oauth.CONNECTION_KEY)
    assert stored is not None and REFRESH not in stored.value

    # The copy signs in with it, through the refresh grant.
    with httpx.Client(transport=httpx.MockTransport(_google)) as google:
        drive = drive_replica.drive_from_settings(configured, google, db)
        assert drive is not None
        assert drive._headers() == {"Authorization": "Bearer a2"}

    disconnected = client.post("/api/admin/gdrive/disconnect", headers=manager)
    assert disconnected.json()["connected"] is False
    db.expire_all()
    assert db.get(SiteSetting, gdrive_oauth.CONNECTION_KEY) is None


def test_only_a_manager_starts_or_finishes_a_connection(
    client: TestClient, admin: User, configured: Settings, fake_google: None
) -> None:
    manager = admin_headers(client)
    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")
    assert client.post("/api/admin/gdrive/connect", headers=reviewer).status_code == 403
    assert client.post("/api/admin/gdrive/run", headers=reviewer).status_code == 403
    # Reading the card is fine for every role.
    assert client.get("/api/admin/gdrive", headers=reviewer).status_code == 200

    # A state that is not a manager's, or not ours at all, connects nothing.
    reviewer_id = client.get("/api/me", headers=reviewer).json()["id"]
    forged = gdrive_oauth.start_url(configured, uuid.UUID(reviewer_id))
    for state in (_state_from(forged), "not-a-state"):
        back = client.get(
            "/api/integrations/gdrive/callback",
            params={"code": "the-code", "state": state},
            follow_redirects=False,
        )
        assert back.headers["location"].endswith("?gdrive=error")
    assert client.get("/api/admin/gdrive", headers=manager).json()["connected"] is False


def test_the_button_says_so_when_the_server_has_no_google_client(
    client: TestClient, admin: User
) -> None:
    manager = admin_headers(client)
    assert client.get("/api/admin/gdrive", headers=manager).json()["available"] is False
    assert client.post("/api/admin/gdrive/connect", headers=manager).status_code == 409
