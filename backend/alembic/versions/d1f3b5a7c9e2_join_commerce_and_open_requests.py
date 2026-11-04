"""join the commerce tables and open service requests

``c5f1a9e3d7b2`` (kassemshdy/South#393) and ``c9e5a7b3d2f4``
(kassemshdy/South#394) were merged into develop-claude minutes apart, each
on ``b8d4f6a2c1e3``, which left two heads and an ``alembic upgrade head``
that refuses to choose. This revision only joins them: it changes nothing,
so it is right for a database that ran either, both or neither.

Revision ID: d1f3b5a7c9e2
Revises: c5f1a9e3d7b2, c9e5a7b3d2f4
"""

from __future__ import annotations

revision = "d1f3b5a7c9e2"
down_revision = ("c5f1a9e3d7b2", "c9e5a7b3d2f4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
