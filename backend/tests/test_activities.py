"""Development activities (29 Oct 2026): announced in a carousel on the
home page and on a page of their own, written and archived by staff only."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1.home import SECTIONS, HomeSection, _normalise
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar
from tests.test_permissions import _invite


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (800, 450), (200, 220, 210)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _body(**extra: object) -> dict[str, object]:
    return {
        "title": ar("business.first"),
        "body": ar("business.applicant_description"),
        **extra,
    }


def _create(
    client: TestClient, headers: dict[str, str], *, image: bool = True, **extra: object
) -> dict:
    created = client.post("/api/admin/activities", headers=headers, json=_body(**extra))
    assert created.status_code == 201, created.text
    activity = created.json()
    if image:
        uploaded = client.post(
            f"/api/admin/activities/{activity['id']}/image",
            headers=headers,
            files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
        )
        assert uploaded.status_code == 200, uploaded.text
        activity = uploaded.json()
    return activity


def test_an_archived_activity_leaves_every_public_route(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    kept = _create(client, headers, slug="kept")
    archived = _create(client, headers, slug="archived")
    put = client.put(
        f"/api/admin/activities/{archived['id']}", headers=headers, json={"is_archived": True}
    )
    assert put.status_code == 200 and put.json()["is_archived"] is True

    assert [a["slug"] for a in client.get("/api/activities").json()] == [kept["slug"]]
    assert client.get(f"/api/activities/{kept['slug']}").status_code == 200
    assert client.get(f"/api/activities/{archived['slug']}").status_code == 404

    # Kept again, it is back.
    client.put(
        f"/api/admin/activities/{archived['id']}", headers=headers, json={"is_archived": False}
    )
    assert client.get(f"/api/activities/{archived['slug']}").status_code == 200


def test_no_photograph_no_announcement(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    bare = _create(client, headers, image=False, slug="bare")
    assert client.get("/api/activities").json() == []
    assert client.get(f"/api/activities/{bare['slug']}").status_code == 404


def test_ordered_by_sort_order_then_newest(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    _create(client, headers, slug="older")
    _create(client, headers, slug="newer")
    _create(client, headers, slug="pinned", sort_order=-1)
    slugs = [a["slug"] for a in client.get("/api/activities").json()]
    assert slugs == ["pinned", "newer", "older"]


def test_staff_write_edit_and_delete(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    starts = datetime.now(UTC) + timedelta(days=5)
    activity = _create(
        client,
        headers,
        slug="dated",
        starts_at=starts.isoformat(),
        ends_at=(starts + timedelta(hours=2)).isoformat(),
        location=ar("business.first"),
    )
    assert activity["image_url"]

    edited = client.put(
        f"/api/admin/activities/{activity['id']}",
        headers=headers,
        json={"summary": ar("business.first")},
    )
    assert edited.status_code == 200 and edited.json()["summary"] == ar("business.first")

    backwards = client.put(
        f"/api/admin/activities/{activity['id']}",
        headers=headers,
        json={"ends_at": (starts - timedelta(hours=1)).isoformat()},
    )
    assert backwards.status_code == 422

    listed = client.get("/api/admin/activities", headers=headers).json()
    assert [a["slug"] for a in listed] == ["dated"]

    deleted = client.delete(f"/api/admin/activities/{activity['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get("/api/activities").json() == []


def test_only_content_staff_may_write(client: TestClient, admin: User) -> None:
    manager = admin_headers(client)
    editor = _invite(client, manager, "EDITOR", "editor@example.com")
    support = _invite(client, manager, "SUPPORT", "support@example.com")
    owner = sign_in(client, "03960202")

    _create(client, editor, slug="by-editor")
    assert client.post("/api/admin/activities", headers=support, json=_body()).status_code == 403
    assert client.post("/api/admin/activities", headers=owner, json=_body()).status_code == 403
    assert client.post("/api/admin/activities", json=_body()).status_code == 401
    assert client.get("/api/admin/activities", headers=owner).status_code == 403


def test_the_carousel_arrives_shown_after_the_slogan_on_a_saved_layout(
    client: TestClient, admin: User
) -> None:
    assert "activities" in SECTIONS
    saved = [
        {"id": name, "visible": True} for name in ("cover", "hero", "slogan", "search")
    ]
    # A layout saved before the section existed: it arrives in place, shown.
    layout = _normalise([HomeSection(**section) for section in saved])
    ids = [section.id for section in layout]
    assert ids[:5] == ["cover", "hero", "slogan", "activities", "search"]
    assert next(s for s in layout if s.id == "activities").visible is True

    # Hidden by an administrator, it stays hidden.
    hidden = _normalise(
        [*(HomeSection(**s) for s in saved), HomeSection(id="activities", visible=False)]
    )
    assert next(s for s in hidden if s.id == "activities").visible is False
