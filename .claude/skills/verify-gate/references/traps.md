# Traps that have actually cost time in this repo

Each of these cost an agent real time here. They are failures of the
*harness*, not of the code under test, so a step that fails in one of
these ways is not telling you what it appears to.

- **`pytest --timeout=N` is not available.** `pytest-timeout` is not installed;
  the flag makes pytest exit with "unrecognized arguments" while the
  surrounding shell can still report success, so the gate looks green without
  having run. Do not pass it.
- **The no-Arabic guard scans comments.** `backend/tests/test_i18n.py` looks
  for Arabic codepoints anywhere in `backend/app`, `backend/scripts`,
  `backend/tests`, `frontend/src` and `frontend/e2e` — including doc comments
  and strings in comments. Name the catalog key instead of quoting the text.
  `frontend/public/`, `.claude/`, `docs/` and `mcp-server/` are not scanned.
- **A failing acceptance spec is usually a stale database, not a flake.** The
  negative assertions ("a pending listing must not be searchable") fail on a
  name collision with a business left over from an earlier run. Confirm the
  locator and the expectation match a previous known-good run, then reset:
  `dropdb south_dev && createdb south_dev && ./.venv/bin/alembic upgrade head
  && ./.venv/bin/python -m scripts.seed --ensure`. Never relax or skip the
  assertion.
- **`pkill -f` will kill this shell.** The pattern matches the tool's own
  command line. Bracket the pattern *and* keep the kill in a command that does
  not also contain the literal process string:
  `pkill -f 'uvi[c]orn app.main:app'` on its own line, then start the server in
  a separate call.
- **Read a commit SHA, never reconstruct one.** `git rev-parse HEAD`. A
  hand-typed SHA produces `409 Head branch was modified` or "must be exactly 40
  characters".
