"""users gain must_change_password

Set when an administrator issues a password rather than the account holder
choosing one. While it is true the account may only read itself and replace
that password — a password that travelled through a WhatsApp message is
readable by anyone who has seen that chat, so it is a way in exactly once.

Existing rows default to false: they either chose their own password or have
none at all, and neither is a credential waiting to be replaced.

Revision ID: 4d82a1c9b3e7
Revises: 3c91d4e2f7a8
Create Date: 2026-09-17 09:00:00.000000+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "4d82a1c9b3e7"
down_revision = "3c91d4e2f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
