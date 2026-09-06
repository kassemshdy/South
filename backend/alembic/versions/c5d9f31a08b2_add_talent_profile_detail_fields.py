"""add talent profile detail fields

Adds the professional detail a talent profile publishes (degree,
specialisation, university, experience, skills, services offered, languages)
and the identity fields it deliberately does not (legal name, birth year,
gender, marital status, civil registration and residence places).

Guarded the same way the earlier migrations are: a schema that already ran
ahead of its recorded version must still be able to reconcile to head
instead of crashing on DuplicateColumn.

Revision ID: c5d9f31a08b2
Revises: b3e7a1c9d2f4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c5d9f31a08b2"
down_revision = "b3e7a1c9d2f4"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


_NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("highest_degree", sa.String(length=160)),
    ("specialization", sa.String(length=160)),
    ("university", sa.String(length=200)),
    ("experience", sa.Text()),
    ("skills_text", sa.Text()),
    ("services_offered", sa.Text()),
    ("full_name", sa.String(length=200)),
    ("birth_year", sa.Integer()),
    ("registration_place", sa.String(length=160)),
    ("residence_place", sa.String(length=200)),
)


def upgrade() -> None:
    bind = op.get_bind()

    # Created explicitly first, then referenced with create_type=False below,
    # so neither add_column nor create_table re-issues CREATE TYPE — the same
    # split the talent-directory migration already uses.
    sa.Enum("MALE", "FEMALE", name="gender").create(bind, checkfirst=True)
    sa.Enum(
        "SINGLE", "MARRIED", "DIVORCED", "WIDOWED", name="marital_status"
    ).create(bind, checkfirst=True)
    sa.Enum(
        "BASIC", "GOOD", "FLUENT", "NATIVE", name="language_proficiency"
    ).create(bind, checkfirst=True)

    gender = postgresql.ENUM("MALE", "FEMALE", name="gender", create_type=False)
    marital_status = postgresql.ENUM(
        "SINGLE", "MARRIED", "DIVORCED", "WIDOWED", name="marital_status", create_type=False
    )
    proficiency = postgresql.ENUM(
        "BASIC", "GOOD", "FLUENT", "NATIVE", name="language_proficiency", create_type=False
    )

    for name, column_type in _NEW_COLUMNS:
        if not _has_column("talent_profiles", name):
            op.add_column("talent_profiles", sa.Column(name, column_type, nullable=True))

    if not _has_column("talent_profiles", "gender"):
        op.add_column("talent_profiles", sa.Column("gender", gender, nullable=True))
    if not _has_column("talent_profiles", "marital_status"):
        op.add_column(
            "talent_profiles", sa.Column("marital_status", marital_status, nullable=True)
        )

    if not _has_table("talent_languages"):
        op.create_table(
            "talent_languages",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column(
                "profile_id",
                sa.UUID(),
                sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column(
                "proficiency", proficiency, nullable=False, server_default="GOOD"
            ),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index(
            "ix_talent_languages_profile_id", "talent_languages", ["profile_id"]
        )
        op.create_index(
            "ix_talent_languages_profile_sort",
            "talent_languages",
            ["profile_id", "sort_order"],
        )


def downgrade() -> None:
    op.drop_table("talent_languages")
    for name in ("gender", "marital_status", *(column for column, _ in _NEW_COLUMNS)):
        op.drop_column("talent_profiles", name)
    sa.Enum(name="language_proficiency").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="marital_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="gender").drop(op.get_bind(), checkfirst=True)
