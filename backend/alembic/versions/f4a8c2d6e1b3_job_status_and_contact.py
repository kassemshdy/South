"""Job openings: status, a contact number, and contact-button counts

The jobs redesign (31 Oct 2026): an opening is applied to by WhatsApp or a
call instead of a form, so it carries the number to contact, and a status
(open, filled, no longer available) that is separate from publishing. Every
existing opening starts open. Presses of the two buttons are counted per
opening, channel and day, with nothing about who pressed.

Revision ID: f4a8c2d6e1b3
Revises: e3b9f1c6a2d8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4a8c2d6e1b3"
down_revision = "e3b9f1c6a2d8"
branch_labels = None
depends_on = None

STATUSES = ("ACTIVE", "FILLED", "UNAVAILABLE")
CHANNELS = ("WHATSAPP", "CALL")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*STATUSES, name="job_status").create(bind, checkfirst=True)
    postgresql.ENUM(*CHANNELS, name="job_contact_channel").create(bind, checkfirst=True)
    op.add_column(
        "job_openings",
        sa.Column(
            "status",
            postgresql.ENUM(*STATUSES, name="job_status", create_type=False),
            nullable=False,
            server_default="ACTIVE",
        ),
    )
    op.add_column(
        "job_openings", sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("job_openings", sa.Column("contact_phone", sa.String(20), nullable=True))
    op.add_column("job_openings", sa.Column("contact_name", sa.String(120), nullable=True))
    op.add_column(
        "job_openings",
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "job_contact_click_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_openings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel",
            postgresql.ENUM(*CHANNELS, name="job_contact_channel", create_type=False),
            nullable=False,
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("job_id", "channel", "day", name="uq_job_contact_click_daily"),
    )
    op.create_index("ix_job_contact_click_daily_job_id", "job_contact_click_daily", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_contact_click_daily_job_id", table_name="job_contact_click_daily")
    op.drop_table("job_contact_click_daily")
    for column in (
        "whatsapp_enabled",
        "contact_name",
        "contact_phone",
        "status_changed_at",
        "status",
    ):
        op.drop_column("job_openings", column)
    bind = op.get_bind()
    postgresql.ENUM(*CHANNELS, name="job_contact_channel").drop(bind, checkfirst=True)
    postgresql.ENUM(*STATUSES, name="job_status").drop(bind, checkfirst=True)
