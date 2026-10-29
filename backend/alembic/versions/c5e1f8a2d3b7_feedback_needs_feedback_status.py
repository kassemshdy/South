"""Ticket board: a «needs feedback from the admin» column.

A ticket waiting on an answer from the owners' side (wording, a file, a
decision) had nowhere to go but «in progress», where it looked like work
under way (the owners' request, 29 Oct 2026).

``ALTER TYPE ... ADD VALUE`` must run outside the migration's transaction,
as in 7ab52c9e3d61; ``BEFORE 'DONE'`` keeps the type's order the board's
order. Adding a value is not reversible, so ``downgrade`` moves those
tickets back to IN_PROGRESS and rebuilds the type without it.

Revision ID: c5e1f8a2d3b7
Revises: a7d3e9f1c2b4
"""

from __future__ import annotations

from alembic import op

revision = "c5e1f8a2d3b7"
down_revision = "a7d3e9f1c2b4"
branch_labels = None
depends_on = None

_TYPE = "feedback_status"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE {_TYPE} ADD VALUE IF NOT EXISTS 'NEEDS_FEEDBACK' BEFORE 'DONE'")


def downgrade() -> None:
    op.execute("UPDATE feedback_tickets SET status = 'IN_PROGRESS' WHERE status = 'NEEDS_FEEDBACK'")
    op.execute(f"ALTER TYPE {_TYPE} RENAME TO {_TYPE}_old")
    op.execute(f"CREATE TYPE {_TYPE} AS ENUM ('BACKLOG', 'TODO', 'IN_PROGRESS', 'DONE')")
    op.execute(
        "ALTER TABLE feedback_tickets "
        f"ALTER COLUMN status TYPE {_TYPE} USING status::text::{_TYPE}"
    )
    op.execute(f"DROP TYPE {_TYPE}_old")
