"""Add the back of the ID card as its own document kind.

An owner uploads two sides now, and the documents table stores one row per
owner per kind — so the second side is a new kind rather than a second row of
the existing one.

``ALTER TYPE ... ADD VALUE`` cannot run inside a transaction that later uses
the value, which is why the testimonials migration swapped the whole type
instead. Nothing here uses it, so the simpler form is available — but it
still has to be outside the migration's transaction, hence the autocommit
block. Adding a value is not reversible in PostgreSQL, so ``downgrade``
rebuilds the type without it, which is safe only because no row can hold the
new value once the rows using it are gone.

Revision ID: 7ab52c9e3d61
Revises: 6fa41b8d2c05
"""

from __future__ import annotations

from alembic import op

revision = "7ab52c9e3d61"
down_revision = "6fa41b8d2c05"
branch_labels = None
depends_on = None

_TYPE = "verification_document_kind"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE {_TYPE} ADD VALUE IF NOT EXISTS 'IDENTITY_BACK'")


def downgrade() -> None:
    # The rows first: a value cannot be dropped from a type while anything
    # still holds it, and a back-of-card scan has no meaning without the kind.
    op.execute(
        "DELETE FROM owner_verification_documents WHERE kind = 'IDENTITY_BACK'"
    )
    op.execute(f"ALTER TYPE {_TYPE} RENAME TO {_TYPE}_old")
    op.execute(f"CREATE TYPE {_TYPE} AS ENUM ('IDENTITY', 'CV')")
    op.execute(
        "ALTER TABLE owner_verification_documents "
        f"ALTER COLUMN kind TYPE {_TYPE} USING kind::text::{_TYPE}"
    )
    op.execute(f"DROP TYPE {_TYPE}_old")
