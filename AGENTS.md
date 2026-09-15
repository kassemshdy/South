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

**Arabic copy is Modern Standard Arabic (فصحى), not Lebanese colloquial.**
The catalogs are read by people across the region and by search engines, and
mixed registers read as carelessness — one screen addressing someone as
«شو بدّك تعمل؟» beside another saying «نشاطك قيد المراجعة» is two different
voices. Write «ماذا تريد أن تفعل؟». This is a convention no test can catch,
because colloquial Arabic is still Arabic: the no-Arabic-in-source guard
below has nothing to say about register, so it is on the author and the
reviewer. Markers to watch for: مش، هون، هلق، بعدين، فيك، بدّك، شو، هيك،
عم + verb، يلّا، and the ب- present tense (بتعمل، بيصير).

**One string deliberately does not live here: the WhatsApp code message.** When
`OTP_PROVIDER=whatsapp`, the sign-in code is delivered as a WhatsApp
*authentication template*, whose wording is registered and approved at Meta and
referenced by name — the API sends only the code. So `auth.sms.body` is not what
a WhatsApp recipient reads, and registering an Arabic template is part of
configuring that provider rather than an optional nicety. This is the only
exception, and it exists because the text is not ours to ship — see
`docs/WHATSAPP_OTP.md`.

`backend/tests/test_i18n.py` scans `backend/app`, `backend/scripts`, `backend/tests` and
`frontend/src`/`frontend/e2e` for Arabic codepoints outside the catalogs and fixture files
and fails the build if it finds one. That test is the actual guard — treat any Arabic
literal outside `locales/`, `scripts/data/`, or a fixture file as a bug, not a style nit.

## Agent Configuration

Everything an agent needs to work here is version-controlled, so it is
reviewed like code and improves when someone fixes it rather than living in
one person's head.

| Path | What it is |
|---|---|
| `AGENTS.md` (this file) | The source of truth. `CLAUDE.md` imports it; editor-specific files should too, never duplicate it. |
| `REVIEW.md` | What a review looks for, in tiers. The blocking tier is the Security Musts below, each with the test that pins it. |
| `.claude/skills/verify-gate/` | The full local gate, plus the traps that have actually cost time here. |
| `.claude/skills/steward/` | How to drive a PR on this repo: branch base, the three CI jobs, red checks, review comments. |
| `.claude/skills/ship-release/` | Promoting `develop-claude` to `master-claude`, with the pre-flight that establishes no data is lost. |
| `.claude/skills/triage-loop/` | One pass of the ticket board: pick a ticket, fix it, open a PR, record it. What the scheduled routine runs. |
| `.claude/commands/verify.md` | Slash command; it invokes the skill rather than restating it, so there is one copy to keep correct. |
| `.claude/settings.json` | Pre-approved tools. Read-only commands and MCP reads are allowed; anything that writes still prompts. |
| `docs/MCP.md` | The agent-facing MCP server: read the whole directory, write only to the ticket board. |
| `docs/WHATSAPP_OTP.md` | Delivering the sign-in code over WhatsApp: what the Meta account needs, why the code message is not in a locale catalog, and the order the switch must happen in. |

**When a mistake repeats, fix the artifact rather than the instance.** A skill
or a line in this file is worth more than a correction in one conversation,
which is gone next session. Three of the traps in `verify-gate` are there
because an agent hit them in this repo, not because they were predicted.

### The scheduled triage routine

A Routine runs `triage-loop` on a schedule: one ticket per pass, a pull
request, and a comment on the ticket saying what happened. It needs
`SOUTH_API_URL`, `SOUTH_AGENT_EMAIL` and `SOUTH_AGENT_PASSWORD` on the
execution environment, and **stops and says so when they are absent** rather
than finding something else to do — an unconfigured pass that improvises is
how invented work becomes a pull request.

Three things it is not allowed to do, and none of them are oversights:
approve or suspend a listing (the MCP server has no such tool), merge, or move
a ticket to `DONE`. `DONE` means shipped, which a person decides after a
merge.

The agent signs in as the existing administrator account, so the board cannot
tell the routine's tickets and comments apart from that person's own. That is
a legibility cost rather than a security one, and a second admin row fixes it
whenever it starts to matter — nothing in the design assumes one.

### Patterns borrowed from elsewhere

