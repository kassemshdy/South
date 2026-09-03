# Railway deployment (project `southwork`)

**Live:** <https://web-production-b8196.up.railway.app>

| | |
|---|---|
| Project | `southwork` (`323dd6ae-af69-4035-9e24-6de498989756`), workspace PulseX |
| Environment | `production` (running `APP_ENV=staging` — see below) |
| Branch | `claude/arabic-business-directory-south-lebanon-gpte8i`, auto-deploys on push |
| Admin sign-in | `/admin/login` — `ADMIN_EMAIL` / `ADMIN_PASSWORD` from the api service variables |
| Owner sign-in | any Lebanese number; the OTP code is **123456** while `APP_ENV=staging` |

Change `ADMIN_PASSWORD` before sharing the URL with anyone.


Three services in one project. Build configuration lives on each service rather
than in a repository-level `railway.json`, because a single config file cannot
describe two different Dockerfiles.

| Service | Dockerfile | Healthcheck | Public |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` image | — | no |
| `api` | `backend/Dockerfile` | `/api/health` | optional (for `/api/docs`) |
| `web` | `frontend/Dockerfile` | `/healthz` | **yes** — this is the site |

## Why the web service is the public entry point

It serves the SPA and reverse-proxies `/api/*`, `/media/*`, `/sitemap.xml`,
`/robots.txt` and `/business/*` to `api.railway.internal:8000` over Railway's
private network. One public origin means the API's relative `/media/...` image
URLs resolve, the browser never makes a cross-origin request, and the
server-rendered Arabic OG tags behind WhatsApp/Facebook link previews survive.

## Service settings

Set per service (Settings → Build / Deploy, or via the MCP `update-service`):

- **api** — Dockerfile path `backend/Dockerfile`, healthcheck `/api/health`,
  volume mounted at `/app/var/media` so uploaded images survive redeploys.
- **web** — Dockerfile path `frontend/Dockerfile`, healthcheck `/healthz`.

## Variables

`api`:

| Variable | Value |
|---|---|
| `APP_ENV` | `staging` (see the environments table in DEPLOYMENT.md) |
| `SECRET_KEY` | a generated 48-byte random string |
| `DATABASE_URL` | `postgresql+psycopg://south:<password>@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/south` — note the `+psycopg` driver |
| `PUBLIC_BASE_URL` / `CORS_ORIGINS` | the **web** service's public domain |
| `OTP_PROVIDER` | `mock` while staging; `twilio` + credentials for production |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | the seeded administrator |
| `STORAGE_BACKEND` | `local` (with the volume above) or `s3` |

`web`:

| Variable | Value |
|---|---|
| `API_INTERNAL_HOST` | `api.railway.internal:8000` |

`PORT` is injected by Railway and honoured by both images.

## First deploy

Migrations and seeding both run automatically when the API container starts,
before it accepts traffic:

```
alembic upgrade head && python -m scripts.seed --ensure && exec uvicorn ...
```

This runs inside the same container that has the media volume mounted —
Railway's separate pre-deploy step does not have volume access, which
previously left seeded businesses with image *rows* pointing at bytes that
were never written anywhere durable. `seed_businesses` now also detects and
repairs that case (missing bytes for an existing row) on every boot, not only
on first creation.

`--ensure` seeds whatever the environment permits and always exits
successfully, so it is safe to run before every deploy:

- **staging** — categories, the location tree, sample businesses and the
  administrator. A staging deployment nobody can click through is not much of a
  staging deployment.
- **production** — the administrator account only. Sample businesses are never
  created there.

It is idempotent: re-running adds only what is missing.

## Going to production

1. Obtain SMS credentials and set `OTP_PROVIDER=twilio` plus the three
   `TWILIO_*` variables.
2. Change `APP_ENV` to `production`.

The API refuses to boot as production with the mock provider, so the switch
either works completely or fails loudly.
