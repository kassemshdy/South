"""The only way a migration may remove a table or a column.

The owners' rule (4 Nov 2026): **never drop a table that has data.** A
migration that wants a table or column gone calls one of these instead of
``op.drop_table`` / ``op.drop_column``. Each looks first, and refuses with an
error when there is anything to lose -- a row in the table, a non-null value
in the column. The migration then fails inside its transaction, nothing is
dropped, and the deploy stops with the reason in its log, which is the right
outcome: someone decides what happens to that data before it goes.

``tests/test_migration_safety.py`` fails any migration that drops without
going through here.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def drop_table_if_empty(name: str) -> None:
    bind = op.get_bind()
    if name not in sa.inspect(bind).get_table_names():
        return
    has_rows = bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {_quoted(name)})")).scalar()
    if has_rows:
        raise RuntimeError(
            f"Refusing to drop table {name}: it has data. Move or archive the rows "
            "first, in their own reviewed migration."
        )
    op.drop_table(name)


def drop_column_if_empty(table: str, column: str) -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns(table)}
    if column not in columns:
        return
    has_values = bind.execute(
        sa.text(
            f"SELECT EXISTS (SELECT 1 FROM {_quoted(table)} "
            f"WHERE {_quoted(column)} IS NOT NULL)"
        )
    ).scalar()
    if has_values:
        raise RuntimeError(
            f"Refusing to drop column {table}.{column}: it has data. Move or archive "
            "the values first, in their own reviewed migration."
        )
    op.drop_column(table, column)
