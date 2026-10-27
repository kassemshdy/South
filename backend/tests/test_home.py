"""The home page's sections and its stories row.

Asserted: a fresh site lists every section, the page's original three
first; an administrator's order and hidden sections are kept, unknown
names dropped and missing ones appended; only staff who edit content may
save it; the stories row lists only published profiles that have a video.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.home import SECTIONS
from app.models.talent import TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.test_talent import _approve, _create_profile, skill  # noqa: F401

VIDEO = "https://www.youtube.com/shorts/3Np8hKhrbB4"


def test_a_fresh_site_shows_every_section_the_original_ones_first(client: TestClient) -> None:
    layout = client.get("/api/home/layout").json()["sections"]
    assert [s["id"] for s in layout] == list(SECTIONS)
    assert [s["id"] for s in layout][:3] == ["cover", "hero", "slogan"]
    assert all(s["visible"] for s in layout)


def test_an_administrator_reorders_and_hides_sections(client: TestClient, admin: User) -> None:
    saved = client.put(
        "/api/admin/home/layout",
        headers=admin_headers(client),
        json={
            "sections": [
                {"id": "search", "visible": True},
                {"id": "products", "visible": True},
                {"id": "slogan", "visible": False},
                {"id": "not-a-section", "visible": True},
                {"id": "search", "visible": False},
            ]
        },
    )
    assert saved.status_code == 200, saved.text

    layout = client.get("/api/home/layout").json()["sections"]
    ids = [s["id"] for s in layout]
    assert ids[:3] == ["search", "products", "slogan"]
    assert "not-a-section" not in ids
    assert sorted(ids) == sorted(SECTIONS), "a missing section is appended, a duplicate dropped"
    assert {s["id"]: s["visible"] for s in layout}["slogan"] is False
    assert {s["id"]: s["visible"] for s in layout}["search"] is True


def test_only_staff_may_save_the_layout(client: TestClient, admin: User) -> None:
    owner = sign_in(client, "03960101")
    body = {"sections": [{"id": "news", "visible": True}]}
    assert client.put("/api/admin/home/layout", headers=owner, json=body).status_code == 403
    assert client.put("/api/admin/home/layout", json=body).status_code == 401


def test_stories_list_only_published_profiles_with_a_video(
    client: TestClient,
    db: Session,
    admin: User,
    skill: TalentSkill,  # noqa: F811
    location: Location,
) -> None:
    published = sign_in(client, "03960102")
    profile = _create_profile(client, published, skill, location)
    client.put("/api/my/talent", headers=published, json={"video_url": VIDEO})

    pending = sign_in(client, "03960103")
    _create_profile(client, pending, skill, location)
    client.put("/api/my/talent", headers=pending, json={"video_url": VIDEO})

    assert client.get("/api/home/stories").json() == [], "nothing published yet"

    _approve(client, db, admin, profile["id"])
    stories = client.get("/api/home/stories").json()
    assert [(s["kind"], s["slug"]) for s in stories] == [("talent", profile["slug"])]
    assert stories[0]["youtube_video_id"] == "3Np8hKhrbB4"
