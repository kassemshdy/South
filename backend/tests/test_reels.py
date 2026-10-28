"""The home page's reels: links to Instagram posts an administrator chooses."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.instagram import parse_instagram_post
from app.models.user import User
from app.services import youtube_covers
from tests.conftest import admin_headers, sign_in
from tests.samples import ar
from tests.test_permissions import _invite
from tests.test_uploads_and_urls import make_image


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The suite never talks to YouTube: thumbnails come from here."""
    asked: list[str] = []

    def fake(video_id: str) -> bytes:
        asked.append(video_id)
        return make_image((720, 1280))

    monkeypatch.setattr(youtube_covers, "fetch_short_cover", fake)
    return asked


@pytest.mark.parametrize(
    ("pasted", "kind", "code"),
    [
        ("https://www.instagram.com/reel/C9xYz_12-ab/", "reel", "C9xYz_12-ab"),
        ("https://www.instagram.com/reels/C9xYz_12-ab", "reel", "C9xYz_12-ab"),
        ("instagram.com/p/C9xYz_12-ab/?igsh=MWQ1ZGUxMzBkMA==", "p", "C9xYz_12-ab"),
        ("http://m.instagram.com/tv/C9xYz_12-ab/", "tv", "C9xYz_12-ab"),
        ("https://www.instagram.com/south.shop/reel/C9xYz_12-ab/", "reel", "C9xYz_12-ab"),
        ("  https://WWW.INSTAGRAM.COM/reel/C9xYz_12-ab/  ", "reel", "C9xYz_12-ab"),
    ],
)
def test_a_link_to_one_post_is_recognised(pasted: str, kind: str, code: str) -> None:
    post = parse_instagram_post(pasted)
    assert post is not None
    assert (post.kind, post.code) == (kind, code)
    assert post.embed_url == f"https://www.instagram.com/{kind}/{code}/embed/"


@pytest.mark.parametrize(
    "pasted",
    [
        "",
        "https://www.instagram.com/south.shop/",
        "https://www.instagram.com/reel/",
        "https://instagram.com.evil.example/reel/C9xYz_12-ab/",
        "https://evil.example/www.instagram.com/reel/C9xYz_12-ab/",
        "https://user@www.instagram.com/reel/C9xYz_12-ab/",
        "https://www.instagram.com:8443/reel/C9xYz_12-ab/",
        "javascript:alert(1)//www.instagram.com/reel/C9xYz_12-ab/",
        "https://www.instagram.com/reel/C9xYz_12-ab/embed/",
        "https://www.facebook.com/reel/1234567890",
    ],
)
def test_anything_else_is_refused(pasted: str) -> None:
    assert parse_instagram_post(pasted) is None


