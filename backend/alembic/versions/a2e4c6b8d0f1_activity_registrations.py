"""Sign-ups for activities on the site itself

An activity takes registrations through a form on its own page by default,
with an external link as the administrator's alternative, or none at all
(the owners' ticket, 4 Nov 2026). Activities that already had a link keep
it; the others take sign-ups on the site from now on.

Revision ID: a2e4c6b8d0f1
Revises: d1f3b5a7c9e2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a2e4c6b8d0f1"
down_revision = "d1f3b5a7c9e2"
branch_labels = None
depends_on = None

MODES = ("ON_SITE", "EXTERNAL", "NONE")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*MODES, name="activity_registration_mode").create(bind, checkfirst=True)
    op.add_column(
        "activities",
        sa.Column(
            "registration_mode",
            postgresql.ENUM(*MODES, name="activity_registration_mode", create_type=False),
            nullable=False,
            server_default="ON_SITE",
        ),
    )
    op.execute(
        "UPDATE activities SET registration_mode = 'EXTERNAL' WHERE register_url IS NOT NULL"
    )

    op.create_table(
        "activity_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(80), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_activity_registrations_activity_id", "activity_registrations", ["activity_id"]
    )


def downgrade() -> None:
    # Drops nothing (the owners' rule, 4 Nov 2026): the sign-ups are people's
    # names and numbers. Undoing this is a new migration through
    # app/database/migration_safety.py.
    pass
