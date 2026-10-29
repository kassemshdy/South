"""The site menu an administrator shows, hides, reorders and renames."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.menu import ITEMS
from app.models.user import User
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_permissions import _invite


def test_a_fresh_site_shows_every_item_in_the_default_order(client: TestClient) -> None:
    items = client.get("/api/menu").json()["items"]
    assert [item["id"] for item in items] == list(ITEMS)
    assert all(item["visible"] and item["label_ar"] is None for item in items)


def test_the_manager_reorders_hides_and_renames(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    saved = client.put(
        "/api/admin/menu",
        headers=headers,
        json={
            "items": [
                {"id": "products", "label_ar": f"  {ar('business.first')}  ", "label_en": " "},
                {"id": "home", "visible": False},
                {"id": "nowhere"},
                {"id": "products", "visible": False},
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    items = client.get("/api/menu").json()["items"]
    assert [item["id"] for item in items][:2] == ["products", "home"]
    assert items[0]["label_ar"] == ar("business.first") and items[0]["label_en"] is None
    assert items[1]["visible"] is False
    assert "nowhere" not in [item["id"] for item in items], "only pages that exist"
    assert sorted(item["id"] for item in items) == sorted(ITEMS), "a missing item comes back"


def test_only_content_staff_change_the_menu(client: TestClient, admin: User) -> None:
    manager = admin_headers(client)
    support = _invite(client, manager, "SUPPORT", "support-menu@example.com")
    editor = _invite(client, manager, "EDITOR", "editor-menu@example.com")
    body = {"items": [{"id": "home", "visible": False}]}
    assert client.put("/api/admin/menu", json=body).status_code == 401
    assert client.put("/api/admin/menu", headers=support, json=body).status_code == 403
    assert client.put("/api/admin/menu", headers=editor, json=body).status_code == 200


def test_a_label_is_short(client: TestClient, admin: User) -> None:
    body = {"items": [{"id": "home", "label_en": "x" * 41}]}
    assert client.put("/api/admin/menu", headers=admin_headers(client), json=body).status_code == 422
