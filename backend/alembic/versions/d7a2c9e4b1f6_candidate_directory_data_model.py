"""Candidate directory data model

Structured candidate data beside the free-text fields: a desired job title,
availability, work types and areas, a hidden-photo flag, a private CV and
team message, experience / education / course rows and the employer-request
log. Existing job seekers keep everything: their degree, field and
university become one education row, their field becomes the desired title.

Revision ID: d7a2c9e4b1f6
Revises: c4e8a1d7b3f9
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d7a2c9e4b1f6"
down_revision = "c4e8a1d7b3f9"
branch_labels = None
depends_on = None

AVAILABILITY = ("NOW", "WITHIN_MONTH", "EMPLOYED_OPEN")
WORK_TYPES = ("FULL_TIME", "PART_TIME", "REMOTE", "TRAINING")
REQUEST_STATUS = ("NEW", "CONTACTED", "HIRED")

_availability = postgresql.ENUM(*AVAILABILITY, name="talent_availability", create_type=False)
_work_type = postgresql.ENUM(*WORK_TYPES, name="talent_work_type", create_type=False)
_request_status = postgresql.ENUM(*REQUEST_STATUS, name="employer_request_status", create_type=False)


def _uuid() -> postgresql.UUID:
    return postgresql.UUID(as_uuid=True)


def _profile_fk() -> sa.Column:
    return sa.Column(
        "profile_id",
        _uuid(),
        sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in (
        ("talent_availability", AVAILABILITY),
        ("talent_work_type", WORK_TYPES),
        ("employer_request_status", REQUEST_STATUS),
    ):
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    op.add_column("talent_profiles", sa.Column("desired_title", sa.String(60), nullable=True))
    op.add_column(
        "talent_profiles",
        sa.Column("availability", _availability, nullable=False, server_default="NOW"),
    )
    op.add_column(
        "talent_profiles",
        sa.Column("photo_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("talent_profiles", sa.Column("cv_storage_key", sa.String(500), nullable=True))
    op.add_column(
        "talent_profiles",
        sa.Column("cv_public", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("talent_profiles", sa.Column("team_message", sa.Text(), nullable=True))
    op.add_column(
        "talent_profiles",
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "talent_work_types",
        sa.Column("id", _uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("work_type", _work_type, nullable=False),
        sa.UniqueConstraint("profile_id", "work_type", name="uq_talent_work_type"),
    )
    op.create_index("ix_talent_work_types_profile_id", "talent_work_types", ["profile_id"])

    op.create_table(
        "talent_work_areas",
        sa.Column("id", _uuid(), primary_key=True),
        _profile_fk(),
        sa.Column(
            "location_id",
            _uuid(),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("profile_id", "location_id", name="uq_talent_work_area"),
    )
    op.create_index("ix_talent_work_areas_profile_id", "talent_work_areas", ["profile_id"])
    op.create_index("ix_talent_work_areas_location_id", "talent_work_areas", ["location_id"])

    op.create_table(
        "talent_experiences",
        sa.Column("id", _uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("employer", sa.String(160), nullable=True),
        sa.Column("town", sa.String(120), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_talent_experiences_profile_id", "talent_experiences", ["profile_id"])

    op.create_table(
        "talent_education",
        sa.Column("id", _uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("degree", sa.String(160), nullable=True),
        sa.Column("field", sa.String(160), nullable=True),
        sa.Column("institution", sa.String(200), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_talent_education_profile_id", "talent_education", ["profile_id"])

    op.create_table(
        "talent_courses",
        sa.Column("id", _uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("issuer", sa.String(160), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_talent_courses_profile_id", "talent_courses", ["profile_id"])

    op.create_table(
        "employer_requests",
        sa.Column("id", _uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("employer_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("company", sa.String(160), nullable=True),
        sa.Column("job_title", sa.String(160), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", _request_status, nullable=False, server_default="NEW"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_employer_requests_profile_id", "employer_requests", ["profile_id"])
    op.create_index("ix_employer_requests_status", "employer_requests", ["status"])

    # Nothing is lost: the free-text education becomes one row, and the
    # specialization stands in as the desired title (60 characters at most)
    # until its owner words it themselves.
    op.execute(
        """
        INSERT INTO talent_education (id, profile_id, degree, field, institution, graduation_year)
        SELECT gen_random_uuid(), id, highest_degree, specialization, university,
               EXTRACT(YEAR FROM graduation_date)::int
        FROM talent_profiles
        WHERE highest_degree IS NOT NULL OR specialization IS NOT NULL OR university IS NOT NULL
        """
    )
    op.execute(
        "UPDATE talent_profiles SET desired_title = LEFT(specialization, 60) "
        "WHERE specialization IS NOT NULL AND kind = 'JOB_SEEKER'"
    )


def downgrade() -> None:
    for table in (
        "employer_requests",
        "talent_courses",
        "talent_education",
        "talent_experiences",
        "talent_work_areas",
        "talent_work_types",
    ):
        op.drop_table(table)
    for column in (
        "last_confirmed_at",
        "team_message",
        "cv_public",
        "cv_storage_key",
        "photo_hidden",
        "availability",
        "desired_title",
    ):
        op.drop_column("talent_profiles", column)
    bind = op.get_bind()
    for name in ("employer_request_status", "talent_work_type", "talent_availability"):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
