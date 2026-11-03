"""Collab reels on the home page.

Asserted: only an Instagram post or reel link is accepted, and only its
kind and shortcode are kept; only content staff may manage reels; the
public list shows published reels that have a cover, and nothing else.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ValidationError
from app.core.urls import instagram_post
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.test_uploads_and_urls import make_image


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://www.instagram.com/reel/C8xYz12AbCd/?igsh=abc", ("reel", "C8xYz12AbCd")),
        ("instagram.com/p/C8xYz12AbCd/", ("p", "C8xYz12AbCd")),
        ("https://www.instagram.com/reels/C8xYz12AbCd", ("reel", "C8xYz12AbCd")),
        ("https://www.instagram.com/someshop/reel/C8xYz12AbCd/", ("reel", "C8xYz12AbCd")),
    ],
)
def test_instagram_links_keep_only_the_kind_and_shortcode(
    raw: str, expected: tuple[str, str]
) -> None:
    assert instagram_post(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "https://evil.example/reel/C8xYz12AbCd",
        "https://www.instagram.com/someshop/",
        "javascript:alert(1)",
    ],
)
def test_other_links_are_refused(raw: str) -> None:
    with pytest.raises(ValidationError):
        instagram_post(raw)


def test_a_reel_is_public_once_published_with_a_cover(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/reels",
        headers=headers,
        json={"instagram_url": "https://www.instagram.com/reel/C8xYz12AbCd/", "title": "x"},
    )
    assert created.status_code == 201, created.text
    reel_id = created.json()["id"]
    assert client.get("/api/reels").json() == [], "no cover yet"

    covered = client.post(
        f"/api/admin/reels/{reel_id}/cover",
        headers=headers,
        files={"file": ("cover.jpg", make_image((720, 1280)), "image/jpeg")},
    )
    assert covered.status_code == 200, covered.text
    public = client.get("/api/reels").json()
    assert [(r["instagram_kind"], r["instagram_code"]) for r in public] == [("reel", "C8xYz12AbCd")]

    client.patch(f"/api/admin/reels/{reel_id}", headers=headers, json={"is_published": False})
    assert client.get("/api/reels").json() == []

    assert client.delete(f"/api/admin/reels/{reel_id}", headers=headers).status_code == 200
    assert client.get("/api/admin/reels", headers=headers).json() == []


def test_only_staff_manage_reels(client: TestClient, admin: User) -> None:
    owner = sign_in(client, "03960201")
    body = {"instagram_url": "https://www.instagram.com/reel/C8xYz12AbCd/"}
    assert client.post("/api/admin/reels", headers=owner, json=body).status_code == 403
    assert client.post("/api/admin/reels", json=body).status_code == 401
    refused = client.post(
        "/api/admin/reels",
        headers=admin_headers(client),
        json={"instagram_url": "https://youtube.com/shorts/3Np8hKhrbB4"},
    )
    assert refused.status_code == 422
