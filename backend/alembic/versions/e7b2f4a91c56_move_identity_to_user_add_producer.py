"""move owner identity onto users, add producer detail to businesses

Identity — legal name, birth year, gender, marital status, place of civil
registration, place of residence — described the *person*, but lived on
``talent_profiles``. One account can hold a talent profile and several
businesses, and a legal name cannot differ between them, so the columns move
to ``users`` and every listing reads the one copy.

The same migration adds the goods-producer detail a business publishes:
registered establishment name, founding (or first-production) date, and the
nature of what it produces.

Existing values are copied across before the old columns are dropped, so this
is not lossy even where a profile was already filled in.

Guarded the same way the earlier migrations are: a schema that already ran
ahead of its recorded version must still be able to reconcile to head
instead of crashing on DuplicateColumn.

Revision ID: e7b2f4a91c56
Revises: d1a4c7e08b93
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e7b2f4a91c56"
down_revision = "d1a4c7e08b93"
branch_labels = None
depends_on = None

_IDENTITY_PLAIN: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("full_name", sa.String(length=200)),
    ("birth_year", sa.Integer()),
    ("registration_place", sa.String(length=160)),
    ("residence_place", sa.String(length=200)),
)
_IDENTITY_ENUM = ("gender", "marital_status")
_PRODUCER: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("institution_name", sa.String(length=200)),
    ("founding_date", sa.Date()),
    ("production_nature", sa.Text()),
)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


def _enum_types() -> tuple[postgresql.ENUM, postgresql.ENUM]:
    gender = postgresql.ENUM("MALE", "FEMALE", name="gender", create_type=False)
    marital = postgresql.ENUM(
        "SINGLE", "MARRIED", "DIVORCED", "WIDOWED", name="marital_status", create_type=False
    )
    return gender, marital


def upgrade() -> None:
    bind = op.get_bind()

    # Both enums already exist (the talent detail migration created them), but
    # a database restored from before that point may not have them.
    sa.Enum("MALE", "FEMALE", name="gender").create(bind, checkfirst=True)
    sa.Enum(
        "SINGLE", "MARRIED", "DIVORCED", "WIDOWED", name="marital_status"
    ).create(bind, checkfirst=True)
    gender, marital = _enum_types()

    for name, column_type in _IDENTITY_PLAIN:
        if not _has_column("users", name):
            op.add_column("users", sa.Column(name, column_type, nullable=True))
    if not _has_column("users", "gender"):
        op.add_column("users", sa.Column("gender", gender, nullable=True))
    if not _has_column("users", "marital_status"):
        op.add_column("users", sa.Column("marital_status", marital, nullable=True))

    # Carry across anything a profile already held. A talent profile is
    # one-per-account, so there is never more than one row to copy from.
    moved = [
        name
        for name in (*(c for c, _ in _IDENTITY_PLAIN), *_IDENTITY_ENUM)
        if _has_column("talent_profiles", name)
    ]
    if moved:
        assignments = ", ".join(f"{name} = p.{name}" for name in moved)
        conditions = " OR ".join(f"p.{name} IS NOT NULL" for name in moved)
        op.execute(
            sa.text(
                f"UPDATE users SET {assignments} FROM talent_profiles AS p "
                f"WHERE p.owner_id = users.id AND ({conditions})"
            )
        )
        for name in moved:
            op.drop_column("talent_profiles", name)

    for name, column_type in _PRODUCER:
        if not _has_column("businesses", name):
            op.add_column("businesses", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    gender, marital = _enum_types()

    for name, column_type in _IDENTITY_PLAIN:
        op.add_column("talent_profiles", sa.Column(name, column_type, nullable=True))
    op.add_column("talent_profiles", sa.Column("gender", gender, nullable=True))
    op.add_column("talent_profiles", sa.Column("marital_status", marital, nullable=True))

    names = (*(c for c, _ in _IDENTITY_PLAIN), *_IDENTITY_ENUM)
    assignments = ", ".join(f"{name} = u.{name}" for name in names)
    op.execute(
        sa.text(
            f"UPDATE talent_profiles SET {assignments} FROM users AS u "
            "WHERE talent_profiles.owner_id = u.id"
        )
    )

    for name in names:
        op.drop_column("users", name)
    for name, _ in _PRODUCER:
        op.drop_column("businesses", name)
