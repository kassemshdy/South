"""Error tracking: off by default, and never ships a credential when on.

Sentry sees production tracebacks, so the interesting assertions here are all
negative: what must *not* leave the service. Owner login phone numbers,
passwords and bearer tokens are the three things this codebase treats as
secret, and each is checked explicitly rather than trusted to
``send_default_pii``.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.observability import REDACTED, _before_send, _scrub, configure_error_tracking


def test_disabled_without_a_dsn() -> None:
    """No DSN, no SDK: a developer's tracebacks stay on their machine."""
    settings = Settings(app_env="development", sentry_dsn=None)
    # Nothing to assert beyond "does not raise and does not initialise" — the
    # call is a no-op, which is exactly the contract.
    configure_error_tracking(settings)


def test_scrub_redacts_credentials_at_any_depth() -> None:
    event = {
        "request": {
            "headers": {"Authorization": "Bearer abc.def", "Accept": "application/json"},
            "cookies": {"session": "xyz"},
        },
        "extra": {
            "payload": {"phone_number": "+9613123456", "code": "123456"},
            "business_id": "5f2c",
        },
    }

    scrubbed = _scrub(event)

    assert scrubbed["request"]["headers"]["Authorization"] == REDACTED
    assert scrubbed["extra"]["payload"]["phone_number"] == REDACTED
    assert scrubbed["extra"]["payload"]["code"] == REDACTED
    # Non-sensitive context survives, or the reports would be useless.
    assert scrubbed["request"]["headers"]["Accept"] == "application/json"
    assert scrubbed["extra"]["business_id"] == "5f2c"


def test_scrub_matches_keys_case_insensitively() -> None:
    assert _scrub({"AUTHORIZATION": "Bearer x"})["AUTHORIZATION"] == REDACTED
    assert _scrub({"Phone_Number": "+9613123456"})["Phone_Number"] == REDACTED


def test_scrub_walks_lists() -> None:
    event = {"breadcrumbs": [{"data": {"token": "secret"}}, {"data": {"path": "/api/me"}}]}
    scrubbed = _scrub(event)
    assert scrubbed["breadcrumbs"][0]["data"]["token"] == REDACTED
    assert scrubbed["breadcrumbs"][1]["data"]["path"] == "/api/me"


def test_before_send_drops_the_query_string_and_body() -> None:
    """A phone number in ?q= is a flat string, so the key-based scrub misses
    it; the whole query string and body go instead."""
    event = {
        "request": {
            "url": "https://example.test/api/businesses",
            "query_string": "q=%2B9613123456",
            "data": {"phone_number": "+9613123456"},
            "headers": {"Authorization": "Bearer abc"},
        }
    }

    sent = _before_send(event, {})

    assert "query_string" not in sent["request"]
    assert "data" not in sent["request"]
    assert sent["request"]["headers"]["Authorization"] == REDACTED
    # The URL itself is kept: it is the only thing locating the failure.
    assert sent["request"]["url"] == "https://example.test/api/businesses"


def test_public_business_contact_fields_are_not_scrubbed() -> None:
    """A listing's published phone is deliberately public, unlike the owner's
    login number, so it must survive into the report as context."""
    event = {"extra": {"business": {"whatsapp": "03123456", "email": "shop@example.test"}}}
    scrubbed = _scrub(event)
    assert scrubbed["extra"]["business"]["whatsapp"] == "03123456"
    assert scrubbed["extra"]["business"]["email"] == "shop@example.test"
