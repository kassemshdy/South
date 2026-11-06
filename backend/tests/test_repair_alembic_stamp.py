"""The stamp a staging deploy left on new.janoubona.net's database is put back.

See ``scripts/repair_alembic_stamp.py`` for why the restamp is safe there.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text

from app.database.session import engine
from scripts import repair_alembic_stamp


@pytest.fixture
def stamps() -> Iterator[None]:
    with engine.begin() as connection:
        connection.execute(text("drop table if exists alembic_version"))
        connection.execute(
            text("create table alembic_version (version_num varchar(32) primary key)")
        )
    yield
    with engine.begin() as connection:
        connection.execute(text("drop table if exists alembic_version"))


def _stamp(*revisions: str) -> None:
    with engine.begin() as connection:
        for revision in revisions:
            connection.execute(
                text("insert into alembic_version values (:r)"), {"r": revision}
            )


def _stamped() -> set[str]:
    with engine.connect() as connection:
        return {row[0] for row in connection.execute(text("select version_num from alembic_version"))}


def test_the_staging_stamp_is_put_back_to_the_live_revision(stamps: None) -> None:
    _stamp("6be444cc6924")
    with engine.begin() as connection:
        fixed = repair_alembic_stamp.repair(connection)
    assert fixed == [("6be444cc6924", "f4a8c2d6e1b3")]
    assert _stamped() == {"f4a8c2d6e1b3"}


def test_a_database_at_a_known_revision_is_left_alone(stamps: None) -> None:
    _stamp("d1f3b5a7c9e2")
    with engine.begin() as connection:
        assert repair_alembic_stamp.repair(connection) == []
    assert _stamped() == {"d1f3b5a7c9e2"}


def test_the_foreign_row_goes_when_the_live_revision_is_already_stamped(stamps: None) -> None:
    _stamp("6be444cc6924", "f4a8c2d6e1b3")
    with engine.begin() as connection:
        repair_alembic_stamp.repair(connection)
    assert _stamped() == {"f4a8c2d6e1b3"}


def test_a_revision_this_code_owns_is_never_undone(stamps: None, tmp_path: Path) -> None:
    (tmp_path / "6be444cc6924_join.py").write_text("")
    _stamp("6be444cc6924")
    with engine.begin() as connection:
        assert repair_alembic_stamp.repair(connection, versions_dir=tmp_path) == []
    assert _stamped() == {"6be444cc6924"}


def test_a_database_without_migrations_is_left_alone() -> None:
    with engine.begin() as connection:
        connection.execute(text("drop table if exists alembic_version"))
        assert repair_alembic_stamp.repair(connection) == []


def test_the_live_revision_it_restores_exists_in_this_code() -> None:
    for own in repair_alembic_stamp.FOREIGN_REVISIONS.values():
        assert any(repair_alembic_stamp.VERSIONS_DIR.glob(f"{own}_*.py")), own
