"""Open service requests: a visitor asks the team for a service.

Revision ID: c9e5a7b3d2f4
Revises: c5f1a9e3d7b2
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c9e5a7b3d2f4"
down_revision = "c5f1a9e3d7b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "open_service_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_name", sa.String(80), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("talent_skills.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    # Drops nothing (the owners' rule, 4 Nov 2026): a table that may hold
    # visitors' requests is removed, if ever, by a new migration through
    # app.database.migration_safety.drop_table_if_empty.
    pass
