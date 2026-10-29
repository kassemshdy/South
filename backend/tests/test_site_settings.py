"""The site's own contact details and social accounts: set by an admin, read by anyone."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import admin_headers, sign_in

EMPTY = {
    "contact_phone": None,
    "contact_whatsapp": None,
    "contact_email": None,
    "social_facebook": None,
    "social_instagram": None,
    "home_video": None,
    "offer_video": None,
}

FULL = {
    "contact_phone": "03 123 456",
    "contact_whatsapp": "+961 71 234 567",
    "contact_email": "hello@example.org",
    "social_facebook": "facebook.com/janoubna",
    "social_instagram": "https://www.instagram.com/janoubna/",
}


def test_nothing_is_set_until_an_administrator_sets_it(client: TestClient) -> None:
    """Unset means the site shows nothing for it -- never a placeholder."""
    assert client.get("/api/site-settings").json() == EMPTY


def test_an_administrator_sets_them_and_every_visitor_sees_them(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    response = client.put("/api/admin/site-settings", headers=headers, json=FULL)
    assert response.status_code == 200, response.text

    public = client.get("/api/site-settings").json()
    # Normalised the way a listing's details are.
    assert public["contact_phone"] == "+9613123456"
    assert public["contact_whatsapp"] == "+96171234567"
    assert public["contact_email"] == "hello@example.org"
    assert public["social_facebook"] == "https://facebook.com/janoubna"
    assert public["social_instagram"] == "https://www.instagram.com/janoubna/"
    assert client.get("/api/admin/site-settings", headers=headers).json() == public


def test_an_empty_field_clears_that_setting(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    client.put("/api/admin/site-settings", headers=headers, json=FULL)
    cleared = {**FULL, "contact_email": "", "social_facebook": None}
    response = client.put("/api/admin/site-settings", headers=headers, json=cleared)
    assert response.status_code == 200, response.text

    public = client.get("/api/site-settings").json()
    assert public["contact_email"] is None
    assert public["social_facebook"] is None
    assert public["social_instagram"] is not None


def test_a_link_that_is_not_the_platform_is_refused(client: TestClient, admin: User) -> None:
    """Rendered as a link on every page, so it must be what it says it is."""
    headers = admin_headers(client)
    for bad in (
        {"social_instagram": "javascript:alert(1)"},
        {"social_instagram": "https://evil.example/instagram.com"},
        {"social_facebook": "https://instagram.com/janoubna"},
        {"contact_email": "not an address"},
        {"contact_phone": "abc"},
    ):
        response = client.put("/api/admin/site-settings", headers=headers, json=bad)
        assert response.status_code == 422, (bad, response.text)
    assert client.get("/api/site-settings").json() == EMPTY


def test_only_an_administrator_can_read_the_admin_view_or_change_them(
    client: TestClient, admin: User
) -> None:
    owner_headers = sign_in(client, "03730001")
    assert client.put("/api/admin/site-settings", json=FULL).status_code == 401
    assert client.get("/api/admin/site-settings").status_code == 401
    assert (
        client.put("/api/admin/site-settings", headers=owner_headers, json=FULL).status_code == 403
    )
    assert client.get("/api/site-settings").json() == EMPTY


def test_the_homepage_video_is_stored_as_its_id(client: TestClient, admin: User) -> None:
    """Round 3: an administrator changes the homepage video by pasting a link.
    Only the id is kept, so nothing typed reaches the page; a link that is
    not YouTube is refused."""
    headers = admin_headers(client)
    saved = client.put(
        "/api/admin/site-settings",
        headers=headers,
        json={**FULL, "home_video": "https://youtu.be/dQw4w9WgXcQ?t=42"},
    )
    assert saved.status_code == 200, saved.text
    assert client.get("/api/site-settings").json()["home_video"] == "dQw4w9WgXcQ"

    refused = client.put(
        "/api/admin/site-settings",
        headers=headers,
        json={**FULL, "home_video": "https://example.com/watch?v=dQw4w9WgXcQ"},
    )
    assert refused.status_code == 422, refused.text
    assert client.get("/api/site-settings").json()["home_video"] == "dQw4w9WgXcQ"


def test_the_offer_page_video_is_stored_as_its_id(client: TestClient, admin: User) -> None:
    """The "how to register" video on /offer, set the way the homepage's is:
    a pasted link kept as its id, and a link that is not YouTube refused."""
    headers = admin_headers(client)
    saved = client.put(
        "/api/admin/site-settings",
        headers=headers,
        json={**FULL, "offer_video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5"},
    )
    assert saved.status_code == 200, saved.text
    assert client.get("/api/site-settings").json()["offer_video"] == "dQw4w9WgXcQ"

    refused = client.put(
        "/api/admin/site-settings",
        headers=headers,
        json={**FULL, "offer_video": "https://vimeo.com/123"},
    )
    assert refused.status_code == 422, refused.text

    cleared = client.put("/api/admin/site-settings", headers=headers, json=FULL)
    assert cleared.status_code == 200, cleared.text
    assert client.get("/api/site-settings").json()["offer_video"] is None


def test_the_credentials_message_is_the_administrator_s_and_not_public(
    client: TestClient, admin: User
) -> None:
    """The owners' wording for the WhatsApp message a password is sent in,
    which may carry a private group's invite link: an administrator sets it,
    and the public settings never show it."""
    headers = admin_headers(client)
    path = "/api/admin/site-settings/credentials-message"
    assert client.get(path, headers=headers).json() == {"message": None}

    text = "Welcome {phone} / {password}\nhttps://chat.whatsapp.com/example"
    saved = client.put(path, headers=headers, json={"message": text})
    assert saved.status_code == 200, saved.text
    assert client.get(path, headers=headers).json() == {"message": text}
    assert "chat.whatsapp.com" not in client.get("/api/site-settings").text

    # Empty goes back to the site's default wording.
    assert client.put(path, headers=headers, json={"message": "  "}).json() == {"message": None}


def test_a_credentials_message_without_the_login_is_refused(
    client: TestClient, admin: User
) -> None:
    path = "/api/admin/site-settings/credentials-message"
    refused = client.put(
        path, headers=admin_headers(client), json={"message": "Welcome {phone}"}
    )
    assert refused.status_code == 422, refused.text


def test_only_an_administrator_reads_or_sets_the_credentials_message(
    client: TestClient,
) -> None:
    path = "/api/admin/site-settings/credentials-message"
    assert client.get(path).status_code == 401
    owner = sign_in(client, "03990001")
    assert client.get(path, headers=owner).status_code == 403
    assert client.put(path, headers=owner, json={"message": None}).status_code == 403
