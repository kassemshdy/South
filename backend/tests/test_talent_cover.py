"""A service profile's photo and cover.

The owners' ticket of 29 Oct 2026 made the photo and a cover compulsory for a
service before review. On 10 Nov 2026 they dropped the wide cover: only the
photo is required now, and the pages no longer show a cover. The upload
routes stay, so a stored cover is not lost and can still be removed.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1200, 500), (90, 120, 100)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


def _profile(
    client: TestClient, phone: str, skill: TalentSkill, location: Location
) -> tuple[str, str, dict[str, str]]:
    headers = sign_in(client, phone)
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "bio": ar("talent.designer_bio"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
            "whatsapp": "03950101",
            "years_experience": 7,
            "work_mode": "BOTH",
        },
    )
    assert created.status_code == 201, created.text
    # Review needs the owner's ID card on file (the owners' decision, 9 Nov 2026).
    client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("id.pdf", b"%PDF-1.4\nfake\n", "application/pdf")},
    )
    return created.json()["id"], created.json()["slug"], headers


def _upload(client: TestClient, headers: dict[str, str], kind: str) -> dict:
    response = client.post(
        "/api/my/talent/images",
        headers=headers,
        files={"file": ("image.jpg", _jpeg(), "image/jpeg")},
        data={"kind": kind},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a_service_goes_to_review_with_its_photo_and_no_cover(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    _, _, headers = _profile(client, "03960001", skill, location)
    missing = client.get("/api/my/talent/readiness", headers=headers).json()
    assert "talent.field.photo" in missing
    assert "talent.field.cover" not in missing
    assert client.post("/api/my/talent/submit", headers=headers).status_code == 422

    _upload(client, headers, "LOGO")
    assert client.get("/api/my/talent/readiness", headers=headers).json() == []
    submitted = client.post("/api/my/talent/submit", headers=headers)
    assert submitted.status_code == 200, submitted.text


def test_the_cover_is_published_replaced_and_removed(
    client: TestClient, db: Session, skill: TalentSkill, location: Location
) -> None:
    profile_id, slug, headers = _profile(client, "03960002", skill, location)
    first = _upload(client, headers, "COVER")["cover_url"]
    second = _upload(client, headers, "COVER")["cover_url"]
    assert second and second != first
    # One cover at a time: the replaced one is gone, not kept beside it.
    entity = db.get(TalentProfile, profile_id)
    assert entity is not None
    db.refresh(entity)
    assert sum(1 for image in entity.images if image.kind.value == "COVER") == 1
    # Never in the portfolio.
    owner_images = client.get("/api/my/talent", headers=headers).json()["images"]
    assert all(image["kind"] == "GALLERY" for image in owner_images)

    entity.status = BusinessStatus.APPROVED
    db.commit()
    assert client.get(f"/api/talent/{slug}").json()["cover_url"] == second

    removed = client.delete("/api/my/talent/images/kind/COVER", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["cover_url"] is None
    assert client.get(f"/api/talent/{slug}").json()["cover_url"] is None


def test_an_approved_profile_without_a_cover_stays_public(
    client: TestClient, db: Session, skill: TalentSkill, location: Location
) -> None:
    """The requirement is for review, not a retroactive purge of live pages."""
    profile_id, slug, _ = _profile(client, "03960003", skill, location)
    entity = db.get(TalentProfile, profile_id)
    assert entity is not None
    entity.status = BusinessStatus.APPROVED
    db.commit()
    page = client.get(f"/api/talent/{slug}")
    assert page.status_code == 200
    assert page.json()["cover_url"] is None


def test_an_administrator_gives_a_profile_a_cover_but_an_owner_cannot_use_that_route(
    client: TestClient, admin: User, skill: TalentSkill, location: Location
) -> None:
    profile_id, _, headers = _profile(client, "03960004", skill, location)
    files = {"file": ("image.jpg", _jpeg(), "image/jpeg")}

    refused = client.post(
        f"/api/admin/talent/{profile_id}/images",
        headers=headers,
        files=files,
        data={"kind": "COVER"},
    )
    assert refused.status_code == 403

    given = client.post(
        f"/api/admin/talent/{profile_id}/images",
        headers=admin_headers(client),
        files=files,
        data={"kind": "COVER"},
    )
    assert given.status_code == 200, given.text
    assert given.json()["cover_url"]

    gallery = client.post(
        f"/api/admin/talent/{profile_id}/images",
        headers=admin_headers(client),
        files=files,
        data={"kind": "GALLERY"},
    )
    assert gallery.status_code == 422
