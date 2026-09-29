"""Each public page's cover photograph: set by an administrator, read by anyone."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.page_cover import PAGE_COVER_KEYS
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.test_uploads_and_urls import make_image


def _upload(client: TestClient, headers: dict[str, str], key: str = "products") -> dict[str, object]:
    response = client.post(
        f"/api/admin/page-covers/{key}",
        headers=headers,
        files={"file": ("cover.jpg", make_image((2400, 900)), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_no_page_has_a_cover_until_one_is_set(client: TestClient) -> None:
    """Every page shows the site's default until an administrator replaces it."""
    assert client.get("/api/page-covers").json() == {}


def test_an_administrator_sets_a_cover_and_every_visitor_sees_it(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    set_cover = _upload(client, headers)
    url = set_cover["image_url"]
    assert isinstance(url, str) and url.startswith("/media/pages/")

    # Public, no token: this is what the page reads.
    assert client.get("/api/page-covers").json() == {"products": url}
    assert client.get(url).status_code == 200


def test_the_admin_list_names_every_page_in_order(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    _upload(client, headers, "talent")
    listed = client.get("/api/admin/page-covers", headers=headers).json()
    assert [row["page_key"] for row in listed] == list(PAGE_COVER_KEYS)
    assert {row["page_key"] for row in listed if row["image_url"]} == {"talent"}


def test_replacing_a_cover_removes_the_old_file(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    first = _upload(client, headers)
    second = _upload(client, headers)
    assert first["image_url"] != second["image_url"]
    assert client.get(str(first["image_url"])).status_code == 404
    assert client.get("/api/page-covers").json() == {"products": second["image_url"]}


def test_resetting_returns_the_page_to_the_default(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    set_cover = _upload(client, headers)
    reset = client.delete("/api/admin/page-covers/products", headers=headers)
    assert reset.status_code == 200, reset.text
    assert reset.json()["image_url"] is None
    assert client.get("/api/page-covers").json() == {}
    assert client.get(str(set_cover["image_url"])).status_code == 404


def test_a_rejected_upload_leaves_the_current_cover_alone(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    set_cover = _upload(client, headers)
    refused = client.post(
        "/api/admin/page-covers/products",
        headers=headers,
        files={"file": ("cover.jpg", b"not an image", "image/jpeg")},
    )
    assert refused.status_code == 415, refused.text
    assert client.get("/api/page-covers").json() == {"products": set_cover["image_url"]}


def test_an_unknown_page_is_refused(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    response = client.post(
        "/api/admin/page-covers/not-a-page",
        headers=headers,
        files={"file": ("cover.jpg", make_image(), "image/jpeg")},
    )
    assert response.status_code == 404


def test_only_an_administrator_can_set_or_reset_one(client: TestClient) -> None:
    anonymous = client.post(
        "/api/admin/page-covers/products",
        files={"file": ("cover.jpg", make_image(), "image/jpeg")},
    )
    assert anonymous.status_code == 401

    owner = sign_in(client, "03730001")
    assert (
        client.post(
            "/api/admin/page-covers/products",
            headers=owner,
            files={"file": ("cover.jpg", make_image(), "image/jpeg")},
        ).status_code
        == 403
    )
    assert client.delete("/api/admin/page-covers/products", headers=owner).status_code == 403
    assert client.get("/api/admin/page-covers", headers=owner).status_code == 403
