"""Never drop a table that has data (the owners' rule, 4 Nov 2026).

Two layers. Every migration's ``upgrade()`` is read, and a direct
``op.drop_table`` / ``op.drop_column`` or a raw ``DROP TABLE`` / ``DROP
COLUMN`` fails here: a migration removes things only through
``app.database.migration_safety``, which looks first and refuses when there is
anything to lose. And that helper is run against the real database, so its
refusal is checked, not assumed.

The three revisions in ``HISTORIC`` dropped things before the rule existed and
ran on every database long ago; they are not a precedent.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import sqlalchemy as sa

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.database.migration_safety import drop_column_if_empty, drop_table_if_empty
from app.database.session import engine

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"

HISTORIC = {
    "6fa41b8d2c05",  # drop otp_requests, when OTP sign-in was removed
    "853f1d6867f8",  # talent_profiles.headline
    "e7b2f4a91c56",  # identity moved from talent_profiles to users
}

DIRECT_DROP = re.compile(
    r"op\.drop_table\(|op\.drop_column\(|DROP\s+TABLE|DROP\s+COLUMN", re.IGNORECASE
)


def _upgrade_source(path: Path) -> tuple[str, str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    revision = ""
    body = ""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "revision" for t in node.targets
        ):
            revision = ast.literal_eval(node.value)
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            body = ast.get_source_segment(source, node) or ""
    return revision, body


def test_no_migration_drops_a_table_or_column_directly() -> None:
    offenders = []
    for path in sorted(VERSIONS.glob("*.py")):
        revision, upgrade = _upgrade_source(path)
        if revision in HISTORIC:
            continue
        if DIRECT_DROP.search(upgrade):
            offenders.append(path.name)
    assert not offenders, (
        "These migrations drop a table or column directly. Use "
        "drop_table_if_empty / drop_column_if_empty from "
        f"app.database.migration_safety instead: {offenders}"
    )


def test_the_historic_list_names_real_revisions() -> None:
    revisions = {_upgrade_source(p)[0] for p in VERSIONS.glob("*.py")}
    assert revisions >= HISTORIC


@pytest.fixture
def scratch() -> object:
    names = ("safety_with_rows", "safety_empty")
    with engine.begin() as conn:
        for name in names:
            conn.execute(sa.text(f'DROP TABLE IF EXISTS "{name}"'))
            conn.execute(sa.text(f'CREATE TABLE "{name}" (id int, note text)'))
        conn.execute(sa.text("INSERT INTO safety_with_rows VALUES (1, 'kept')"))
        conn.execute(sa.text("INSERT INTO safety_empty VALUES (1, NULL)"))
    yield
    with engine.begin() as conn:
        for name in names:
            conn.execute(sa.text(f'DROP TABLE IF EXISTS "{name}"'))


def _tables() -> set[str]:
    return set(sa.inspect(engine).get_table_names())


@pytest.mark.usefixtures("scratch")
def test_a_table_with_data_is_never_dropped() -> None:
    with (
        engine.connect() as conn,
        Operations.context(MigrationContext.configure(conn)),
        pytest.raises(RuntimeError, match="has data"),
    ):
        drop_table_if_empty("safety_with_rows")
    assert "safety_with_rows" in _tables()
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT note FROM safety_with_rows")).scalar() == "kept"


@pytest.mark.usefixtures("scratch")
def test_a_column_with_data_is_never_dropped_and_an_empty_one_is() -> None:
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        with pytest.raises(RuntimeError, match="has data"):
            drop_column_if_empty("safety_with_rows", "note")
        drop_column_if_empty("safety_empty", "note")
    columns = {c["name"] for c in sa.inspect(engine).get_columns("safety_empty")}
    assert "note" not in columns
    assert "note" in {c["name"] for c in sa.inspect(engine).get_columns("safety_with_rows")}


@pytest.mark.usefixtures("scratch")
def test_an_empty_table_may_go() -> None:
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM safety_empty"))
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        drop_table_if_empty("safety_empty")
    assert "safety_empty" not in _tables()
