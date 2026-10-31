"""Ticket board: «waiting for approval» and «approved» columns.

A ticket the triage routine has fixed, merged into develop and shown on the
develop site waits here for a person to approve the release (the owners'
request, 31 Oct 2026). Moving a ticket into it posts to the Telegram chat,
with a button to the ticket, where a person approves it into APPROVED.

Same shape as c5e1f8a2d3b7: ``ADD VALUE`` outside the transaction, ``BEFORE
'DONE'`` to keep the board's order, and a downgrade that moves the tickets
back to IN_PROGRESS and rebuilds the type without the value.

Revision ID: b9d2e6f4a1c8
Revises: f1a7c3e9b524
"""

from __future__ import annotations

from alembic import op

revision = "b9d2e6f4a1c8"
down_revision = "f1a7c3e9b524"
branch_labels = None
depends_on = None

_TYPE = "feedback_status"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE {_TYPE} ADD VALUE IF NOT EXISTS 'NEEDS_APPROVAL' BEFORE 'DONE'")
        op.execute(f"ALTER TYPE {_TYPE} ADD VALUE IF NOT EXISTS 'APPROVED' BEFORE 'DONE'")


def downgrade() -> None:
    op.execute(
        "UPDATE feedback_tickets SET status = 'IN_PROGRESS' "
        "WHERE status IN ('NEEDS_APPROVAL', 'APPROVED')"
    )
    op.execute(f"ALTER TYPE {_TYPE} RENAME TO {_TYPE}_old")
    op.execute(
        f"CREATE TYPE {_TYPE} AS ENUM "
        "('BACKLOG', 'TODO', 'IN_PROGRESS', 'NEEDS_FEEDBACK', 'DONE')"
    )
    op.execute(
        "ALTER TABLE feedback_tickets "
        f"ALTER COLUMN status TYPE {_TYPE} USING status::text::{_TYPE}"
    )
    op.execute(f"DROP TYPE {_TYPE}_old")