def test_a_reel_is_shown_only_once_published(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    added = client.post(
        "/api/admin/reels",
        headers=headers,
        json={
            "url": "https://www.instagram.com/reel/C9xYz_12-ab/?igsh=abc",
            "caption_ar": ar("reel.caption"),
            "caption_en": "   ",
        },
    )
    assert added.status_code == 201, added.text
    reel = added.json()
    assert reel["is_published"] is False
    # The stored link is rebuilt from the code, not the pasted text.
    assert reel["url"] == "https://www.instagram.com/reel/C9xYz_12-ab/"
    assert reel["caption_en"] is None
    assert client.get("/api/reels").json() == []

    published = client.put(
        f"/api/admin/reels/{reel['id']}",
        headers=headers,
        json={"url": reel["url"], "caption_ar": ar("reel.caption"), "is_published": True},
    )
    assert published.status_code == 200, published.text
    public = client.get("/api/reels").json()
    assert [r["id"] for r in public] == [reel["id"]]
    assert public[0]["caption_ar"] == ar("reel.caption")
    assert "is_published" not in public[0]

    deleted = client.delete(f"/api/admin/reels/{reel['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == []
    assert client.get("/api/reels").json() == []


def test_a_bad_or_repeated_link_is_refused(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    bad = client.post("/api/admin/reels", headers=headers, json={"url": "https://example.com/x"})
    assert bad.status_code == 422
    first = client.post(
        "/api/admin/reels", headers=headers, json={"url": "instagram.com/reel/C9xYz_12-ab"}
    )
    assert first.status_code == 201
    # The same post through a different link is the same reel.
    again = client.post(
        "/api/admin/reels",
        headers=headers,
        json={"url": "https://www.instagram.com/south.shop/reels/C9xYz_12-ab/"},
    )
    assert again.status_code == 409


def test_new_reels_go_first_and_the_order_can_be_set(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    ids = [
        client.post(
            "/api/admin/reels",
            headers=headers,
            json={"url": f"https://www.instagram.com/reel/Reel{n}code/", "is_published": True},
        ).json()["id"]
        for n in range(3)
    ]
    assert [r["id"] for r in client.get("/api/reels").json()] == ids[::-1]

    wanted = [ids[1], ids[0], ids[2]]
    ordered = client.put("/api/admin/reels/order", headers=headers, json={"ids": wanted})
    assert ordered.status_code == 200, ordered.text
    assert [r["id"] for r in client.get("/api/reels").json()] == wanted

    # A list that leaves one out is refused rather than half applied.
    partial = client.put("/api/admin/reels/order", headers=headers, json={"ids": wanted[:2]})
    assert partial.status_code == 422


def test_a_reel_cover_is_stored_and_replaced(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    reel = client.post(
        "/api/admin/reels", headers=headers, json={"url": "instagram.com/reel/C9xYz_12-ab"}
    ).json()
    cover = client.post(
        f"/api/admin/reels/{reel['id']}/cover",
        headers=headers,
        files={"file": ("cover.jpg", make_image((900, 1600)), "image/jpeg")},
    )
    assert cover.status_code == 200, cover.text
    url = cover.json()["cover_url"]
    assert url and "/reels/" in url
    assert client.get(url).status_code == 200

    removed = client.delete(f"/api/admin/reels/{reel['id']}/cover", headers=headers)
    assert removed.json()["cover_url"] is None
    assert client.get(url).status_code == 404


def test_only_content_staff_choose_reels(client: TestClient, admin: User) -> None:
    body = {"url": "instagram.com/reel/C9xYz_12-ab"}
    manager = admin_headers(client)
    viewer = _invite(client, manager, "VIEWER", "viewer@example.com")
    editor = _invite(client, manager, "EDITOR", "editor@example.com")
    assert client.post("/api/admin/reels", headers=viewer, json=body).status_code == 403
    assert client.post("/api/admin/reels", headers=editor, json=body).status_code == 201
    owner = sign_in(client, "03990010")
    assert client.get("/api/admin/reels", headers=owner).status_code == 403
    assert client.post("/api/admin/reels", json=body).status_code == 401


def test_a_youtube_short_is_a_reel_with_its_own_thumbnail(
    client: TestClient, admin: User, _no_network: list[str]
) -> None:
    headers = admin_headers(client)
    added = client.post(
        "/api/admin/reels",
        headers=headers,
        json={"url": "https://youtube.com/shorts/3Np8hKhrbB4?si=abc", "is_published": True},
    )
    assert added.status_code == 201, added.text
    reel = added.json()
    assert reel["provider"] == "youtube"
    assert reel["url"] == "https://www.youtube.com/shorts/3Np8hKhrbB4"
    assert reel["embed_url"].startswith("https://www.youtube-nocookie.com/embed/3Np8hKhrbB4?")
    # No cover was uploaded, so the Short's own thumbnail became one, stored here.
    assert _no_network == ["3Np8hKhrbB4"]
    assert reel["cover_url"] and "/reels/" in reel["cover_url"]
    assert client.get(reel["cover_url"]).status_code == 200

    # The same video through another YouTube link is the same reel.
    again = client.post(
        "/api/admin/reels", headers=headers, json={"url": "https://youtu.be/3Np8hKhrbB4"}
    )
    assert again.status_code == 409


def test_an_instagram_reel_fetches_no_thumbnail(
    client: TestClient, admin: User, _no_network: list[str]
) -> None:
    added = client.post(
        "/api/admin/reels",
        headers=admin_headers(client),
        json={"url": "instagram.com/reel/C9xYz_12-ab"},
    )
    assert added.json()["provider"] == "instagram"
    assert added.json()["cover_url"] is None
    assert _no_network == []
