# Railway deployment (project `southwork`)

**Live:** <https://janoubona.up.railway.app>
**Staging:** <https://web-develop-production-bce3.up.railway.app>

<!-- The previous value here, web-production-b8196, answers Railway's
     "Application not found" and had been wrong long enough that the
     ship-release skill carries a note telling operators not to trust this
     line. Confirmed against both hosts before changing it: b8196 -> 404,
     janoubona -> 200. -->

| | |
|---|---|
| Project | `southwork` (`323dd6ae-af69-4035-9e24-6de498989756`), workspace PulseX |
| Environment | `production` (running `APP_ENV=staging` — see below) |
| Branch | `master-claude` (live) and `develop-claude` (staging), both auto-deploy on push |
| Admin sign-in | `/admin/login` — `ADMIN_EMAIL` / `ADMIN_PASSWORD` from the api service variables |
| Owner sign-in | any Lebanese number; the OTP code is **123456** while `APP_ENV=staging` |

Change `ADMIN_PASSWORD` before sharing the URL with anyone.


Six services in one project — a live trio and a staging trio, all in the single
`production` Railway environment, separated by which branch each tracks rather
than by environment. Build configuration lives on each service rather than in a
repository-level `railway.json`, because a single config file cannot describe two
different Dockerfiles.

| Service | Tracks | Dockerfile | Healthcheck | Public |
|---|---|---|---|---|
| `postgres` | — | `postgres:16-alpine` image | — | no |
| `api` | `master-claude` | `backend/Dockerfile` | `/api/health` | optional (for `/api/docs`) |
| `web` | `master-claude` | `frontend/Dockerfile` | `/healthz` | **yes** — this is the site |
| `postgres-develop` | — | `postgres:16-alpine` image | — | no |
| `api-develop` | `develop-claude` | `backend/Dockerfile` | `/api/health` | no |
| `web-develop` | `develop-claude` | `frontend/Dockerfile` | `/healthz` | yes (staging) |

## Why the web service is the public entry point

It serves only hashed `/assets/*` directly; everything else — `/api/*`,
`/media/*`, and every page route (`/`, `/business/*`, `/talent/*`, a hard
refresh on any client-side route) — is reverse-proxied to
`api.railway.internal:8000` over Railway's private network. One public origin
means the API's relative `/media/...` image URLs resolve, the browser never
makes a cross-origin request, and the server-rendered Arabic OG tags behind
WhatsApp/Facebook link previews survive on every page, not just a
hand-maintained list of proxied paths (a gap that once left `/` itself served
a stale, edge-cached `index.html` with no real SEO tags — see the git history
on `frontend/Caddyfile` for the incident).

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

1. Configure a real OTP provider:
   - `OTP_PROVIDER=whatsapp` plus the `WHATSAPP_*` variables — see
     `WHATSAPP_OTP.md`. This is the live route, because Twilio's signup
     verification does not reach Lebanese numbers.
   - or `OTP_PROVIDER=twilio` plus the three `TWILIO_*` variables, if an SMS
     gateway becomes available.
2. Change `APP_ENV` to `production`.

The API refuses to boot as production with the mock provider, so the switch
either works completely or fails loudly. Do step 1 and step 2 as one change:
production with the mock provider will not start, and `OTP_PROVIDER` set to a
value the deployed build does not know will not start either.

**Neither step blocks owners from signing in any more.** That used to be the
whole reason this page mattered: without a gateway there was no code, and
without a code nobody could get in. There is now a route that needs no
gateway — a public application, an administrator's audit, and a password
handed over from the administrator's own WhatsApp (see *How Somebody Gets
Onto This Site* in `AGENTS.md`). So the OTP switch is an improvement to make
when a phone number becomes available, not an outage to clear.

### Optional: the registration captcha

The public application forms carry a Cloudflare Turnstile widget when, and
only when, both halves are configured:

- `TURNSTILE_SECRET_KEY` on `api` / `api-develop` — an ordinary service
  variable, read at runtime.
- `VITE_TURNSTILE_SITE_KEY` as a **build argument**, because Vite inlines it
  when the bundle is compiled. It is declared in `backend/Dockerfile` (the
  stage that builds the bundle the API serves) and `frontend/Dockerfile`;
  setting it only in the Railway dashboard leaves it undefined and the widget
  silently absent.

With neither set, the forms work and nothing is verified — which is the
correct state for local development and for the test suite, and an acceptable
one in production only while the rate limits are carrying the load alone.
