"""the floating contact form's messages

Feedback or any question from a visitor, read by administrators only. A
table of its own, like the partner form's: it carries a stranger's name and
a way to reach them.

Guarded like the migrations before it.

Revision ID: d6a2f4c8e913
Revises: c5e1f8a2d3b7
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d6a2f4c8e913"
down_revision = "c5e1f8a2d3b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("contact_messages"):
        return
    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("topic", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page_path", sa.String(300), nullable=True),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_contact_messages_created_at", "contact_messages", ["created_at"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("contact_messages"):
        op.drop_index("ix_contact_messages_created_at", table_name="contact_messages")
        op.drop_table("contact_messages")