The skills here follow the open Agent Skills format and take their structure
from [getsentry/skills](https://github.com/getsentry/skills), which is worth
reading before writing a new one. Borrowed deliberately:

- **`SKILL.md` is a router, not an encyclopedia.** Checklists, tables and
  commands in the skill; deep knowledge in `references/`, and every reference
  named with an explicit "open when ..." reason so it is fetched on purpose
  rather than by default.
- **A `SPEC.md` next to each skill states its maintenance contract** — what
  the skill must stay in step with, and what would make it wrong. These files
  describe commands and CI jobs, so they go stale silently; the contract says
  where to look.
- **A description written for routing**, dense with the words someone would
  actually use, because it is the only thing read when deciding whether the
  skill applies.
- **An explicit stopping condition on any loop.** `steward` takes its
  state-to-action table and its two-attempts-then-ask rule from that repo's
  `iterate-pr`.

Not adopted: its Django access and performance review skills, which do not
apply — this backend is FastAPI and SQLAlchemy, so a Django-shaped review
would mislead rather than help.

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
- **An account holder's identity is stored on `users`, and no public schema carries it.**
  Legal name, birth year, gender, marital status, place of civil registration and place
  of residence describe the person, not a listing — one account holds one copy, shared by
  its talent profile and every business it owns, set through `PATCH /api/me`. Publishing
  any of them means adding the field to a public `*Out` class, which is the only thing
  standing between those columns and the open internet: read it back through
  `OwnerIdentityOut` on a review payload instead. `tests/test_identity.py` pins that
  boundary, so treat a failure there as a disclosure bug rather than a stale assertion.
- **The view counter stores nothing about a visitor.** `listing_view_daily`
  holds a listing id, a UTC date and an integer — no address, cookie, session
  id, user agent or fingerprint. That is what made per-listing analytics
  acceptable here at all, so it is pinned by
  `tests/test_views.py::test_the_counter_table_stores_nothing_about_a_visitor`,
  which asserts the exact column set. A visitor-identifying column is a
  design change to argue for, not a convenience to add while debugging. The
  consequence is a labelling rule with teeth: without a per-visitor
  identifier the number is a count of **views**, never of visitors or
  people, and every string that renders it must say so.
- **A public route reads the caller through `Viewer`, never `OptionalUser`.**
  `OptionalUser` returns None only for a request with no token and raises 401
  for a bad one, and the frontend attaches whatever token is in local storage
  to every request — so an expired session would 401 the public listing pages.
  `Viewer` degrades to anonymous. See `app/core/dependencies.py`.
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

## Agent-Facing MCP Server

`mcp-server/` exposes the directory over MCP: **read all of it, write only to
the support ticket board.** Full detail in `docs/MCP.md`; the parts that
constrain how you work on it:

- It is an **HTTP client of the API**, holds no database connection, and
  imports nothing from `backend/app`. Writes therefore land on a service, which
  calls a repository — there is no second path into the database, and no
  database credential to leak. Keep it that way: a direct session here would
  bypass every rule the service layer enforces.
- It has **its own virtualenv**, because `mcp` requires `pydantic>=2.12` and
  the backend pins `pydantic==2.10.4`. Never install `mcp` into
  `backend/.venv`.
- **Owner identity is redacted in `south_mcp/redaction.py`** before any tool
  returns. `AdminBusinessOut`/`AdminTalentOut` carry `owner_identity` and the
  owner's personal phone for a human reviewer; an agent never needs them, and
  ticket text is written by other people. Widen `REDACTED_KEYS` rather than
  loosening the strip — `mcp-server/tests/test_redaction.py` is the guard,
  the counterpart to `backend/tests/test_identity.py`.
- **No tool moderates a listing or reads a personal document.** Approving,
  rejecting, suspending and the verification/CV downloads are deliberately
  absent, and a test asserts no tool name matches them.
- `update_ticket` is **one** tool that routes `status` to `/move` and
  everything else to the edit route, because the edit route silently ignores a
  status and answers 200.

## Optional Integrations Are Inert Without Their Variable

Every third-party integration follows the Sentry pattern above: a `VITE_`-prefixed
variable set per service in Railway, and **nothing at all when it is unset** — no
script tag, no network request, no half-configured UI. Local development and the
test suite therefore never phone home, and never pollute anyone's numbers with a
developer's own clicks.

**A `VITE_` variable is a build argument, not a runtime one.** Vite inlines
`import.meta.env.VITE_*` when the bundle is compiled, so setting it as a Railway
*service* variable does nothing on its own — `npm run build` never sees it, the
value comes out undefined, and the feature looks simply "not configured" with
nothing in the logs to say otherwise. Every such variable must therefore be
declared as an `ARG`+`ENV` pair in **`backend/Dockerfile`**, whose Node stage
builds the bundle the API actually serves (`frontend/Caddyfile` proxies
`/assets/*` to the API rather than serving the web image's own copy), and kept in
step in `frontend/Dockerfile`. Adding a new `VITE_` variable means editing both
Dockerfiles, not just the Railway dashboard.

| Variable | Effect when unset |
|---|---|
| `VITE_SENTRY_DSN` | The frontend SDK does not initialise. |
| `VITE_GA_MEASUREMENT_ID` | No analytics script is injected and no page view is sent (`src/services/analytics.ts`). |
| `VITE_SOCIAL_INSTAGRAM` / `_FACEBOOK` / `_TIKTOK` | That link is not rendered; with none set the whole footer block disappears (`src/components/layout/SocialLinks.tsx`). |
| `VITE_SUPPORT_WHATSAPP` | The assisted-listing offer — "contact us and we will list it for you" — is not rendered anywhere (`src/features/onboarding/AssistedListing.tsx`). A number with no digits in it counts as unset, because the guard is `whatsappHref` itself. |

Analytics additionally **drops the query string and skips `/dashboard` and
`/admin`**: `?q=…` carries whatever someone typed into search, which can be a
person's or a shop's name, and counting our own moderation clicks would corrupt
the only question analytics exists to answer. Widen those exclusions rather than
narrowing them.

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
