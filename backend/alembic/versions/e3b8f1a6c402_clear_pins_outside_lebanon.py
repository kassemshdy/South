"""clear map pins outside Lebanon

A pin is now refused on save unless it is in Lebanon (``app/core/pins.py``).
Pins saved before that check and outside the country are slips on a
zoomed-out map -- one listing's was in the sea off Haifa -- and send visitors
to the wrong place, so they are cleared here. The listing keeps its town;
its owner pins it again from the dashboard.

Data only, and safe to run twice. The downgrade cannot restore the pins,
which were wrong anyway.

Revision ID: e3b8f1a6c402
Revises: d7a1c4e9b305
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e3b8f1a6c402"
down_revision = "d7a1c4e9b305"
branch_labels = None
depends_on = None

# Kept in step with app/core/pins.py by hand: a migration must not import
# application code that may change after it runs.
_OUTSIDE = (
    "latitude IS NOT NULL AND longitude IS NOT NULL AND ("
    "latitude < 33.0 OR latitude > 34.75 OR longitude < 35.05 OR longitude > 36.7)"
)


def upgrade() -> None:
    for table in ("businesses", "talent_profiles"):
        op.execute(
            sa.text(f"UPDATE {table} SET latitude = NULL, longitude = NULL WHERE {_OUTSIDE}")
        )


def downgrade() -> None:
    pass
