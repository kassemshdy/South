"""keep applications for a number that already has an account, for review

They used to be thrown away. The applicant's answer does not change and
nothing is attached to the existing account; the application is kept where
only an administrator can read it, at the CEO's request, so a real owner
applying a second time is not silently lost. The ID scan is still never
stored.

Revision ID: e5b9c3d72a14
Revises: d4a8f2c61e57
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "e5b9c3d72a14"
down_revision = "d4a8f2c61e57"
branch_labels = None
depends_on = None

_KINDS = ("BUSINESS", "TALENT")


def upgrade() -> None:
    bind = op.get_bind()
    sa.Enum(*_KINDS, name="application_kind").create(bind, checkfirst=True)
    if sa.inspect(bind).has_table("discarded_applications"):
        return
    op.create_table(
        "discarded_applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "kind",
            postgresql.ENUM(*_KINDS, name="application_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("login_phone", sa.String(20), nullable=False),
        sa.Column(
            "existing_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_discarded_applications_login_phone",
        "discarded_applications",
        ["login_phone"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("discarded_applications"):
        op.drop_index("ix_discarded_applications_login_phone", "discarded_applications")
        op.drop_table("discarded_applications")
    sa.Enum(*_KINDS, name="application_kind").drop(bind, checkfirst=True)
