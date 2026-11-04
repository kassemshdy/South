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


def test_upcoming_first_then_undated_then_finished(client: TestClient, admin: User) -> None:
    """The owners' ticket of 31 Oct 2026: upcoming and current first, the
    soonest first; finished ones last, the most recent first."""
    headers = admin_headers(client)
    now = datetime.now(UTC)

    def at(days: int) -> str:
        return (now + timedelta(days=days)).isoformat()

    _create(client, headers, slug="later", starts_at=at(10))
    _create(client, headers, slug="soon", starts_at=at(2))
    _create(client, headers, slug="undated")
    _create(client, headers, slug="long-ago", starts_at=at(-30), ends_at=at(-29))
    _create(client, headers, slug="last-week", starts_at=at(-7), ends_at=at(-6))
    _create(client, headers, slug="running", starts_at=at(-1), ends_at=at(3))
    slugs = [a["slug"] for a in client.get("/api/activities").json()]
    assert slugs == ["running", "soon", "later", "undated", "last-week", "long-ago"]
    page = [a["slug"] for a in client.get("/api/activities?limit=2&offset=2").json()]
    assert page == ["later", "undated"]


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
    saved = [{"id": name, "visible": True} for name in ("cover", "hero", "slogan", "search")]
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


# --- The carousel (the owners' ticket, 31 Oct 2026) ------------------------


def _slides(client: TestClient) -> list[str | None]:
    return [slide["title"] for slide in client.get("/api/carousel").json()]


def test_a_new_photograph_puts_the_activity_first_in_the_carousel(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    first = _create(client, headers, slug="first", title="First one")
    second = _create(client, headers, slug="second", title="Second one")
    assert _slides(client) == ["Second one", "First one"]
    assert first["in_carousel"] and second["in_carousel"]
    slide = client.get("/api/carousel").json()[0]
    assert slide["href"] == "/activities/second" and slide["external"] is False


def test_taking_a_slide_out_keeps_the_activity_listed(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    activity = _create(client, headers, slug="kept", title="Kept one")
    removed = client.put(
        f"/api/admin/activities/{activity['id']}", headers=headers, json={"in_carousel": False}
    )
    assert removed.json()["in_carousel"] is False
    assert _slides(client) == []
    assert [a["slug"] for a in client.get("/api/activities").json()] == ["kept"]
    # A later edit does not put it back on its own.
    client.put(f"/api/admin/activities/{activity['id']}", headers=headers, json={"location": "x"})
    assert _slides(client) == []


def test_archiving_takes_it_out_of_the_carousel(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    activity = _create(client, headers, slug="gone", title="Gone")
    client.put(
        f"/api/admin/activities/{activity['id']}", headers=headers, json={"is_archived": True}
    )
    assert _slides(client) == []
    assert client.get("/api/admin/carousel", headers=headers).json()["slides"] == []


def test_finished_activities_leave_unless_the_setting_is_off(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    now = datetime.now(UTC)
    _create(
        client,
        headers,
        slug="done",
        title="Done",
        starts_at=(now - timedelta(days=3)).isoformat(),
        ends_at=(now - timedelta(days=2)).isoformat(),
    )
    assert _slides(client) == []
    managed = client.get("/api/admin/carousel", headers=headers).json()
    assert managed["autoremove_expired"] is True
    assert managed["slides"][0]["hidden_reason"] == "ENDED"
    client.put("/api/admin/carousel/settings", headers=headers, json={"autoremove_expired": False})
    assert _slides(client) == ["Done"]


def test_custom_slides_are_added_reordered_and_removed(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    _create(client, headers, slug="a", title="Activity A")
    added = client.post(
        "/api/admin/carousel/custom",
        headers=headers,
        files={"file": ("b.jpg", _jpeg(), "image/jpeg")},
        data={"title": "Partner", "link_url": "https://partner.example"},
    )
    assert added.status_code == 200, added.text
    assert _slides(client) == ["Partner", "Activity A"]
    custom = client.get("/api/carousel").json()[0]
    assert custom["href"] == "https://partner.example" and custom["external"] is True

    ids = [slide["id"] for slide in added.json()["slides"]]
    client.put("/api/admin/carousel/order", headers=headers, json={"slide_ids": ids[::-1]})
    assert _slides(client) == ["Activity A", "Partner"]

    client.delete(f"/api/admin/carousel/{ids[0]}", headers=headers)
    assert _slides(client) == ["Activity A"]

    refused = client.post(
        "/api/admin/carousel/custom",
        headers=headers,
        files={"file": ("b.jpg", _jpeg(), "image/jpeg")},
        data={"link_url": "javascript:alert(1)"},
    )
    assert refused.status_code == 422


def test_registration_link_must_be_http(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    bad = client.post(
        "/api/admin/activities", headers=headers, json=_body(register_url="javascript:x")
    )
    assert bad.status_code == 422
    good = _create(
        client,
        headers,
        slug="reg",
        register_url="https://forms.example/x",
        register_label="  ",
        kind="WORKSHOP",
    )
    public = client.get("/api/activities/reg").json()
    assert public["register_url"] == "https://forms.example/x"
    assert public["register_label"] is None and public["kind"] == "WORKSHOP"
    assert public["show_calendar"] is True and good["kind"] == "WORKSHOP"


# --- Signing up on the site (the owners' ticket, 4 Nov 2026) -----------------


def _sign_up(client: TestClient, slug: str, phone: str = "70 111 444"):
    return client.post(
        f"/api/activities/{slug}/register",
        json={"full_name": ar("order.customer"), "phone_number": phone},
    )


def test_people_sign_up_on_the_site_by_default_and_only_staff_see_who(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    activity = _create(client, headers, slug="on-site")
    assert activity["registration_mode"] == "ON_SITE"

    signed = _sign_up(client, "on-site")
    assert signed.status_code == 201, signed.text

    public = client.get("/api/activities/on-site").text
    assert "111" not in public and ar("order.customer") not in public

    listed = client.get(
        f"/api/admin/activities/{activity['id']}/registrations", headers=headers
    ).json()
    assert [row["full_name"] for row in listed] == [ar("order.customer")]
    assert listed[0]["phone_number"].endswith("70111444")
    assert client.get("/api/admin/activities", headers=headers).json()[0]["registration_count"] == 1
    assert client.get(f"/api/admin/activities/{activity['id']}/registrations").status_code == 401


def test_an_external_link_or_no_sign_up_closes_the_form(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    _create(
        client,
        headers,
        slug="external",
        registration_mode="EXTERNAL",
        register_url="https://forms.example/x",
    )
    _create(client, headers, slug="none", registration_mode="NONE")
    assert _sign_up(client, "external").status_code == 422
    assert _sign_up(client, "none").status_code == 422

    # External needs its link, on create and on edit.
    refused = client.post(
        "/api/admin/activities", headers=headers, json=_body(registration_mode="EXTERNAL")
    )
    assert refused.status_code == 422
    on_site = _create(client, headers, slug="switch")
    switched = client.put(
        f"/api/admin/activities/{on_site['id']}",
        headers=headers,
        json={"registration_mode": "EXTERNAL"},
    )
    assert switched.status_code == 422


def test_no_sign_up_once_it_has_ended_or_while_hidden(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    past = datetime.now(UTC) - timedelta(days=2)
    _create(client, headers, slug="ended", starts_at=past.isoformat())
    _create(client, headers, slug="no-photo", image=False)

    assert _sign_up(client, "ended").status_code == 422
    assert _sign_up(client, "no-photo").status_code == 404
