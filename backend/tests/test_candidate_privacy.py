"""The candidate fields that are private stay out of every public schema.

``team_message`` is a note to the team, ``cv_storage_key`` points into private
storage and ``last_confirmed_at`` is staff bookkeeping. The same guard as the
identity columns: adding one to a public ``*Out`` class is a disclosure.
"""

from __future__ import annotations

from app.schemas import talent as talent_schemas

PRIVATE = {"team_message", "cv_storage_key", "last_confirmed_at"}
PUBLIC = ("TalentSummaryOut", "TalentDetailOut")


def test_private_candidate_fields_are_not_in_public_schemas() -> None:
    for name in PUBLIC:
        schema = getattr(talent_schemas, name)
        assert not PRIVATE & set(schema.model_fields), name
