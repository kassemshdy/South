"""The Google Drive copy of the bucket (the owners' decision, 13 Nov 2026).

Drive is simulated with ``httpx.MockTransport``: these pin what is sent --
a signed service-account sign-in, the bucket's folders recreated, every file
uploaded once with its key attached -- and that a second run adds nothing.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.services import drive_replica, media_replica

ROOT = "root-folder"


def _account() -> dict[str, Any]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return {"client_email": "copy@example.iam.gserviceaccount.com", "private_key": pem}


class FakeDrive:
    """Just enough of the Drive v3 API for the replica to talk to."""

    def __init__(self, public_key: Any) -> None:
        self.public_key = public_key
        self.folders: dict[tuple[str, str], str] = {}
        self.files: list[dict[str, Any]] = []
        self.pending: dict[str, dict[str, Any]] = {}
        self.token_requests = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.startswith(drive_replica.TOKEN_URL):
            self.token_requests += 1
            form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
            claims = jwt.decode(
                form["assertion"],
                self.public_key,
                algorithms=["RS256"],
                audience=drive_replica.TOKEN_URL,
            )
            assert claims["scope"] == drive_replica.SCOPE
            return httpx.Response(200, json={"access_token": "t0k", "expires_in": 3600})
        assert request.headers.get("Authorization") == "Bearer t0k" or "upload-session" in url
        if request.method == "GET" and url.startswith(f"{drive_replica.API}/files"):
            q = request.url.params["q"]
            if "appProperties has" in q:
                return httpx.Response(
                    200,
                    json={
                        "files": [
                            {"description": f["key"], "appProperties": f["appProperties"]}
                            for f in self.files
                        ]
                    },
                )
            parent = q.split("'")[1]
            name = q.split("name='")[1].split("' and")[0]
            found = self.folders.get((parent, name))
            return httpx.Response(200, json={"files": [{"id": found}] if found else []})
        if request.method == "POST" and url.startswith(f"{drive_replica.API}/files"):
            body = json.loads(request.content)
            assert body["mimeType"] == drive_replica.FOLDER
            folder_id = f"f{len(self.folders)}"
            self.folders[(body["parents"][0], body["name"])] = folder_id
            return httpx.Response(200, json={"id": folder_id})
        if request.method == "POST" and url.startswith(drive_replica.UPLOAD):
            assert request.url.params["uploadType"] == "resumable"
            assert request.url.params["supportsAllDrives"] == "true"
            session = f"https://upload.example/upload-session/{len(self.pending)}"
            self.pending[session] = json.loads(request.content)
            return httpx.Response(200, headers={"Location": session})
        if request.method == "PUT" and url in self.pending:
            meta = self.pending.pop(url)
            self.files.append(
                {
                    "key": meta["description"],
                    "name": meta["name"],
                    "parent": meta["parents"][0],
                    "appProperties": meta["appProperties"],
                    "data": request.content,
                }
            )
            return httpx.Response(200, json={"id": f"file{len(self.files)}"})
        raise AssertionError(f"unexpected request {request.method} {url}")


class Bucket:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def keys(self) -> set[str]:
        return set(self.files)

    def read(self, key: str) -> bytes:
        return self.files[key]


def _drive() -> tuple[drive_replica.GoogleDrive, FakeDrive]:
    account = _account()
    public = serialization.load_pem_private_key(
        account["private_key"].encode(), password=None
    ).public_key()
    fake = FakeDrive(public)
    client = httpx.Client(transport=httpx.MockTransport(fake.handle))
    return drive_replica.GoogleDrive(service_account=account, folder_id=ROOT, client=client), fake


def test_every_file_is_copied_once_in_the_buckets_own_folders() -> None:
    drive, fake = _drive()
    bucket = Bucket(
        {
            "businesses/b1/item/a.jpg": b"photo",
            "businesses/b1/logo/l.webp": b"logo",
            "verification/u1/id.pdf": b"scan",
            "backups/db/2026-11-13.sql.gz": b"dump",
            "businesses/b1/": b"",  # a folder marker, not a file
        }
    )

    assert media_replica.replicate(bucket, drive) == (4, 0, 0)
    copied = {f["key"]: f for f in fake.files}
    assert set(copied) == {
        "businesses/b1/item/a.jpg",
        "businesses/b1/logo/l.webp",
        "verification/u1/id.pdf",
        "backups/db/2026-11-13.sql.gz",
    }
    assert copied["verification/u1/id.pdf"]["data"] == b"scan"
    assert copied["businesses/b1/item/a.jpg"]["name"] == "a.jpg"
    # businesses -> b1 -> item, each created once and reused.
    businesses = fake.folders[(ROOT, "businesses")]
    b1 = fake.folders[(businesses, "b1")]
    assert copied["businesses/b1/item/a.jpg"]["parent"] == fake.folders[(b1, "item")]
    assert copied["businesses/b1/logo/l.webp"]["parent"] == fake.folders[(b1, "logo")]
    assert all(f["appProperties"][drive_replica.MARK] == "1" for f in fake.files)
    # One sign-in serves the whole run.
    assert fake.token_requests == 1

    # A second run adds nothing, and a new file is the only upload.
    assert media_replica.replicate(bucket, drive) == (0, 4, 0)
    bucket.files["businesses/b1/item/new.jpg"] = b"new"
    assert media_replica.replicate(bucket, drive) == (1, 4, 0)
    assert len(fake.files) == 5


def test_the_key_is_accepted_raw_or_base64_and_refused_when_incomplete() -> None:
    account = _account()
    raw = json.dumps(account)
    assert drive_replica.load_service_account(raw)["client_email"] == account["client_email"]
    encoded = base64.b64encode(raw.encode()).decode()
    assert drive_replica.load_service_account(encoded)["private_key"] == account["private_key"]
    with pytest.raises(ValueError):
        drive_replica.load_service_account(json.dumps({"client_email": "x"}))
    with pytest.raises(ValueError):
        drive_replica.load_service_account("not json and not base64!")


def test_nothing_happens_without_both_settings() -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as client:
        assert drive_replica.drive_from_settings(Settings(gdrive_folder_id=ROOT), client) is None
        assert (
            drive_replica.drive_from_settings(
                Settings(gdrive_service_account_json=json.dumps(_account())), client
            )
            is None
        )
    # Local storage (no bucket): nothing to copy, nothing sent.
    assert drive_replica.replicate_configured(Settings(gdrive_folder_id=ROOT), object()) is None
