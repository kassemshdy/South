"""Drop the one-time password challenges table.

OTP sign-in is gone — no SMS or WhatsApp gateway was ever obtainable, so the
only provider that ever ran was the development one, which issues a fixed
code. The table held nothing worth keeping: a challenge is a hash and an
expiry, every row is spent or stale within five minutes, and no other table
refers to one. Recreating it is what ``downgrade`` is for.

Revision ID: 6fa41b8d2c05
Revises: 5e93f7a2c1d4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "6fa41b8d2c05"
down_revision = "5e93f7a2c1d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_otp_requests_phone_created", table_name="otp_requests")
    op.drop_index("ix_otp_requests_phone_number", table_name="otp_requests")
    op.drop_table("otp_requests")


def downgrade() -> None:
    op.create_table(
        "otp_requests",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("request_ip", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_otp_requests_phone_number", "otp_requests", ["phone_number"], unique=False
    )
    op.create_index(
        "ix_otp_requests_phone_created",
        "otp_requests",
        ["phone_number", "created_at"],
        unique=False,
    )
