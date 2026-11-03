"""Activities redesign and the carousel table

An announcement gets a kind, a registration link with its button label and
a calendar switch. The carousel's slides move to a table of their own, which
also holds custom slides, so the home page and /activities share one order
(the owners' ticket, 31 Oct 2026).

The carousel starts as it is today: every activity that was public (kept,
with its photograph), in the order it was shown.

Revision ID: f4a8c2e1d9b7
Revises: e3b9f1c6a2d8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4a8c2e1d9b7"
down_revision = "e3b9f1c6a2d8"
branch_labels = None
depends_on = None

KINDS = ("ACTIVITY", "CONSULTATION", "WORKSHOP", "TRAINING")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*KINDS, name="activity_kind").create(bind, checkfirst=True)
    op.add_column(
        "activities",
        sa.Column(
            "kind",
            postgresql.ENUM(*KINDS, name="activity_kind", create_type=False),
            nullable=False,
            server_default="ACTIVITY",
        ),
    )
    op.add_column("activities", sa.Column("register_url", sa.String(500), nullable=True))
    op.add_column("activities", sa.Column("register_label", sa.String(60), nullable=True))
    op.add_column(
        "activities",
        sa.Column("show_calendar", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "carousel_slides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"),
            nullable=True,
            unique=True,
        ),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("image_storage_key", sa.String(500), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_carousel_slides_position", "carousel_slides", ["position"])

    op.execute(
        """
        INSERT INTO carousel_slides (id, position, activity_id)
        SELECT gen_random_uuid(),
               ROW_NUMBER() OVER (ORDER BY sort_order ASC, created_at DESC),
               id
        FROM activities
        WHERE is_archived = false AND image_url IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_carousel_slides_position", table_name="carousel_slides")
    op.drop_table("carousel_slides")
    for column in ("show_calendar", "register_label", "register_url", "kind"):
        op.drop_column("activities", column)
    postgresql.ENUM(*KINDS, name="activity_kind").drop(op.get_bind(), checkfirst=True)
