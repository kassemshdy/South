"""The identity boundary, as this server sees it.

``backend/tests/test_identity.py`` pins that no public schema carries an
account holder's identity. The admin review payloads deliberately do, because
a human reviewer needs them. This is the matching guard on the agent's side:
those fields must not survive the trip through a tool.
"""

from __future__ import annotations

from south_mcp.redaction import REDACTION_NOTE, redact


def test_owner_identity_never_survives() -> None:
    payload = {
        "id": "b1",
        "name": "A shop",
        "owner_identity": {"full_name": "A Person", "birth_year": 1980},
        "owner_phone": "03000000",
        "owner_personal_phone": "03111111",
    }

    result = redact(payload)

    assert result["owner_identity"] == REDACTION_NOTE
    assert result["owner_phone"] == REDACTION_NOTE
    assert result["owner_personal_phone"] == REDACTION_NOTE
    assert "A Person" not in str(result)
    assert "1980" not in str(result)


def test_a_published_phone_number_is_left_alone() -> None:
    """What a shop prints on its own listing is public and stays readable --
    the same distinction ``test_observability.py`` pins for error reports.

    The field names are the ones ``AdminBusinessOut`` actually serialises
    (``phone``/``whatsapp``, not ``phone_number``), checked against a live
    response: a guard asserting on invented keys would pass while proving
    nothing."""
    payload = {"phone": "03222222", "whatsapp": "+9613911122"}

    assert redact(payload) == payload


def test_redaction_reaches_into_lists_and_nesting() -> None:
    payload = {"items": [{"meta": {"owner_phone": "03000000"}}]}

    assert redact(payload)["items"][0]["meta"]["owner_phone"] == REDACTION_NOTE


def test_non_dict_values_pass_through() -> None:
    assert redact("text") == "text"
    assert redact(7) == 7
    assert redact(None) is None
