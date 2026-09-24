# Railway deployment (project `southwork`)

**Live:** <https://janoubona.net> — also reachable at
<https://janoubona.up.railway.app>
**Staging:** <https://janoubona-develop.up.railway.app>

<!-- This line has been wrong twice, and it is the line people trust when a
     deploy looks broken, so here is where these came from: the Railway API's
     own domain list for the `web` and `web-develop` services, which is the
     configuration of record. `janoubona.net` is a custom domain on `web` and
     is the one to give people. Two dead hosts that used to be recorded here
     and must not come back: `web-production-b8196` and
     `web-develop-production-bce3`, both of which answer "Application not
     found". If a probe 404s, re-read the domain list from Railway before
     concluding the deploy failed — the host is the likelier thing to have
     changed. -->

| | |
|---|---|
| Project | `southwork` (`323dd6ae-af69-4035-9e24-6de498989756`), workspace PulseX |
| Environment | `production` (running `APP_ENV=staging` — see below) |
| Branch | `master-claude` (live) and `develop-claude` (staging), both auto-deploy on push |
| Sign-in | `/login`, for everybody — an owner types their phone number, an administrator their `ADMIN_EMAIL`, both with a password. `/admin/login` is the same administrator credentials on an unlinked URL, kept as the way back in when the main form is broken |
| Owner passwords | issued per account by an administrator, at *issue credentials* on the review screen, and relayed over their own WhatsApp |

`ADMIN_PASSWORD` has no default and must be set on both `api` and `api-develop` to a
password of your own: a deployed API refuses to start without one, or with the
default this repository once published (`Settings.enforce_production_safety`).


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
| `SEED_OWNER_PASSWORD` | the demo accounts' password, so a deployed build can be signed into. Refused in production |
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

Set `APP_ENV=production`. That is the whole of it now.

The switch used to be blocked on an SMS or WhatsApp gateway, because without
one no sign-in code was ever delivered and nobody could get in. That
dependency is gone: OTP sign-in was removed, and the only way onto the site is
a public application, an administrator's audit, and a password handed over
from the administrator's own WhatsApp (see *How Somebody Gets Onto This Site*
in `AGENTS.md`).

What production refuses to boot with is a weak `SECRET_KEY` and
`SEED_OWNER_PASSWORD` — the demo accounts' password, which is in this
repository, so it is not a password anywhere real. Clear it from the live
`api` service before flipping `APP_ENV`, or the deploy will fail loudly rather
than quietly running with a known credential on the seeded listings.

### Optional: the registration captcha

The public application forms carry a Cloudflare Turnstile widget when, and
only when, both halves are configured:

- `TURNSTILE_SECRET_KEY` on `api` / `api-develop` — an ordinary service
  variable, read at runtime.
- `VITE_TURNSTILE_SITE_KEY` as a **build argument**, because Vite inlines it
  when the bundle is compiled. It is declared in `backend/Dockerfile` (the
  stage that builds the bundle the API serves) and `frontend/Dockerfile`;
  setting it only on `web` leaves the served bundle's copy undefined and the
  widget silently absent, so it goes on `api` and `api-develop` as well.

The keys come from a free Cloudflare account — dashboard → Turnstile → Add
widget; the domain does not need to be on Cloudflare DNS. The widget's
hostname list has to name every host the form is served from, or it fails on
the ones it does not:

- `janoubona.net`
- `janoubona.up.railway.app`
- `janoubona-develop.up.railway.app`

With neither set, the forms work and nothing is verified — which is the
correct state for local development and for the test suite, and an acceptable
one in production only while the rate limits are carrying the load alone.
