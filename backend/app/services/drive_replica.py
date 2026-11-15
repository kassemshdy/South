"""A copy of the bucket -- uploads and database backups -- in a Google Drive folder.

The owners' decision (12-13 Nov 2026): everything janoubona.net keeps in its
Railway bucket is also copied to a Google Drive folder of theirs, private
documents and database dumps included, so the team can browse it with a
Google login. It sits beside the Amazon S3 replica (``media_replica``), not
in place of it, and reuses its rule and its loop: ``media_replica.replicate``.

It **only adds**. Each run lists what the folder already holds and uploads the
keys it lacks; nothing in Drive is ever overwritten or deleted, and the site's
bucket is only read. So account deletion does not reach this copy, exactly as
it does not reach the S3 replica or the Telegram chat.

The folder keeps the bucket's own layout (``businesses/<id>/item/...``): each
path segment is a Drive folder, created on first use. Every uploaded file
carries its full key in ``appProperties`` and its description, which is how a
later run knows what is already there without walking the tree.

**Who can read it is whoever the folder is shared with.** It holds ID scans,
CVs and full database dumps; nothing here can check how it is shared, so the
folder must never be shared by link.

Signs in as a Google *service account* (its JSON key in
``GDRIVE_SERVICE_ACCOUNT_JSON``, raw or base64) that the owners add to a
Shared Drive, or to a folder in one, as a Content manager. Inert without both
that and ``GDRIVE_FOLDER_ID``.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx
import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import SessionLocal
from app.services import gdrive_oauth, media_replica
from app.storage.s3 import S3Storage

logger = logging.getLogger("app.services.drive_replica")

#: ``pg_try_advisory_lock`` key, distinct from the S3 replica's and the backups'.
_LOCK_KEY = 7_242_028

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
SCOPE = "https://www.googleapis.com/auth/drive"
FOLDER = "application/vnd.google-apps.folder"
#: Marks the files this copy wrote, so a listing ignores anything else in the folder.
MARK = "janoubona_replica"

_COMMON = {"supportsAllDrives": "true"}


def load_service_account(raw: str) -> dict[str, Any]:
    """The service account key from its JSON, pasted raw or base64-encoded."""
    text_value = raw.strip()
    if not text_value.startswith("{"):
        try:
            text_value = base64.b64decode(text_value).decode()
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise ValueError("GDRIVE_SERVICE_ACCOUNT_JSON is neither JSON nor base64") from exc
    info: dict[str, Any] = json.loads(text_value)
    for field in ("client_email", "private_key"):
        if not info.get(field):
            raise ValueError(f"GDRIVE_SERVICE_ACCOUNT_JSON has no {field}")
    return info


class GoogleDrive:
    """The replica target: ``keys()`` and ``save()`` over one Drive folder."""

    def __init__(
        self,
        *,
        folder_id: str,
        client: httpx.Client,
        service_account: dict[str, Any] | None = None,
        token_source: Callable[[httpx.Client], dict[str, Any]] | None = None,
    ) -> None:
        if (service_account is None) == (token_source is None):
            raise ValueError("Give a service account or a token source, not both")
        self._account = service_account or {}
        self._token_source = token_source
        self._root = folder_id
        self._client = client
        self._token: str | None = None
        self._token_expires = 0.0
        self._folders: dict[str, str] = {"": folder_id}

    # --- auth -------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if self._token is None or time.time() > self._token_expires - 60:
            body = (
                self._token_source(self._client)
                if self._token_source is not None
                else self._service_account_token()
            )
            self._token = body["access_token"]
            self._token_expires = time.time() + int(body.get("expires_in", 3600))
        return {"Authorization": f"Bearer {self._token}"}

    def _service_account_token(self) -> dict[str, Any]:
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": self._account["client_email"],
                "scope": SCOPE,
                "aud": self._account.get("token_uri") or TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            },
            self._account["private_key"],
            algorithm="RS256",
        )
        response = self._client.post(
            self._account.get("token_uri") or TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    # --- listing ----------------------------------------------------------

    def keys(self) -> set[str]:
        """Every key this copy has already written, at any depth."""
        found: set[str] = set()
        page: str | None = None
        while True:
            params = {
                **_COMMON,
                "includeItemsFromAllDrives": "true",
                "corpora": "allDrives",
                "q": f"appProperties has {{ key='{MARK}' and value='1' }} and trashed=false",
                "fields": "nextPageToken, files(description, appProperties)",
                "pageSize": "1000",
            }
            if page:
                params["pageToken"] = page
            response = self._client.get(f"{API}/files", params=params, headers=self._headers())
            response.raise_for_status()
            body = response.json()
            for item in body.get("files", []):
                key = (item.get("appProperties") or {}).get("key") or item.get("description")
                if key:
                    found.add(key)
            page = body.get("nextPageToken")
            if not page:
                return found

    # --- writing ----------------------------------------------------------

    def _folder(self, path: str) -> str:
        """The Drive id of ``path`` under the root, creating what is missing."""
        if path in self._folders:
            return self._folders[path]
        parent_path, _, name = path.rpartition("/")
        parent = self._folder(parent_path)
        safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
        response = self._client.get(
            f"{API}/files",
            params={
                **_COMMON,
                "includeItemsFromAllDrives": "true",
                "corpora": "allDrives",
                "q": (
                    f"'{parent}' in parents and name='{safe_name}' "
                    f"and mimeType='{FOLDER}' and trashed=false"
                ),
                "fields": "files(id)",
            },
            headers=self._headers(),
        )
        response.raise_for_status()
        existing = response.json().get("files", [])
        if existing:
            folder_id = str(existing[0]["id"])
        else:
            created = self._client.post(
                f"{API}/files",
                params={**_COMMON, "fields": "id"},
                json={"name": name, "mimeType": FOLDER, "parents": [parent]},
                headers=self._headers(),
            )
            created.raise_for_status()
            folder_id = str(created.json()["id"])
        self._folders[path] = folder_id
        return folder_id

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        """Upload ``data`` as ``key``; returns the new file's Drive id."""
        folder_path, _, name = key.rpartition("/")
        metadata: dict[str, Any] = {
            "name": name,
            "parents": [self._folder(folder_path)],
            "description": key,
            "appProperties": {MARK: "1"},
        }
        # appProperties hold at most 124 bytes per key+value; the description
        # carries the key whatever its length.
        if len(b"key") + len(key.encode()) <= 124:
            metadata["appProperties"]["key"] = key
        session = self._client.post(
            UPLOAD,
            params={**_COMMON, "uploadType": "resumable", "fields": "id"},
            json=metadata,
            headers={**self._headers(), "X-Upload-Content-Type": content_type},
        )
        session.raise_for_status()
        uploaded = self._client.put(
            session.headers["Location"],
            content=data,
            headers={"Content-Type": content_type},
        )
        uploaded.raise_for_status()
        return str(uploaded.json().get("id", ""))


