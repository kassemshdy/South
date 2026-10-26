"""staff roles for administrator accounts

Administrators were all one kind. A manager now invites staff with a role
-- reviewer, support, content editor or viewer -- and keeps staff, exports,
permanent deletes and site settings to themselves. Every administrator that
exists today becomes a manager, so nobody loses access by this migration.

Revision ID: f1c6a9d3b507
Revises: e3b8f1a6c402
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f1c6a9d3b507"
down_revision = "e3b8f1a6c402"
branch_labels = None
depends_on = None

staff_role = postgresql.ENUM(
    "MANAGER", "REVIEWER", "SUPPORT", "EDITOR", "VIEWER", name="staff_role", create_type=False
)


def upgrade() -> None:
    staff_role.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("staff_role", staff_role, nullable=True))
    op.execute(sa.text("UPDATE users SET staff_role = 'MANAGER' WHERE role = 'ADMIN'"))


def downgrade() -> None:
    op.drop_column("users", "staff_role")
    staff_role.drop(op.get_bind(), checkfirst=True)
