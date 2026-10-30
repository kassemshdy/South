"""The home page's sections.

Asserted: a fresh site lists every section with only the page's original
three shown, so a release changes nothing a visitor sees; an
administrator's order and hidden sections are kept, unknown names dropped
and missing ones appended hidden; only staff who edit content may
save it. The stories row has its own tests, in ``test_stories.py``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.home import SECTIONS
from app.models.user import User
from tests.conftest import admin_headers, sign_in


def test_a_fresh_site_shows_only_the_original_sections(client: TestClient) -> None:
    layout = client.get("/api/home/layout").json()["sections"]
    assert [s["id"] for s in layout] == list(SECTIONS)
    shown = [s["id"] for s in layout if s["visible"]]
    # The carousel is the one exception: it is empty until an activity exists.
    assert shown == ["cover", "hero", "slogan", "activities"], (
        "new sections wait for an administrator"
    )


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
    assert {s["id"]: s["visible"] for s in layout}["news"] is False, "appended hidden"


def test_only_staff_may_save_the_layout(client: TestClient, admin: User) -> None:
    owner = sign_in(client, "03960101")
    body = {"sections": [{"id": "news", "visible": True}]}
    assert client.put("/api/admin/home/layout", headers=owner, json=body).status_code == 403
    assert client.put("/api/admin/home/layout", json=body).status_code == 401
