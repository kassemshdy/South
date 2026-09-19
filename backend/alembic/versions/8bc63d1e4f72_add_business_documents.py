"""Add the business_documents table.

A listing's own papers — commercial register, licence, permit — kept apart
from ``owner_verification_documents``, which answers a different question (is
this a real person) and holds one row per owner per kind. These belong to the
business, so one owner may hold papers for two shops without either table's
uniqueness rule having to bend.

Revision ID: 8bc63d1e4f72
Revises: 7ab52c9e3d61
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8bc63d1e4f72"
down_revision = "7ab52c9e3d61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_business_documents_business_id", "business_documents", ["business_id"]
    )
    op.create_index(
        "ix_business_documents_business_created",
        "business_documents",
        ["business_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_business_documents_business_created", table_name="business_documents")
    op.drop_index("ix_business_documents_business_id", table_name="business_documents")
    op.drop_table("business_documents")
