"""the partner form's submissions

Round 3: a card on the site for someone who wants to support the project,
leading to a short form whose answers reach an admin page of their own. A
table of its own rather than a ticket: it carries a stranger's name and phone
number and is read by administrators only.

Guarded like the migrations before it.

Revision ID: c5f9a3d7e214
Revises: b4e8f2a9c613
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c5f9a3d7e214"
down_revision = "b4e8f2a9c613"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("partner_requests"):
        return
    op.create_table(
        "partner_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("occupation", sa.String(160), nullable=False),
        sa.Column("residence", sa.String(200), nullable=False),
        sa.Column("offer", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_partner_requests_created_at", "partner_requests", ["created_at"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("partner_requests"):
        op.drop_index("ix_partner_requests_created_at", table_name="partner_requests")
        op.drop_table("partner_requests")