def configured(settings: Settings) -> bool:
    """Whether a copy could run at all: a service account, or the connect button's client."""
    return bool(
        (settings.gdrive_folder_id and settings.gdrive_service_account_json)
        or gdrive_oauth.available(settings)
    )


def drive_from_settings(
    settings: Settings, client: httpx.Client, db: Session | None = None
) -> GoogleDrive | None:
    """The Drive target, or None when it is not configured or not connected.

    A service account in the environment wins; otherwise the connection a
    manager made with the admin panel's button, when there is one."""
    if settings.gdrive_folder_id and settings.gdrive_service_account_json:
        return GoogleDrive(
            service_account=load_service_account(settings.gdrive_service_account_json),
            folder_id=settings.gdrive_folder_id,
            client=client,
        )
    if db is None or not gdrive_oauth.available(settings):
        return None
    connection = gdrive_oauth.load(db, settings)
    if connection is None:
        return None
    return GoogleDrive(
        token_source=gdrive_oauth.refresher(settings, connection.refresh_token),
        folder_id=connection.folder_id,
        client=client,
    )


def replicate_configured(settings: Settings, storage: object) -> tuple[int, int, int] | None:
    """Copy the site's bucket to the Drive folder; None when there is nothing to do."""
    if not isinstance(storage, S3Storage) or not configured(settings):
        return None
    with SessionLocal() as db, httpx.Client(timeout=120) as client:
        drive = drive_from_settings(settings, client, db)
        if drive is None:
            return None
        try:
            counts = media_replica.replicate(storage, drive)
        except Exception as exc:  # recorded for the admin card, then raised
            gdrive_oauth.record_run(db, None, type(exc).__name__)
            raise
        gdrive_oauth.record_run(db, counts, None)
    # In the message itself: the deploy log prints it, and it is how the copy
    # is checked -- every file copied or already there, none failed.
    logger.info("Google Drive copy: %d copied, %d already there, %d failed", *counts)
    return counts


def replicate_if_first(settings: Settings, storage: object) -> bool:
    """Copy unless another worker already is; True when this one did."""
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            if not connection.execute(
                text("select pg_try_advisory_lock(:key)"), {"key": _LOCK_KEY}
            ).scalar():
                return False
            try:
                replicate_configured(settings, storage)
            finally:
                connection.execute(text("select pg_advisory_unlock(:key)"), {"key": _LOCK_KEY})
            return True
    finally:
        engine.dispose()


async def run_periodic(settings: Settings, storage: object, *, interval_hours: int) -> None:
    """Copy every ``interval_hours`` for as long as the API runs."""
    while True:
        await asyncio.sleep(interval_hours * 3600)
        try:
            await asyncio.to_thread(replicate_if_first, settings, storage)
        except Exception:  # reported, and the next interval tries again
            logger.exception("Scheduled Google Drive copy failed")
