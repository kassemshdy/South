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

It also needs `SEED_OWNER_PASSWORD` set in the API's environment *before the
seed ran*, because that is when the hash is written, and because the demo
owner accounts the owner specs sign in as are only created when it is set.
`e2e/support/sign-in.ts` defaults to the `.env.example` value, and
`E2E_OWNER_PASSWORD` overrides it. Sign-ins failing across the board is this,
not broken auth: re-seed after changing the variable.

A spec needing an owner takes its number from
`backend/scripts/data/demo_owners.json` via `demoOwnerPhone(key)`, never a
literal. Signing in no longer creates the account it cannot find — the OTP
flow did — so an invented number is just a failed sign-in. A new spec adds an
entry there and re-seeds.

## 6. Look at it, from `frontend/`

Only for a change that alters something a visitor or owner sees. Everything
above passes happily while a layout is unusable, and the exposure plan asks
for a walk through both journeys at 420px after each slice.

```bash
NO_PROXY='localhost,127.0.0.1' HTTP_PROXY= HTTPS_PROXY= \
  node scripts/shoot-mobile.mjs /tmp/shots
```

Same prerequisites as Playwright. It writes nine PNGs and asserts nothing —
**open them.** An agent session can read the files directly, which is the one
way to see a phone layout from here: a browser in this sandbox cannot reach a
deployed host (`ERR_CONNECTION_RESET`), so a claim about how staging looks is
not available, but a claim about how the local build looks is.

Two things it handles that cost time when done by hand: it picks the *oldest*
public listing, because the newest is whatever the acceptance spec just made
and its logo is a 10x10 black test fixture that reads as a broken image; and
it clears the proxy variables, without which Node's `fetch` sends
localhost requests to an outbound proxy that never answers.

## When a step fails

Read `references/traps.md` **before** concluding a failure is real. It lists
the five ways a step here has previously failed for a reason other than the
code under test: an unavailable pytest flag that exits while the shell still
reports success, the no-Arabic guard reading a doc comment, `pkill` killing
its own shell, a stale database failing the acceptance spec's negative
assertions, and a hand-typed commit SHA.

Otherwise: fix the cause, re-run that step, then re-run the whole gate. Never
relax an assertion, skip a test, or narrow a guard's scope to get to green.
