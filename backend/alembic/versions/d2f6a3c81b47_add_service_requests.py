"""Add service_requests

A visitor asks a talent profile for a piece of work, and the request reaches
that person's dashboard instead of evaporating into a WhatsApp deep link --
the counterpart to what #39 gave products.

Its own table rather than a nullable second parent on ``orders``: an order is
a basket of snapshotted catalogue lines, a talent profile has no catalogue,
and a nullable ``business_id`` would give up the schema-level guarantee that
an order has exactly one owner to fulfil it. The ``order_status`` enum *is*
shared -- new/contacted/done is the same three-step -- so it is referenced
here and never created or dropped.

Revision ID: d2f6a3c81b47
Revises: c4a8e91b2d75
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d2f6a3c81b47"
down_revision = "c4a8e91b2d75"
branch_labels = None
depends_on = None

# `order_status` already exists -- orders created it -- so it is only ever
# referenced here. `create_type=False` is honoured by the postgresql
# dialect's ENUM and ignored by the generic sa.Enum, which would then emit a
# second CREATE TYPE from create_table and die on DuplicateObject.
_status_column = postgresql.ENUM(name="order_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "service_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_name", sa.String(length=80), nullable=False),
        sa.Column("customer_phone", sa.String(length=20), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", _status_column, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["talent_profiles.id"],
            name="fk_service_requests_profile_id_talent_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_requests"),
    )
    op.create_index("ix_service_requests_profile_id", "service_requests", ["profile_id"])
    op.create_index(
        "ix_service_requests_profile_status", "service_requests", ["profile_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_service_requests_profile_status", table_name="service_requests")
    op.drop_index("ix_service_requests_profile_id", table_name="service_requests")
    op.drop_table("service_requests")
