"""Uploads in a private bucket, served at the same /media URLs as the disk.

The real ``S3Storage`` runs against an in-memory stand-in for the S3 client,
so what is tested is this code's behaviour -- the URLs it hands out, what
/media will and will not serve, and the one-time copy off the volume -- not
the network.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import MEDIA_CACHE_CONTROL, PRIVATE_MEDIA_FOLDERS, create_app
from app.storage import factory as storage_factory
from app.storage.s3 import S3Storage
from scripts.copy_media_to_bucket import copy


class _Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class _Paginator:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self._objects = objects

    def paginate(self, **_: Any) -> Iterator[dict[str, Any]]:
        yield {"Contents": [{"Key": key} for key in self._objects]}


class FakeS3Client:
    """The handful of S3 calls ``S3Storage`` makes, over a dict."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def _missing(self, op: str) -> ClientError:
        return ClientError({"Error": {"Code": "NoSuchKey"}}, op)

    def put_object(self, *, Key: str, Body: bytes, **_: Any) -> None:
        self.objects[Key] = Body

    def get_object(self, *, Key: str, **_: Any) -> dict[str, Any]:
        if Key not in self.objects:
            raise self._missing("GetObject")
        return {"Body": _Body(self.objects[Key])}

    def head_object(self, *, Key: str, **_: Any) -> dict[str, Any]:
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {}

    def delete_object(self, *, Key: str, **_: Any) -> None:
        self.objects.pop(Key, None)

    def get_paginator(self, _name: str) -> _Paginator:
        return _Paginator(self.objects)


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> S3Storage:
    storage = S3Storage.__new__(S3Storage)
    storage._client = FakeS3Client()
    storage._client_error = ClientError
    storage._bucket = "test-bucket"
    storage._public_base = ""
    storage._prefix = "/media"
    monkeypatch.setattr(storage_factory, "get_storage", lambda: storage)
    return storage


@pytest.fixture
def bucket_client(bucket: S3Storage) -> Iterator[TestClient]:
    settings = get_settings().model_copy(
        update={"storage_backend": "s3", "s3_bucket": "test-bucket", "s3_public_base_url": None}
    )
    with TestClient(create_app(settings)) as client:
        yield client


PHOTO = "businesses/abc/cover/" + "a" * 32 + ".jpg"


def test_a_private_bucket_hands_out_the_sites_own_media_urls(bucket: S3Storage) -> None:
    """Not a bucket address: those would be public, private folders included."""
    stored = bucket.save(key=PHOTO, data=b"jpeg", content_type="image/jpeg")
    assert stored.url == f"/media/{PHOTO}"


def test_a_photo_is_served_from_the_bucket_and_cached_for_good(
    bucket: S3Storage, bucket_client: TestClient
) -> None:
    bucket.save(key=PHOTO, data=b"jpeg-bytes", content_type="image/jpeg")
    response = bucket_client.get(f"/media/{PHOTO}")
    assert response.status_code == 200
    assert response.content == b"jpeg-bytes"
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.headers["cache-control"] == MEDIA_CACHE_CONTROL


@pytest.mark.parametrize("folder", sorted(PRIVATE_MEDIA_FOLDERS))
def test_private_files_in_the_bucket_are_not_on_the_media_route(
    bucket: S3Storage, bucket_client: TestClient, folder: str
) -> None:
    """The same rule as on disk: the file exists, and /media still refuses it."""
    key = f"{folder}/someone/{'b' * 32}.pdf"
    bucket.save(key=key, data=b"%PDF-1.4 private", content_type="application/pdf")
    assert bucket_client.get(f"/media/{key}").status_code == 404
    # Still readable by its own authenticated route, which reads storage directly.
    assert bucket.read(key) == b"%PDF-1.4 private"


def test_a_missing_file_is_not_found_rather_than_an_error(
    bucket: S3Storage, bucket_client: TestClient
) -> None:
    assert bucket_client.get(f"/media/{PHOTO}").status_code == 404
    with pytest.raises(FileNotFoundError):
        bucket.read(PHOTO)


def test_the_volume_is_copied_into_the_bucket_once(bucket: S3Storage, tmp_path: Path) -> None:
    """Everything on the volume goes, and a second boot copies nothing."""
    files = {
        PHOTO: b"photo",
        "owner-verification/someone/" + "c" * 32 + ".pdf": b"id scan",
    }
    for key, data in files.items():
        path = tmp_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    assert copy(tmp_path, bucket) == (2, 0)
    for key, data in files.items():
        assert bucket.read(key) == data
    assert copy(tmp_path, bucket) == (0, 0)
