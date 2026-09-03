# Railway deployment (project `southwork`)

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

Migrations run automatically when the API container starts. Bootstrap the
administrator once the API is healthy:

```bash
railway run --service api python -m scripts.seed --admin-only
```

To load the sample categories, locations and businesses into a fresh database,
run the full seed once with `APP_ENV=development` set for that command only —
sample data is refused against staging and production.

## Going to production

1. Obtain SMS credentials and set `OTP_PROVIDER=twilio` plus the three
   `TWILIO_*` variables.
2. Change `APP_ENV` to `production`.

The API refuses to boot as production with the mock provider, so the switch
either works completely or fails loudly.
