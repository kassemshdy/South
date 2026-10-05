"""The site's static pages: their text is written by an admin, read by anyone."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import admin_headers, sign_in

EMPTY = {
    "key": "about",
    "title_ar": None,
    "title_en": None,
    "summary_ar": None,
    "summary_en": None,
    "body_ar": None,
    "body_en": None,
}

# English text only: Arabic test strings live in the fixture catalog, and
# whether a page stores one language or two is the same code either way.
TEXT = {
    "title_en": "About us",
    "summary_en": "A short paragraph for the footer.",
    "body_en": "First paragraph.\r\n\r\nSecond paragraph with https://example.org in it.",
}


def test_a_page_is_its_built_in_text_until_an_administrator_writes_it(
    client: TestClient,
) -> None:
    """Every field null: the page shows the text it ships with."""
    assert client.get("/api/pages/about").json() == EMPTY


def test_an_administrator_writes_a_page_and_every_visitor_reads_it(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    response = client.put("/api/admin/pages/about", headers=headers, json=TEXT)
    assert response.status_code == 200, response.text

    public = client.get("/api/pages/about").json()
    assert public["title_en"] == "About us"
    assert public["summary_en"] == "A short paragraph for the footer."
    # Paragraph breaks survive, in one form, whatever the admin pasted from.
    assert (
        public["body_en"] == "First paragraph.\n\nSecond paragraph with https://example.org in it."
    )
    # A field not sent stays unset, so the Arabic page keeps its built-in text.
    assert public["body_ar"] is None
    assert client.get("/api/admin/pages", headers=headers).json() == [public]


def test_emptying_every_field_restores_the_built_in_text(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    client.put("/api/admin/pages/about", headers=headers, json=TEXT)
    blank = {key: "  " for key in TEXT}
    response = client.put("/api/admin/pages/about", headers=headers, json=blank)
    assert response.status_code == 200, response.text
    assert client.get("/api/pages/about").json() == EMPTY


def test_only_known_pages_exist(client: TestClient, admin: User) -> None:
    """A page is a route the site already has, not a free-form URL."""
    headers = admin_headers(client)
    assert client.get("/api/pages/anything").status_code == 404
    assert client.put("/api/admin/pages/anything", headers=headers, json=TEXT).status_code == 404


def test_only_an_administrator_writes_a_page(client: TestClient, admin: User) -> None:
    assert client.put("/api/admin/pages/about", json=TEXT).status_code == 401
    headers = sign_in(client, "03730001")
    assert client.put("/api/admin/pages/about", headers=headers, json=TEXT).status_code == 403
    assert client.get("/api/admin/pages", headers=headers).status_code == 403
    assert client.get("/api/pages/about").json() == EMPTY
