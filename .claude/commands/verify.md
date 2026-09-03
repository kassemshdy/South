---
description: Run the full local verification gate (backend, frontend, e2e, no-Arabic guard)
---

Run the complete local check sequence for this repo, in order, stopping to report and fix
anything that fails rather than plowing ahead:

1. Ensure Postgres is running (`pg_ctlcluster 16 main start` in this sandbox if it's down).
2. Backend, from `backend/`:
   - `./.venv/bin/pytest tests/ -q` — this includes the no-Arabic-in-code guard
     (`tests/test_i18n.py`), which must pass over `app`, `scripts`, `tests`, and
     `frontend/src`/`frontend/e2e`.
   - `./.venv/bin/ruff check .`
   - `./.venv/bin/mypy app scripts`
3. Frontend, from `frontend/`:
   - `npx tsc -b`
   - `npm run build`
4. End-to-end, from `frontend/`, only if the database is in a clean/known state (a stale
   business from a previous run can fail the acceptance spec's negative assertions on a
   name collision — reset with `dropdb`/`createdb`/`alembic upgrade head`/
   `python -m scripts.seed --ensure` first if unsure):
   - `CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npx playwright test`

Report which steps passed and which didn't — do not claim success on a step you didn't
actually run or couldn't verify the output of.
