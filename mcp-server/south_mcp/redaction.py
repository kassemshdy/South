"""Strip an owner's personal details out of anything an agent reads.

The admin review payloads (``AdminBusinessOut``, ``AdminTalentOut``) carry an
``owner_identity`` block -- legal name, birth year, gender, marital status,
place of civil registration, place of residence -- plus the owner's personal
phone number. An administrator reviewing a listing needs those. An agent
triaging a ticket or writing a feature never does.

That asymmetry is the whole argument for redacting here rather than trusting
the tool list: ticket text and listing content are written by other people, so
they are exactly the kind of input that can talk a model into fetching
something it should not. Data the process never holds cannot be talked out of
it.

The published fields survive on purpose. A shop's own ``phone_number`` and
``whatsapp_number`` are printed on its listing for the whole internet, and the
same distinction is already pinned for error reports in
``backend/tests/test_observability.py``: what an owner *published* is public,
what identifies the *person* is not.
"""

from __future__ import annotations

from typing import Any

#: Keys removed from every payload, at any depth.
REDACTED_KEYS = frozenset(
    {
        "owner_identity",
        "owner_phone",
        "owner_personal_phone",
    }
)

REDACTION_NOTE = "redacted by the MCP server"


def redact(value: Any) -> Any:
    """Return ``value`` with every :data:`REDACTED_KEYS` entry removed.

    A removed key is replaced with a note rather than dropped silently, so a
    model reading the result can tell the difference between "this owner has
    no recorded name" and "you are not allowed to see it" -- and does not go
    looking for another route to the same field.
    """
    if isinstance(value, dict):
        return {
            key: (REDACTION_NOTE if key in REDACTED_KEYS else redact(inner))
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
