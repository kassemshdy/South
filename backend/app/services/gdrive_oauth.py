"""Connecting the Google Drive copy from the admin panel (the owners' choice, 13 Nov 2026).

A manager presses «Connect Google Drive» at /admin/site-settings, signs in to
Google as the account that should hold the copy (admin@janoubona.net) and
allows it. Google sends them back to ``/api/integrations/gdrive/callback``
with a one-time code, which is exchanged here for a refresh token; the copy
(``drive_replica``) then signs in with that token on every run.

Three things keep this narrow:

- **Scope ``drive.file`` only.** The site can see and change the files it
  created itself -- the "Janoubona backup" folder made here at connect time
  and everything put in it -- and nothing else in that Google Drive.
- **The refresh token is stored encrypted** in ``site_settings`` (a key
  derived from ``SECRET_KEY``), because that table travels: the whole
  database goes to the Telegram chat every 3 hours and into every backup,
  this Drive folder included. A changed ``SECRET_KEY`` makes it unreadable,
  which shows as "not connected" until someone connects again.
- **The ``state`` sent through Google is a signed, 10-minute token naming
  the manager** who started it, checked again on the way back -- the
  callback has no session of its own (it is a browser redirect).

Inert without ``GDRIVE_OAUTH_CLIENT_ID`` and ``GDRIVE_OAUTH_CLIENT_SECRET``
(an OAuth client of type "Web application" in Google Cloud, whose authorised
redirect URI is ``<PUBLIC_BASE_URL>/api/integrations/gdrive/callback``).
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.site_setting import SiteSetting

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
SCOPES = "openid email https://www.googleapis.com/auth/drive.file"
FOLDER_NAME = "Janoubona backup"
CALLBACK_PATH = "/api/integrations/gdrive/callback"

#: ``site_settings`` rows. Neither is in ``SITE_SETTING_KEYS``, so neither is
#: ever served to the public site.
CONNECTION_KEY = "gdrive:connection"
LAST_RUN_KEY = "gdrive:last_run"

_STATE_PURPOSE = "gdrive-connect"
_STATE_SECONDS = 600


@dataclass
class Connection:
    refresh_token: str
    email: str
    folder_id: str
    connected_at: str


def available(settings: Settings) -> bool:
    return bool(settings.gdrive_oauth_client_id and settings.gdrive_oauth_client_secret)


def redirect_uri(settings: Settings) -> str:
    return settings.public_base_url.rstrip("/") + CALLBACK_PATH


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(b"gdrive-connection:" + settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


# --- the round trip through Google -----------------------------------------


def start_url(settings: Settings, admin_id: uuid.UUID) -> str:
    """Where the manager's browser goes to sign in to Google and allow the copy."""
    now = int(time.time())
    state = jwt.encode(
        {"sub": str(admin_id), "purpose": _STATE_PURPOSE, "iat": now, "exp": now + _STATE_SECONDS},
        settings.secret_key,
        algorithm="HS256",
    )
    query = {
        "client_id": settings.gdrive_oauth_client_id,
        "redirect_uri": redirect_uri(settings),
        "response_type": "code",
        "scope": SCOPES,
        # A refresh token, every time: without consent Google sends one only
        # on the first connection, and a reconnect would come back without it.
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(query)}"


def read_state(settings: Settings, state: str) -> uuid.UUID | None:
    """The manager who started the connection, or None for a bad or old state."""
    try:
        claims = jwt.decode(state, settings.secret_key, algorithms=["HS256"])
        if claims.get("purpose") != _STATE_PURPOSE:
            return None
        return uuid.UUID(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def finish(db: Session, settings: Settings, code: str, client: httpx.Client) -> Connection:
    """Exchange Google's code, make the backup folder, and keep the connection."""
    tokens = client.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.gdrive_oauth_client_id,
            "client_secret": settings.gdrive_oauth_client_secret,
            "redirect_uri": redirect_uri(settings),
            "grant_type": "authorization_code",
        },
    )
    tokens.raise_for_status()
    body = tokens.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise ValueError("Google sent no refresh token")
    auth = {"Authorization": f"Bearer {body['access_token']}"}

    who = client.get(USERINFO_URL, headers=auth)
    who.raise_for_status()
    email = str(who.json().get("email") or "")

    # Reconnecting the same account keeps writing into the folder it had.
    previous = load(db, settings)
    folder_id = previous.folder_id if previous and previous.email == email else ""
    if not folder_id:
        made = client.post(
            DRIVE_FILES,
            params={"fields": "id"},
            json={"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
            headers=auth,
        )
        made.raise_for_status()
        folder_id = str(made.json()["id"])

    connection = Connection(
        refresh_token=refresh_token,
        email=email,
        folder_id=folder_id,
        connected_at=datetime.now(UTC).isoformat(),
    )
    sealed = _fernet(settings).encrypt(json.dumps(asdict(connection)).encode())
    _put(db, CONNECTION_KEY, sealed.decode())
    db.commit()
    return connection


def forget(db: Session, settings: Settings, client: httpx.Client) -> None:
    """Disconnect: revoke the token at Google (best effort) and drop it here."""
    connection = load(db, settings)
    if connection is not None:
        # Gone from here either way; Google's side expires on its own.
        with contextlib.suppress(httpx.HTTPError):
            client.post(REVOKE_URL, data={"token": connection.refresh_token})
    row = db.get(SiteSetting, CONNECTION_KEY)
    if row is not None:
        db.delete(row)
    db.commit()


# --- stored state -----------------------------------------------------------


def load(db: Session, settings: Settings) -> Connection | None:
    row = db.get(SiteSetting, CONNECTION_KEY)
    if row is None:
        return None
    try:
        data = json.loads(_fernet(settings).decrypt(row.value.encode()))
        return Connection(**data)
    except (InvalidToken, ValueError, TypeError):
        return None


def refresher(settings: Settings, refresh_token: str) -> Callable[[httpx.Client], dict[str, Any]]:
    """A token source for ``drive_replica.GoogleDrive``: a fresh access token."""

    def fetch(client: httpx.Client) -> dict[str, Any]:
        response = client.post(
            TOKEN_URL,
            data={
                "client_id": settings.gdrive_oauth_client_id,
                "client_secret": settings.gdrive_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    return fetch


def record_run(db: Session, counts: tuple[int, int, int] | None, error: str | None) -> None:
    """What the last copy did, for the admin card."""
    value: dict[str, Any] = {"at": datetime.now(UTC).isoformat(), "error": error}
    if counts is not None:
        value.update(dict(zip(("copied", "already", "failed"), counts, strict=True)))
    _put(db, LAST_RUN_KEY, json.dumps(value))
    db.commit()


def last_run(db: Session) -> dict[str, Any] | None:
    row = db.get(SiteSetting, LAST_RUN_KEY)
    if row is None:
        return None
    try:
        value: dict[str, Any] = json.loads(row.value)
        return value
    except ValueError:
        return None


def _put(db: Session, key: str, value: str) -> None:
    row = db.get(SiteSetting, key)
    if row is None:
        db.add(SiteSetting(key=key, value=value))
    else:
        row.value = value
