"""Put back a migration stamp that a staging deploy left on a live database.

On 3 Nov 2026 the Shopify staging service ran its branch's migrations against
new.janoubona.net's database (it now sets ``SKIP_MIGRATIONS``). That left the
database stamped ``6be444cc6924``, an empty join of the branch's
``b7e2d4f6a913`` with live's ``f4a8c2d6e1b3``. Live has never had that
revision, so every release since failed with "Can't locate revision".

Putting the stamp back to ``f4a8c2d6e1b3`` is safe because of what the branch
actually did to that database:

- ``a3d9e2c1b7f4`` created the commerce tables. Live's ``c5f1a9e3d7b2``
  creates the very same tables, only where they are absent, so it skips them.
- ``b7e2d4f6a913`` drops two tables this database never had: a no-op here.
- ``6be444cc6924`` itself changes nothing.

Runs from the start command just before ``alembic upgrade head``, after the
boot backup. Each entry applies only while the code has no file for the
foreign revision, so it can never undo a revision this code owns. On any other
database it finds nothing and does nothing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Connection, create_engine, inspect, text

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger("scripts.repair_alembic_stamp")

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"

#: A revision another branch left on a shared database -> the revision of this
#: code's history that the database was really at. Add an entry only after
#: checking what the foreign revisions changed, as above.
FOREIGN_REVISIONS = {"6be444cc6924": "f4a8c2d6e1b3"}


def _known(revision: str, versions_dir: Path) -> bool:
    return any(versions_dir.glob(f"{revision}_*.py"))


def repair(
    connection: Connection,
    foreign_revisions: dict[str, str] = FOREIGN_REVISIONS,
    versions_dir: Path = VERSIONS_DIR,
) -> list[tuple[str, str]]:
    """Restamp every foreign revision found; returns (foreign, own) pairs."""
    if not inspect(connection).has_table("alembic_version"):
        return []
    stamped = {row[0] for row in connection.execute(text("select version_num from alembic_version"))}
    fixed: list[tuple[str, str]] = []
    for foreign, own in foreign_revisions.items():
        if foreign not in stamped or _known(foreign, versions_dir):
            continue
        if own in stamped:
            connection.execute(
                text("delete from alembic_version where version_num = :foreign"),
                {"foreign": foreign},
            )
        else:
            connection.execute(
                text("update alembic_version set version_num = :own where version_num = :foreign"),
                {"own": own, "foreign": foreign},
            )
        fixed.append((foreign, own))
    return fixed


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            fixed = repair(connection)
    finally:
        engine.dispose()
    for foreign, own in fixed:
        logger.warning("Migration stamp %s (not in this code) put back to %s", foreign, own)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
