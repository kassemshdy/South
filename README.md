# دليل الجنوب — South Lebanon Business Directory

An Arabic-first, mobile-first directory of local businesses in South Lebanon.
Shop owners register with their phone number, build a small storefront (photos,
products, prices, contact links) and submit it for review; nothing appears
publicly until an administrator approves it. Visitors browse, search and filter
without an account.

> **اكتشف وادعم الأعمال المحلية في جنوب لبنان.**

---

## Contents

- [What it does](#what-it-does)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [API](#api)
- [Testing](#testing)
- [Deployment](#deployment)
- [Further documentation](#further-documentation)

---

## What it does

**Visitors** (no account) browse approved businesses, search by name,
description or product, filter by category and location, open a business
profile, and contact the owner by phone or WhatsApp.

**Business owners** sign in with a Lebanese phone number and a one-time code,
then create one or more listings through a six-step wizard: basics → location →
images → social links → products → review. A listing starts as a draft and
becomes public only after approval.

**Administrators** sign in separately with an email and password, work through a
review queue, approve or reject with a reason, suspend or reactivate published
listings, manage categories and locations, and see platform statistics. Every
decision is written to an append-only audit trail.

### Moderation states

```
DRAFT ──submit──> PENDING_REVIEW ──approve──> APPROVED ──suspend──> SUSPENDED
                        │                                              │
                        └──reject──> REJECTED ──submit──┐              │
                                                        └──────────────┘
                                          (reactivate returns to APPROVED)
```

Only `APPROVED` businesses are returned by public endpoints, listed in the
sitemap, or reachable at `/business/{slug}`.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 · TypeScript (strict) · Vite · Tailwind CSS · TanStack Query · React Hook Form · Zod |
| i18n | JSON catalogs on both sides; no user-facing string lives in code |
| UI | Hand-rolled shadcn-style primitives on Radix UI, fully RTL |
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 |
| Database | PostgreSQL 16 (with `pg_trgm` for Arabic substring search) |
| Auth | Phone + OTP for owners, email + password for admins, JWT bearer tokens |
| Storage | Pluggable: local disk (default) or any S3-compatible service |
| Deployment | Three services (Postgres, API, web) on Railway, or `docker compose` on any VPS |

---

## Quick start

### With Docker (recommended)

```bash
git clone https://github.com/kassemshdy/South.git
cd South
docker compose up
```

Then, in another terminal, load development data:

```bash
docker compose exec api python -m scripts.seed --reset
```

- Site: <http://localhost:5173>
- API docs: <http://localhost:8000/api/docs>

### Without Docker

Requires Python 3.11+, Node 22+ and a running PostgreSQL 16.

```bash
# 1. Database
createdb south_dev

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # adjust DATABASE_URL if needed
alembic upgrade head
python -m scripts.seed --reset
uvicorn app.main:app --reload --port 8000

# 3. Frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173, /api proxied to :8000
```

### Signing in during development

| Role | Credentials |
|---|---|
| Business owner | Any Lebanese number (e.g. `03123456`), OTP code **`123456`** |
| Administrator | `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env` (defaults: `admin@example.com` / `ChangeMe!123`) — sign in at `/admin/login` |

The fixed OTP code works **only** when `APP_ENV=development`. The application
refuses to start in production with the mock OTP provider configured.

---

## Translations

No user-facing string is written in source. Everything lives in JSON catalogs:

| Catalog | Covers |
|---|---|
| `frontend/src/i18n/locales/{ar,en}.json` | every string the interface renders (419 keys) |
| `backend/app/locales/{ar,en}.json` | API error and status messages (97 keys) |
| `backend/scripts/data/*.json` | seed content — categories, locations, sample businesses |

Arabic is the default and the source of truth. To change wording, edit
`ar.json`; to add a language, copy it and translate.

The frontend derives its key type from the Arabic catalog
(`TranslationKey = keyof typeof ar`), and `en.json` is typed as
`Record<TranslationKey, string>` — so a missing or misspelled key is a **build
error**, not a blank space in production. The backend negotiates
`Accept-Language` and renders error messages at the response edge, so the same
error reads correctly in whichever language the caller asked for while the
machine-readable `error.code` stays stable.

A test (`backend/tests/test_i18n.py`) fails the build if an Arabic character
appears anywhere outside those catalogs and fixture files.

The interface currently ships Arabic-only — `setLocale` exists and the English
catalog is complete, but no language switcher is exposed yet.

## Configuration

All configuration is environment-driven; nothing secret is committed. See
[`backend/.env.example`](backend/.env.example) for the complete annotated list.
The values you must change before a real deployment:

| Variable | Why |
|---|---|
| `SECRET_KEY` | Signs JWTs. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Your PostgreSQL instance |
| `PUBLIC_BASE_URL` | Used for canonical URLs, OG tags and the sitemap |
| `APP_ENV` | `staging` for a testable deployment, `production` once a real SMS gateway exists |
| `OTP_PROVIDER` | `mock` is refused in production; allowed in staging; use `twilio` in production |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | The seeded administrator account |
| `CORS_ORIGINS` | Comma-separated allowlist |

### Swapping the OTP provider

`app/auth/otp/base.py` defines a small `OtpProvider` protocol. `mock.py` logs
codes for development and `twilio.py` sends SMS. To use a different gateway —
a WhatsApp sender or a Lebanese SMS aggregator — add one file implementing
`send()` and `fixed_code()`, register it in `factory.py`, and set
`OTP_PROVIDER`. No authentication logic changes.

### Swapping image storage

`app/storage/base.py` defines `StorageBackend` (`save` / `delete` / `url_for`).
`local.py` writes to disk (fine in production behind a mounted volume) and
`s3.py` speaks the S3 API, so AWS S3, Cloudflare R2, Backblaze B2 and MinIO all
work by setting `STORAGE_BACKEND=s3` plus the `S3_*` variables. Only image
*metadata* is stored in PostgreSQL.

---

## Project layout

```
backend/
  app/
    api/          HTTP layer — routing and serialization only
    core/         config, security, errors, logging, rate limiting, Arabic/phone/URL helpers
    models/       SQLAlchemy models
    schemas/      Pydantic request/response DTOs
    repositories/ data access — the only layer that touches the ORM
    services/     business rules (moderation, business, items, images)
    auth/otp/     OTP provider protocol + adapters
    storage/      storage protocol + adapters
  alembic/        migrations
  scripts/seed.py development seed data
  tests/          pytest suite
frontend/
  src/
    components/ui|layout   reusable primitives and shell
    features/              auth, businesses, items, images
    pages/                 route components (public, dashboard, admin)
    hooks/ services/api/ types/ utils/
  e2e/            Playwright acceptance test
docs/             architecture, database and deployment documentation
```

The dependency direction is strictly **API → service → repository → model**.
Routers contain no business rules; repositories make no authorization
decisions.

---

## API

Interactive docs are served at `/api/docs` when the backend is running.

**Public** — `GET /api/categories`, `/api/locations`, `/api/businesses`
(`?q=&category=&location=&sort=&page=&page_size=`), `/api/businesses/latest`,
`/api/businesses/{slug}`, `/sitemap.xml`, `/robots.txt`

**Auth** — `POST /api/auth/request-otp`, `/api/auth/verify-otp`,
`/api/auth/admin/login`; `GET|PATCH /api/me`

**Owner** — `GET /api/my/businesses`; `POST /api/businesses`;
`GET|PUT|DELETE /api/businesses/{id}`; `POST /api/businesses/{id}/submit`;
images and items under `/api/businesses/{id}/images` and `/items`

**Admin** — `/api/admin/businesses[/pending|/{id}]`,
`/{id}/approve|reject|suspend|reactivate`, CRUD `/api/admin/categories` and
`/locations`, `/api/admin/users`, `/api/admin/stats`

Errors always use one envelope:

```json
{ "error": { "code": "validation_error", "message": "…", "details": { } } }
```

---

## Testing

```bash
# Backend (needs a PostgreSQL database named south_test)
cd backend
pytest                     # 97 tests
ruff check . && mypy app scripts

# Frontend
cd frontend
npm run typecheck && npm run build

# End-to-end acceptance flow in a real browser
npx playwright install chromium      # first run only
npm run e2e
```

The Playwright suite drives the full scenario on a phone-sized viewport:
browse anonymously → sign in by phone → create a business with images and priced
products → submit → confirm it is *not* publicly visible → approve it as an
administrator → confirm it becomes searchable and its profile renders.

The e2e run writes into the development database, so re-seed with
`python -m scripts.seed --reset` before repeating it.

---

## Deployment

The `backend/Dockerfile` is a multi-stage build: Node builds the SPA, then the
Python image serves both the API and the built frontend — including
server-rendered SEO tags for `/business/{slug}`, so WhatsApp and Facebook link
previews work. One image runs anywhere.

Three services:

| Service | Image | Role |
|---|---|---|
| `postgres` | Railway PostgreSQL | database |
| `api` | `backend/Dockerfile` | FastAPI; also renders SEO'd `/business/*` HTML |
| `web` | `frontend/Dockerfile` | Caddy serving the SPA, proxying `/api`, `/media`, `/sitemap.xml`, `/robots.txt` and `/business/*` to the API |

The web service holds the public domain and proxies rather than standing alone,
which keeps one origin: image URLs resolve, the browser makes no cross-origin
requests, and the server-rendered Arabic OG tags that make WhatsApp and Facebook
link previews work survive.

- **Railway** — `railway.json` selects the API Dockerfile; the web service points
  at `frontend/Dockerfile`. Attach a volume at `/app/var/media` when using local
  image storage.
- **Any VPS** — `docker compose -f docker-compose.prod.yml up -d`, with Caddy
  terminating TLS automatically.

Migrations run automatically on container start. Full instructions, including
the first-administrator step, are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Further documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layering, request lifecycle, key decisions
- [`docs/DATABASE.md`](docs/DATABASE.md) — schema, relationships, indexes, migrations
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Railway and VPS deployment, backups, going live

---

## Notes on scope

This is a deliberately simple first version. Built to grow, but not built yet:
moderation of *edits* to already-approved listings (the transition table in
`app/services/moderation.py` is the single place to add it), full
internationalization (the UI is Arabic-only, though the layout uses logical CSS
properties so an English locale would not require restyling), map embedding, and
search beyond PostgreSQL (the repository interface is designed so OpenSearch
could be added without changing any frontend contract).
