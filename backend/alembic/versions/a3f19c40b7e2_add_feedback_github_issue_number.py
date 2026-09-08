"""Add feedback_tickets.github_issue_number

Records which roadmap issue serves a ticket, so the board and the tracker can
be joined without matching on title text.

Revision ID: a3f19c40b7e2
Revises: e7b2f4a91c56
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a3f19c40b7e2"
down_revision = "e7b2f4a91c56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feedback_tickets",
        sa.Column("github_issue_number", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_feedback_tickets_github_issue_number",
        "feedback_tickets",
        ["github_issue_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_tickets_github_issue_number", table_name="feedback_tickets")
    op.drop_column("feedback_tickets", "github_issue_number")
