"""Photo stories: owners post, administrators approve, a day later they go."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.story import StoryImage
from app.models.talent import TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from app.services import telegram_archive
from tests.conftest import OWNER_PASSWORD, admin_headers, sign_in
from tests.samples import ar
from tests.test_permissions import _invite
from tests.test_talent import _approve, _create_profile, skill  # noqa: F401
from tests.test_uploads_and_urls import make_image
from tests.test_views import approved_business, owner_headers  # noqa: F401


def _photo() -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("story.jpg", make_image((900, 1600)), "image/jpeg")}


def _post(client: TestClient, headers: dict[str, str], business: Business) -> dict[str, str]:
    posted = client.post(
        f"/api/my/businesses/{business.id}/stories",
        headers=headers,
        files=_photo(),
        data={"caption": ar("story.caption")},
    )
    assert posted.status_code == 201, posted.text
    return posted.json()


def test_a_story_shows_only_once_approved_and_for_a_day(
    client: TestClient,
    db: Session,
    admin: User,
    owner_headers: dict[str, str],  # noqa: F811
    approved_business: Business,  # noqa: F811
) -> None:
    story = _post(client, owner_headers, approved_business)
    assert story["status"] == "PENDING_REVIEW"
    assert client.get("/api/home/stories").json() == [], "waiting for review"

    staff = admin_headers(client)
    queue = client.get("/api/admin/stories", headers=staff).json()
    assert [entry["id"] for entry in queue] == [story["id"]]
    assert queue[0]["listing_slug"] == approved_business.slug

    approved = client.post(f"/api/admin/stories/{story['id']}/approve", headers=staff).json()
    assert approved["status"] == "APPROVED"
    shown = datetime.fromisoformat(approved["expires_at"]) - datetime.fromisoformat(
        approved["approved_at"]
    )
    assert shown == timedelta(hours=24)

    groups = client.get("/api/home/stories").json()
    assert [(g["kind"], g["slug"]) for g in groups] == [("business", approved_business.slug)]
    assert groups[0]["stories"][0]["caption"] == ar("story.caption")
    assert "status" not in groups[0]["stories"][0]

    # A day later it is gone from the row, and from storage the next time
    # anyone lists stories.
    row = db.get(StoryImage, story["id"])
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert client.get("/api/home/stories").json() == []
    url = row.image_url
    assert client.get(f"/api/my/businesses/{approved_business.id}/stories", headers=owner_headers).json() == []
    assert client.get(url).status_code == 404


def test_a_rejected_story_or_a_hidden_listing_shows_nothing(
    client: TestClient,
    db: Session,
    admin: User,
    owner_headers: dict[str, str],  # noqa: F811
    approved_business: Business,  # noqa: F811
) -> None:
    staff = admin_headers(client)
    rejected = _post(client, owner_headers, approved_business)
    client.post(f"/api/admin/stories/{rejected['id']}/reject", headers=staff)
    assert client.get("/api/home/stories").json() == []

    story = _post(client, owner_headers, approved_business)
    client.post(f"/api/admin/stories/{story['id']}/approve", headers=staff)
    assert len(client.get("/api/home/stories").json()) == 1
    approved_business.status = BusinessStatus.SUSPENDED
    db.commit()
    assert client.get("/api/home/stories").json() == [], "a suspended shop's stories go with it"


def test_an_owner_reaches_only_their_own_listing(
    client: TestClient,
    owner_headers: dict[str, str],  # noqa: F811
    approved_business: Business,  # noqa: F811
) -> None:
    story = _post(client, owner_headers, approved_business)
    stranger = sign_in(client, "03990077")
    base = f"/api/my/businesses/{approved_business.id}/stories"
    assert client.get(base, headers=stranger).status_code == 404
    assert client.post(base, headers=stranger, files=_photo()).status_code == 404
    assert client.delete(f"{base}/{story['id']}", headers=stranger).status_code == 404
    assert client.post(base, files=_photo()).status_code == 401
    # The owner may take their own story down.
    assert client.delete(f"{base}/{story['id']}", headers=owner_headers).json() == []


def test_a_service_profile_posts_stories_too(
    client: TestClient,
    db: Session,
    admin: User,
    skill: TalentSkill,  # noqa: F811
    location: Location,
) -> None:
    person = sign_in(client, "03960104")
    profile = _create_profile(client, person, skill, location)
    _approve(client, db, admin, profile["id"])
    posted = client.post("/api/my/talent/stories", headers=person, files=_photo())
    assert posted.status_code == 201, posted.text
    client.post(f"/api/admin/stories/{posted.json()['id']}/approve", headers=admin_headers(client))
    groups = client.get("/api/home/stories").json()
    assert [(g["kind"], g["slug"]) for g in groups] == [("talent", profile["slug"])]


def test_only_reviewers_approve(
    client: TestClient,
    admin: User,
    owner_headers: dict[str, str],  # noqa: F811
    approved_business: Business,  # noqa: F811
) -> None:
    story = _post(client, owner_headers, approved_business)
    manager = admin_headers(client)
    editor = _invite(client, manager, "EDITOR", "editor@example.com")
    reviewer = _invite(client, manager, "REVIEWER", "reviewer@example.com")
    approve = f"/api/admin/stories/{story['id']}/approve"
    assert client.post(approve, headers=editor).status_code == 403
    assert client.post(approve, headers=owner_headers).status_code == 403
    assert client.post(approve, headers=reviewer).status_code == 200


def test_too_many_open_stories_are_refused(
    client: TestClient,
    owner_headers: dict[str, str],  # noqa: F811
    approved_business: Business,  # noqa: F811
) -> None:
    for _ in range(10):
        _post(client, owner_headers, approved_business)
    extra = client.post(
        f"/api/my/businesses/{approved_business.id}/stories", headers=owner_headers, files=_photo()
    )
    assert extra.status_code == 409


def test_a_new_story_is_copied_to_telegram_and_links_to_the_queue() -> None:
    assert "story_images" in telegram_archive.ARCHIVED_TABLES
    change = telegram_archive.Change(action="created", table="story_images", row_id="x")
    assert telegram_archive.admin_path(change, lambda _: None) == "/admin/stories"


def test_deleting_the_account_deletes_its_story_photos(
    client: TestClient,
    db: Session,
    owner_headers: dict[str, str],  # noqa: F811
    approved_business: Business,  # noqa: F811
) -> None:
    story = _post(client, owner_headers, approved_business)
    assert client.get(story["image_url"]).status_code == 200
    deleted = client.post(
        "/api/me/delete", headers=owner_headers, json={"password": OWNER_PASSWORD}
    )
    assert deleted.status_code == 200, deleted.text
    assert db.get(StoryImage, story["id"]) is None
    assert client.get(story["image_url"]).status_code == 404
