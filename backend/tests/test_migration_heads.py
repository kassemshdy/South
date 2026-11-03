"""The migration history has exactly one head.

Two pull requests each added a migration on the same parent (3 Nov 2026).
Each was green on its own, because each branch had only its own; merged
together they left two heads, and ``alembic upgrade head`` -- which the API
runs on every boot -- refuses to choose between them. This catches that on
the pull request that would create the second head, not on the deploy.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[1]


def test_there_is_a_single_migration_head() -> None:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1, f"Several migration heads, chain them: {heads}"
