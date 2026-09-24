"""The public media mount: thumbnails, caching, and what it must never serve."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.main import MEDIA_CACHE_CONTROL, PRIVATE_MEDIA_FOLDERS
from app.models.business import Business
from app.models.enums import BusinessStatus, ImageKind
from app.services.images import ImageService, thumbnail_key
from app.storage.factory import get_storage
from scripts.backfill_thumbnails import backfill
from tests.test_uploads_and_urls import business, make_image

__all__ = ["business"]  # the fixture, re-used


def _upload(
    client: TestClient, business_id: str, headers: dict[str, str], kind: str, size: tuple[int, int]
) -> None:
    response = client.post(
        f"/api/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("photo.jpg", make_image(size), "image/jpeg")},
        data={"kind": kind},
    )
    assert response.status_code == 201, response.text


def _approve(db: Session, business_id: str) -> None:
    record = db.get(Business, business_id)
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()


def test_a_card_gets_a_small_copy_of_the_cover(
    client: TestClient, db: Session, business: tuple[str, dict[str, str]]
) -> None:
    """The reason thumbnails exist: a card no longer downloads the original."""
    business_id, headers = business
    _upload(client, business_id, headers, "COVER", (3000, 2000))
    _upload(client, business_id, headers, "LOGO", (800, 800))
    _approve(db, business_id)

    [card] = client.get("/api/businesses").json()["items"]
    assert card["cover_thumb_url"].endswith(".thumb.jpg")
    assert card["logo_thumb_url"].endswith(".thumb.jpg")

    full = client.get(card["cover_url"])
    thumb = client.get(card["cover_thumb_url"])
    assert thumb.status_code == 200
    assert len(thumb.content) < len(full.content)
    width, _ = Image.open(io.BytesIO(thumb.content)).size
    assert width <= 720


def test_replacing_a_photo_removes_its_small_copy(
    client: TestClient, db: Session, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    _upload(client, business_id, headers, "COVER", (1200, 800))
    first = db.get(Business, business_id)
    assert first is not None and first.cover_storage_key is not None
    first_thumb = thumbnail_key(first.cover_storage_key)
    assert first_thumb is not None

    _upload(client, business_id, headers, "COVER", (1200, 800))
    storage = get_storage()
    assert not storage.exists(first_thumb)


def test_the_backfill_writes_what_is_missing_and_nothing_twice(
    client: TestClient, db: Session, business: tuple[str, dict[str, str]]
) -> None:
    """Photos stored before thumbnails existed get theirs on the next boot."""
    business_id, headers = business
    _upload(client, business_id, headers, "COVER", (1200, 800))
    record = db.get(Business, business_id)
    assert record is not None and record.cover_storage_key is not None
    thumb = thumbnail_key(record.cover_storage_key)
    assert thumb is not None

    storage = get_storage()
    storage.delete(thumb)  # as if uploaded before this change

    assert backfill() == (1, 0)
    assert storage.exists(thumb)
    assert backfill() == (0, 0)


def test_a_gallery_photo_has_no_small_copy() -> None:
    """Only shown large, so a thumbnail would be bytes nobody fetches."""
    service = ImageService(get_storage(), get_settings())
    key = "businesses/x/gallery/" + "a" * 32 + ".jpg"
    assert service.ensure_thumbnail(key, ImageKind.GALLERY) is False


def test_an_uploaded_photo_is_cached_for_good(
    client: TestClient, db: Session, business: tuple[str, dict[str, str]]
) -> None:
    """A photo is written under a fresh name and never rewritten in place."""
    business_id, headers = business
    _upload(client, business_id, headers, "COVER", (1200, 800))
    _approve(db, business_id)
    [card] = client.get("/api/businesses").json()["items"]

    response = client.get(card["cover_url"])
    assert response.status_code == 200
    assert response.headers["cache-control"] == MEDIA_CACHE_CONTROL


@pytest.mark.parametrize("folder", sorted(PRIVATE_MEDIA_FOLDERS))
def test_private_files_are_not_on_the_media_mount(client: TestClient, folder: str) -> None:
    """ID scans, CVs, official papers and ticket attachments share the disk
    with the photographs. Knowing a file's name must not be enough to read it
    -- they have their own authenticated routes."""
    key = f"{folder}/someone/{'b' * 32}.pdf"
    get_storage().save(key=key, data=b"%PDF-1.4 private", content_type="application/pdf")

    assert client.get(f"/media/{key}").status_code == 404
    assert client.get(f"/media/businesses/../{key}").status_code == 404


def test_every_private_folder_is_named(client: TestClient) -> None:
    """A new private upload service must add its folder, or it is public."""
    expected = {
        "owner-verification",
        "owner-verification-back",
        "owner-cv",
        "business-documents",
        "feedback",
    }
    assert expected <= PRIVATE_MEDIA_FOLDERS

