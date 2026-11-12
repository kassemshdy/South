"""Links to videos of a services provider's work (the owners' review,
12 Nov 2026): four platforms, several per profile, and only a platform and
a pinned key kept -- the link and the embed are rebuilt on the platform's
own host."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.core.work_videos import parse_work_video
from app.models.talent import TalentSkill
from app.models.taxonomy import Location
from tests.conftest import sign_in
from tests.samples import ar


@pytest.mark.parametrize(
    ("link", "platform", "embed"),
    [
        ("https://youtu.be/dQw4w9WgXcQ?t=3", "YOUTUBE", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
        ("instagram.com/reel/Cabc123/?igsh=x", "INSTAGRAM", "https://www.instagram.com/reel/Cabc123/embed/"),
        (
            "https://www.tiktok.com/@ali.r/video/7212345678901234567?lang=ar",
            "TIKTOK",
            "https://www.tiktok.com/embed/v2/7212345678901234567",
        ),
        (
            "https://m.facebook.com/reel/987654321",
            "FACEBOOK",
            "https://www.facebook.com/plugins/video.php?show_text=false&href="
            "https%3A%2F%2Fwww.facebook.com%2Freel%2F987654321",
        ),
    ],
)
def test_each_platform_is_read_and_rebuilt(link: str, platform: str, embed: str) -> None:
    video = parse_work_video(link)
    assert video.platform == platform
    assert video.embed_url == embed


@pytest.mark.parametrize(
    "link",
    [
        "https://evil.example/video.mp4",
        "javascript:alert(1)",
        "https://www.tiktok.com/@ali.r",
        "https://vm.tiktok.com/ZMabc/",
        "https://www.facebook.com/somepage",
    ],
)
def test_anything_else_is_refused(link: str) -> None:
    with pytest.raises(ValidationError):
        parse_work_video(link)


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


def test_a_profile_keeps_its_videos_in_order(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950301")
    client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    saved = client.put(
        "/api/my/talent",
        headers=headers,
        json={
            "work_videos": [
                "https://www.tiktok.com/@ali.r/video/7212345678901234567",
                "https://youtu.be/dQw4w9WgXcQ",
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    assert [video["platform"] for video in saved.json()["work_videos"]] == ["TIKTOK", "YOUTUBE"]

    refused = client.put(
        "/api/my/talent", headers=headers, json={"work_videos": ["https://evil.example/x.mp4"]}
    )
    assert refused.status_code == 422
    # A refused save changes nothing.
    kept = client.get("/api/my/talent", headers=headers).json()["work_videos"]
    assert len(kept) == 2
