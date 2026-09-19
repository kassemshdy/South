# Deployment

The application deploys as **three services**:

| Service | Source | Role |
|---|---|---|
| `postgres` | managed Postgres | database |
| `api` | `backend/Dockerfile` | FastAPI. Also carries the SPA build so it can render every page's `index.html` with real per-route SEO tags |
| `web` | `frontend/Dockerfile` | Caddy; serves hashed `/assets/*` directly and proxies everything else to the API |

**The web service is the public entry point and proxies almost everything to
the API.** Only pre-hashed, immutable build assets (`/assets/*`) are served
directly by Caddy — every page route (`/`, `/business/*`, `/talent/*`,
`/products/*`, a hard refresh on any client-side route) goes to the API, which
serves the same built files for a real static request and injects real
per-route SEO tags for an HTML one. This used to be a hand-maintained list of
proxied paths (only `/business/*` got real tags; every other route silently
served the generic static `index.html`) — routing everything through the API
instead means a new route never needs a matching Caddyfile change to get
correct tags. A single public origin also keeps the API's relative
`/media/...` image URLs resolving and removes CORS from the browser's path
entirely.

Migrations run automatically when the API container starts.

## Choosing an environment

| `APP_ENV` | Demo passwords | Use it for |
|---|---|---|
| `development` | yes | local work |
| `staging` | yes | a deployed build people can sign into without issuing credentials by hand |
| `production` | **never** | the real thing |

`staging` applies every production safety check except the `SEED_OWNER_PASSWORD`
ban: a weak `SECRET_KEY` still refuses to boot, and security headers and HSTS
still apply. Moving to production is a variable change — no code edit.

---

## Before you deploy

Generate a real secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The application refuses to start in production if `SECRET_KEY` is still the
development default, if `SEED_OWNER_PASSWORD` is set — it is the demo
accounts' password and lives in this repository — or if `DEBUG` is true. That
check lives in `Settings.enforce_production_safety()`.

### Required environment variables

| Variable | Example | Notes |
|---|---|---|
| `APP_ENV` | `production` | |
| `SECRET_KEY` | *(generated above)* | signs JWTs |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/south` | note the `+psycopg` driver |
| `PUBLIC_BASE_URL` | `https://daleeljanoub.com` | canonical URLs, OG tags, sitemap |
| `CORS_ORIGINS` | `https://daleeljanoub.com` | comma-separated |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | | the seeded administrator |
| `STORAGE_BACKEND` | `local` or `s3` | |

With `STORAGE_BACKEND=s3`, also set `S3_BUCKET`, `S3_REGION`,
`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, and `S3_ENDPOINT_URL` +
`S3_PUBLIC_BASE_URL` for non-AWS providers (Cloudflare R2, Backblaze, MinIO).
Add `boto3` to `requirements.txt` when using S3.

---

## Railway

1. **Create the project** and add the **PostgreSQL** plugin. Railway provides
   `DATABASE_URL` automatically — rewrite it to use the `postgresql+psycopg://`
   scheme (Railway supplies `postgresql://`).
2. **Add a service from this repository.** `railway.json` selects
   `backend/Dockerfile`, so no build configuration is needed.
3. **Set the environment variables** from the table above. `PORT` is provided by
   Railway and the container honours it.
4. **Attach a volume** mounted at `/app/var/media` if `STORAGE_BACKEND=local`,
   so uploaded images survive redeploys. Skip this if you use S3.
5. **Deploy.** The healthcheck is `/api/health`.
6. **Create the administrator** once the service is live:

   ```bash
   railway run python -m scripts.seed --admin-only
   ```

   `--admin-only` creates (or updates the password of) the account from
   `ADMIN_EMAIL` / `ADMIN_PASSWORD` and touches nothing else. It is the only
   seeding mode permitted against a production database — sample businesses and
   `--reset` are refused there.

   You will also want categories and locations. Add them through the admin UI
   at `/admin/categories` and `/admin/locations`, or run the full seed once
   against an empty production database with `APP_ENV=development` set for that
   single command.
7. **Add your domain** in Railway's settings and point DNS at it. Update
   `PUBLIC_BASE_URL` and `CORS_ORIGINS` to match.

---

## Any VPS (Docker Compose)

```bash
git clone https://github.com/kassemshdy/South.git
cd South

cat > .env <<'ENV'
DOMAIN=daleeljanoub.com
PUBLIC_BASE_URL=https://daleeljanoub.com
POSTGRES_PASSWORD=<strong password>
SECRET_KEY=<generated>
ENV

docker compose -f docker-compose.prod.yml up -d
```

Caddy obtains and renews a Let's Encrypt certificate for `DOMAIN`
automatically — just point an A record at the server first, and open ports 80
and 443.

Create the administrator:

```bash
docker compose -f docker-compose.prod.yml exec app python -m scripts.seed --admin-only
```

### Backups

```bash
# Database
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U postgres south | gzip > south-$(date +%F).sql.gz

# Uploaded images (when STORAGE_BACKEND=local)
docker run --rm -v south_media_data:/media -v "$PWD":/backup alpine \
  tar czf /backup/media-$(date +%F).tar.gz -C /media .
```

Restore with `gunzip -c backup.sql.gz | docker compose exec -T db psql -U postgres south`.

---

## Moving between hosts

Nothing binds the application to a particular provider: the only coupling is
`DATABASE_URL` plus the storage variables. Moving from Railway to a VPS is a
database dump, a media copy, and the same image running elsewhere.

---

## Operating notes

- **Logs** are single-line JSON with a `request_id`; `X-Request-Id` is honoured
  from the incoming request so a proxy can correlate.
- **Health** is `GET /api/health`.
- **Scaling** — the container runs `WEB_CONCURRENCY` uvicorn workers (default 2).
  Rate limits are stored in PostgreSQL, so they hold across workers and replicas.
  With more than one replica, use S3-compatible storage rather than a local
  volume.
- **`rate_limit_events`** grows with traffic. `DatabaseRateLimiter.purge_expired()`
  clears rows older than a day; call it from a scheduled job if the table grows.
