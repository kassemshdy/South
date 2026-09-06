# دليل الجنوب — Agent Guide

This is the source of truth for AI agent instructions on this repo. Editor/tool-specific
files (`CLAUDE.md`, etc.) should import this rather than duplicate it.

## What this is

An Arabic-first business directory for South Lebanon. FastAPI + PostgreSQL backend,
React/Vite frontend, phone/OTP auth, admin moderation workflow. Deployed to Railway as
two sets of three services — `postgres`/`api`/`web` and their `-develop`
counterparts — under the `southwork` project — see
`docs/RAILWAY.md` for the live topology and `docs/DEPLOYMENT.md` for environments.

## Command Execution Guide

### Backend

Commands MUST run inside the virtualenv:

```bash
cd backend
./.venv/bin/pytest tests/ -q
./.venv/bin/ruff check .
./.venv/bin/mypy app scripts
./.venv/bin/alembic upgrade head
```

Postgres must be running locally first (`pg_ctlcluster 16 main start` in this sandbox);
tests run against a real database (`south_test`), not SQLite.

### Frontend

```bash
cd frontend
npm run build
npx tsc -b
CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npx playwright test
```

Playwright needs both the API (`:8000`) and Vite dev server (`:5173`) running, and a
freshly-migrated + seeded database — a leftover business from a previous run can make the
acceptance spec's negative assertions (pending listing must not be searchable) fail on a
name collision. Reset with `dropdb`/`createdb`/`alembic upgrade head`/`scripts.seed --ensure`
if the suite fails on stale state rather than a real regression.

## No Arabic Text in Source Code

**Every user-facing string lives in a locale catalog, never as a literal in code.**

- Backend: `backend/app/locales/{ar,en}.json`, looked up via `app.core.i18n.translate()`
  or the `LazyText`/`LazyJoin` helpers when a translated parameter is embedded in another
  message (needed so the *reader's* locale wins, not the locale active when raised).
- Frontend: `frontend/src/i18n/locales/{ar,en}.json`, looked up via `useT()`/`useI18n()`.
  `TranslationKey = keyof typeof ar` means a wrong or missing key is a compile error.
- Seed/sample content: `backend/scripts/data/*.json`, not inline in `seed_data.py`.
- Test fixtures: `backend/tests/fixtures/arabic_samples.json` + `tests/samples.py::ar()`,
  and `frontend/e2e/fixtures/*.json` — never a hardcoded Arabic literal in a test file.

`backend/tests/test_i18n.py` scans `backend/app`, `backend/scripts`, `backend/tests` and
`frontend/src`/`frontend/e2e` for Arabic codepoints outside the catalogs and fixture files
and fails the build if it finds one. That test is the actual guard — treat any Arabic
literal outside `locales/`, `scripts/data/`, or a fixture file as a bug, not a style nit.

## Security Musts

- **Never commit secrets.** `SECRET_KEY`, `ADMIN_PASSWORD`, Twilio credentials, and the
  admin bootstrap password are Railway environment variables, never literals in code,
  docs, or commit messages.
- **Scope every business query to its owner.** Dashboard/owner endpoints (`/api/my/*`)
  must filter by the authenticated user's id — never trust a business id alone from the
  request. See `app/repositories/business.py` for the existing scoping pattern before
  adding a new owner-facing endpoint.
- **Public endpoints only ever return `APPROVED` businesses.** A pending/rejected/
  suspended listing must be invisible to an unauthenticated request, both via search and
  via its direct `/business/{slug}` URL — the acceptance test asserts this explicitly.
- Production refuses to boot with the mock OTP provider or a weak `SECRET_KEY` — see
  `Settings.enforce_production_safety()` in `app/core/config.py`. Don't weaken this to
  make a deploy easier; fix the underlying config instead.
- **Nothing an owner authenticates with may reach Sentry.** Both SDKs run with PII
  collection off, and `app/core/observability.py` additionally drops the query string
  and request body and recursively redacts credential-shaped keys. A business's
  *published* phone number is public and deliberately survives — `tests/
  test_observability.py` pins that distinction, so widen `SENSITIVE_KEYS` rather than
  loosening the scrub.

## Error Tracking

Two Sentry projects under the `dotcom-yj` org, owned by the `south` team:
`south-api` (backend) and `south-web` (frontend). Each is wired by a DSN set per
service in Railway — `SENTRY_DSN` on `api`/`api-develop`, `VITE_SENTRY_DSN` on
`web`/`web-develop` — and both SDKs are inert without one, so local tracebacks
never leave the machine and the test suite never touches the network.
`SENTRY_RELEASE` is set to `${{RAILWAY_GIT_COMMIT_SHA}}` so an error points at the
deploy that introduced it.

## Deploy Gotchas (learned the hard way)

- **Anything that writes to `/app/var/media` must run in the container that actually has
  the volume mounted.** Railway's `preDeployCommand` runs in a separate, volume-less
  container — seeding images there silently discards them. Migrations and seeding both
  run from the API image's own start command (`backend/Dockerfile` →
  `docker-entrypoint.sh`) for this reason.
- **A Railway volume is mounted with root ownership regardless of the image's `USER`.**
  The API container starts as root, `chown`s the mounted volume, then drops to `appuser`
  via `gosu` before running anything — see `backend/docker-entrypoint.sh`.
- **`seed_businesses` self-heals missing image bytes**, not just missing rows: it checks
  `storage.exists()` per image, not just whether the `Business` row exists, and
  regenerates anything missing. This matters because a business row can survive a bad
  deploy while its files don't.
- **The `postgres` service currently has no persistent volume.** Any Postgres redeploy
  (including one triggered by only changing its environment variables) wipes the entire
  database back to empty — schema and all. Recovery is a redeploy of the `api` service
  (its start command re-runs migrations + seed), but avoid triggering a Postgres redeploy
  at all until this is fixed. Before setting *any* variable or config on `postgres`, check
  whether it forces a redeploy, and confirm with the user first if so.
- **Point-in-Time Recovery (`WAL_ARCHIVE_*` variables) only works on Railway's own managed
  Postgres image.** This project's `postgres` service runs plain `postgres:16-alpine` from
  Docker Hub — pgBackRest isn't installed, so those variables are inert. Real PITR here
  would require migrating to Railway's managed Postgres template, not just setting vars.

## Testing Conventions

- Backend tests run against a real Postgres (`tests/conftest.py`), truncating tables
  between tests rather than mocking the database.
- New Arabic-language assertions or fixtures go through `tests/samples.py::ar(key)` and
  `tests/fixtures/arabic_samples.json` — never a literal string in the test file.
- The Playwright acceptance spec (`frontend/e2e/acceptance.spec.ts`) reads its expected UI
  text from the same catalog the app renders from (`ar.json`) and its test data from the
  same seed files the app is loaded with, so it can't silently drift from what's actually
  shipped.

## Pull Requests / Deploys

- Run the full local gate before pushing anything meant to deploy: backend pytest +
  ruff + mypy, frontend `tsc -b` + build, the no-Arabic guard (part of the backend suite),
  and — for anything touching the owner/admin flow — the Playwright acceptance spec.
- Two branches auto-deploy on push: `master-claude` drives the live services
  (`api`, `web`) and `develop-claude` drives the staging pair (`api-develop`,
  `web-develop`). Treat `master-claude` as production: verify locally first, and check
  Railway deploy status/logs after pushing rather than assuming success. Feature work
  goes to `develop-claude` first, then to `master-claude`.
