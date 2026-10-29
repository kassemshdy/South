"""Import the owners' full list of Lebanon's towns into the location tree, once.

Runs from the container's start command after migrations and seeding. The
first boot on a database applies ``app.services.location_import`` and
records it; every boot after that does nothing, so a town an administrator
adds or re-activates later is never undone. ``--dry-run`` prints what it
would change and rolls back, for checking against a copy of the database.

It never fails a deploy: an error is logged and the site starts on the tree
it already had.
"""

from __future__ import annotations

import argparse
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import SessionLocal
from app.services.location_import import import_locations, run_once

logger = logging.getLogger("scripts.import_locations")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report, then roll back")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level, json_output=False)
    db = SessionLocal()
    try:
        if args.dry_run:
            report = import_locations(db)
            db.rollback()
            print(report.summary())
            for name in report.towns_kept_unlisted:
                print("kept, in use:", name)
            return 0
        run_once(db)
    except Exception:
        db.rollback()
        logger.exception("Location import failed; the existing tree is unchanged")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
