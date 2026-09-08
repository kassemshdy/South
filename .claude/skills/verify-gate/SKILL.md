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

## When a step fails

Read `references/traps.md` **before** concluding a failure is real. It lists
the five ways a step here has previously failed for a reason other than the
code under test: an unavailable pytest flag that exits while the shell still
reports success, the no-Arabic guard reading a doc comment, `pkill` killing
its own shell, a stale database failing the acceptance spec's negative
assertions, and a hand-typed commit SHA.

Otherwise: fix the cause, re-run that step, then re-run the whole gate. Never
relax an assertion, skip a test, or narrow a guard's scope to get to green.
