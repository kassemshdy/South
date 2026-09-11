"""add business working hours

Revision ID: c1a7e2f43b98
Revises: d2f6a3c81b47
Create Date: 2026-09-11 00:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'c1a7e2f43b98'
down_revision = 'd2f6a3c81b47'
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


def upgrade() -> None:
    if not _has_column('businesses', 'working_hours'):
        op.add_column('businesses', sa.Column('working_hours', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('businesses', 'working_hours')
