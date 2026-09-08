---
name: verify-gate
description: Run this repo's full verification gate before pushing or opening a PR — backend pytest/ruff/mypy against a real Postgres, the MCP server suite, frontend tsc/build, the no-Arabic-in-source guard, and the Playwright acceptance spec. Use when asked to verify, check, run the gate, run the tests, or before any commit meant to deploy.
license: Apache-2.0
compatibility: Requires the sandbox's local Postgres and the checked-in virtualenvs.
---

# The gate

Run these in order. Report which passed and which did not — never claim a step
you did not run or whose output you did not read.

## 1. Postgres

`pg_ctlcluster 16 main start` if it is down. Tests run against a real
database, not SQLite.

## 2. Backend, from `backend/`

```bash
./.venv/bin/pytest tests/ -q      # includes the no-Arabic guard
./.venv/bin/ruff check .
./.venv/bin/mypy app scripts
```

Expect ~196 passing. Takes about three minutes — if a wrapper kills it at two,
run it in the background rather than shortening it.

## 3. MCP server, from `mcp-server/`

```bash
./.venv/bin/python -m pytest tests -q
../backend/.venv/bin/ruff check .
../backend/.venv/bin/mypy south_mcp
```

It has its own virtualenv on purpose: `mcp` requires `pydantic>=2.12` and the
backend pins `2.10.4`. **Never install `mcp` into `backend/.venv`** — it would
silently upgrade the API's own validation library. `ruff` and `mypy` come from
the backend venv against `mcp-server/pyproject.toml`, which mirrors the
backend's settings.

## 4. Frontend, from `frontend/`

```bash
npx tsc -b
npm run build
```

## 5. Playwright, from `frontend/`

```bash
CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npx playwright test
```

Needs the API on `:8000`, Vite on `:5173`, and a **clean database**.

## Traps that have actually cost time here

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
