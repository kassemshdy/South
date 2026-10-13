"""release accounts waiting on a forced password change

The owners dropped the forced change: an issued password is the owner's to
keep, and the WhatsApp message it arrived in is their record of it. Accounts
issued one before this change still carry the flag, and would be shut out of
their dashboard until they replaced it, so it is cleared here.

Data only, and safe to run twice. The downgrade does not restore the flag:
which accounts carried it is not recorded anywhere.

Revision ID: d7a1c4e9b305
Revises: c5f9a3d7e214
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d7a1c4e9b305"
down_revision = "c5f9a3d7e214"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET must_change_password = false WHERE must_change_password")
    )


def downgrade() -> None:
    pass
