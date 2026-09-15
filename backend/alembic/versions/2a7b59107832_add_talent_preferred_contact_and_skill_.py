"""add talent preferred contact and skill specialty

Two nullable columns on ``talent_profiles``: which contact channel the public
page should lead with, and the trade in the person's own words one level below
the skill they picked from the taxonomy.

The ``contact_channel`` enum type is created explicitly. Autogenerate also
proposed dropping four pre-existing trigram (GIN) indexes it cannot see,
because they are created with raw DDL rather than through the model metadata;
those drops are removed. This revision adds one type and two columns.

Revision ID: 2a7b59107832
Revises: 18c64fbbe097
Create Date: 2026-09-15 19:12:00.000000+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "2a7b59107832"
down_revision = "18c64fbbe097"
branch_labels = None
depends_on = None

_CONTACT_CHANNEL = sa.Enum(
    "PHONE", "WHATSAPP", "EMAIL", "WEBSITE", name="contact_channel"
)


def upgrade() -> None:
    _CONTACT_CHANNEL.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "talent_profiles",
        sa.Column("preferred_contact", _CONTACT_CHANNEL, nullable=True),
    )
    op.add_column(
        "talent_profiles", sa.Column("skill_specialty", sa.String(length=160), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("talent_profiles", "skill_specialty")
    op.drop_column("talent_profiles", "preferred_contact")
    _CONTACT_CHANNEL.drop(op.get_bind(), checkfirst=True)
