"""job openings, offered by staff or by employers, and the applications sent to them

Revision ID: f4c9d2e6b8a1
Revises: e3b8c5d1a7f2
Create Date: 2026-10-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4c9d2e6b8a1"
down_revision = "e3b8c5d1a7f2"
branch_labels = None
depends_on = None

_job_type = postgresql.ENUM(
    "FULL_TIME", "PART_TIME", "REMOTE", "FREELANCE", "INTERNSHIP", name="job_type"
)
# Already created for talent profiles (remote, on site, both); reused.


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    _job_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "job_openings",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("employer_name", sa.String(160), nullable=True),
        sa.Column(
            "job_type",
            postgresql.ENUM(name="job_type", create_type=False),
            nullable=False,
            server_default="FULL_TIME",
        ),
        sa.Column("salary", sa.String(120), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "location_id",
            sa.UUID(),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("work_place", sa.String(200), nullable=True),
        sa.Column(
            "work_mode", postgresql.ENUM(name="work_mode", create_type=False), nullable=True
        ),
        sa.Column("submitter_name", sa.String(80), nullable=True),
        sa.Column("submitter_phone", sa.String(20), nullable=True),
        sa.Column("id_document_storage_key", sa.String(300), nullable=True),
        sa.Column("id_document_content_type", sa.String(100), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_job_openings_slug", "job_openings", ["slug"], unique=True)
    op.create_index("ix_job_openings_published", "job_openings", ["is_published", "created_at"])
    op.create_table(
        "job_applications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("job_openings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(80), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_job_applications_job_id", "job_applications", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_applications_job_id", table_name="job_applications")
    op.drop_table("job_applications")
    op.drop_index("ix_job_openings_published", table_name="job_openings")
    op.drop_index("ix_job_openings_slug", table_name="job_openings")
    op.drop_table("job_openings")
    _job_type.drop(op.get_bind(), checkfirst=True)
