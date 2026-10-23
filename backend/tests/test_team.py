"""The about page's team section: six slots an administrator fills."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar
from tests.test_uploads_and_urls import make_image


def test_the_section_shows_only_the_slots_an_administrator_filled(
    client: TestClient, admin: User
) -> None:
    assert client.get("/api/team").json() == []
    headers = admin_headers(client)

    captioned = client.put(
        "/api/admin/team/2",
        headers=headers,
        json={"caption_ar": ar("team.caption"), "caption_en": "  "},
    )
    assert captioned.status_code == 200, captioned.text
    photo = client.post(
        "/api/admin/team/2/photo",
        headers=headers,
        files={"file": ("face.jpg", make_image((800, 800)), "image/jpeg")},
    )
    assert photo.status_code == 200, photo.text

    public = client.get("/api/team").json()
    assert [entry["slot"] for entry in public] == [2]
    assert public[0]["caption_ar"] == ar("team.caption")
    assert public[0]["caption_en"] is None  # blank means none
    assert public[0]["photo_url"]
    assert len(client.get("/api/admin/team", headers=headers).json()) == 6

    # Emptied again, the slot is gone from the page.
    client.delete("/api/admin/team/2/photo", headers=headers)
    client.put("/api/admin/team/2", headers=headers, json={"caption_ar": "", "caption_en": ""})
    assert client.get("/api/team").json() == []


def test_only_six_slots_and_only_administrators(client: TestClient, admin: User) -> None:
    assert client.put(
        "/api/admin/team/7", headers=admin_headers(client), json={"caption_ar": ar("team.caption")}
    ).status_code == 404
    owner = sign_in(client, "03990010")
    assert client.put(
        "/api/admin/team/1", headers=owner, json={"caption_ar": ar("team.caption")}
    ).status_code == 403
    assert client.put("/api/admin/team/1", json={"caption_ar": ar("team.caption")}).status_code == 401
