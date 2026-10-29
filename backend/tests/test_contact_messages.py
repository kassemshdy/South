"""The floating contact form: anyone may write, only an administrator reads."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import engine
from app.models.contact import ContactMessage
from app.models.user import User
from app.services import telegram_archive
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

URL = "/api/contact-messages"
ADMIN_URL = "/api/admin/contact-messages"


def _payload(**overrides: object) -> dict[str, object]:
    return {
        "name": ar("identity.full_name"),
        "phone": "03 456 789",
        "topic": "question",
        "message": ar("talent.services_offered"),
        "page_path": "/products?q=secret#top",
        **overrides,
    }


def test_a_visitor_sends_one_and_an_administrator_reads_it(
    client: TestClient, admin: User
) -> None:
    sent = client.post(URL, json=_payload())
    assert sent.status_code == 201, sent.text
    # Nothing about the stored row comes back.
    assert set(sent.json()) == {"message"}

    listed = client.get(ADMIN_URL, headers=admin_headers(client))
    assert listed.status_code == 200, listed.text
    [entry] = listed.json()
    assert entry["name"] == ar("identity.full_name")
    assert entry["phone"] == "+9613456789"
    assert entry["topic"] == "question"
    assert entry["message"] == ar("talent.services_offered")
    # The path only: a query string can carry what someone searched for.
    assert entry["page_path"] == "/products"

    removed = client.delete(f"{ADMIN_URL}/{entry['id']}", headers=admin_headers(client))
    assert removed.status_code == 200, removed.text
    assert client.get(ADMIN_URL, headers=admin_headers(client)).json() == []


def test_an_email_alone_is_enough_but_some_way_to_answer_is_required(
    client: TestClient,
) -> None:
    by_email = client.post(URL, json=_payload(phone=None, email="visitor@example.com"))
    assert by_email.status_code == 201, by_email.text

    neither = client.post(URL, json=_payload(phone="", email=""))
    assert neither.status_code == 422
    assert neither.json()["error"]["code"] == "contact_reach_required"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"message": "hi"},
        {"message": "x" * 2001},
        {"topic": "spam"},
        {"email": "not-an-email"},
    ],
)
def test_invalid_input_is_refused(client: TestClient, overrides: dict[str, object]) -> None:
    assert client.post(URL, json=_payload(**overrides)).status_code == 422


def test_text_is_cleaned_and_sql_is_stored_as_plain_text(
    client: TestClient, db: Session
) -> None:
    """Control characters (a NUL included, which Postgres refuses) are
    dropped and the text trimmed; quotes and SQL keywords are kept as typed,
    because every query is parameterised and they are only text."""
    injection = "'; DROP TABLE users; --"
    sent = client.post(
        URL,
        json=_payload(name=f"  {injection}\x00 ", message=f"{injection}\x07\nline two\r\n"),
    )
    assert sent.status_code == 201, sent.text

    row = db.query(ContactMessage).one()
    assert row.name == injection
    assert row.message == f"{injection}\nline two"
    assert inspect(engine).has_table("users")


def test_a_configured_captcha_refuses_a_message_with_no_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    refused = client.post(URL, json=_payload())
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "captcha_required"


def test_one_sender_is_rate_limited(client: TestClient) -> None:
    headers = {"X-Forwarded-For": "198.51.100.41"}
    limit = get_settings().contact_per_ip_limit
    for _ in range(limit):
        assert client.post(URL, json=_payload(), headers=headers).status_code == 201
    assert client.post(URL, json=_payload(), headers=headers).status_code == 429


def test_only_an_administrator_reads_them(client: TestClient) -> None:
    client.post(URL, json=_payload())
    assert client.get(ADMIN_URL).status_code == 401
    assert client.get(ADMIN_URL, headers=sign_in(client, "03993002")).status_code == 403


def test_a_solved_message_moves_to_the_archive_and_can_come_back(
    client: TestClient, admin: User
) -> None:
    assert client.post(URL, json=_payload()).status_code == 201
    headers = admin_headers(client)
    [entry] = client.get(ADMIN_URL, headers=headers).json()

    solved = client.post(f"{ADMIN_URL}/{entry['id']}/solve", headers=headers)
    assert solved.status_code == 200, solved.text
    assert client.get(ADMIN_URL, headers=headers).json() == []
    archive = client.get(ADMIN_URL, params={"solved": True}, headers=headers).json()
    assert [row["id"] for row in archive] == [entry["id"]]

    reopened = client.post(f"{ADMIN_URL}/{entry['id']}/reopen", headers=headers)
    assert reopened.status_code == 200, reopened.text
    assert [row["id"] for row in client.get(ADMIN_URL, headers=headers).json()] == [entry["id"]]


def test_an_owner_cannot_solve_one(client: TestClient, admin: User) -> None:
    assert client.post(URL, json=_payload()).status_code == 201
    [entry] = client.get(ADMIN_URL, headers=admin_headers(client)).json()
    owner = sign_in(client, "03990002")
    assert client.post(f"{ADMIN_URL}/{entry['id']}/solve", headers=owner).status_code == 403


def test_it_is_copied_to_the_telegram_archive() -> None:
    assert "contact_messages" in telegram_archive.ARCHIVED_TABLES
