# ---------------------------------------------------------------------------
# The API image. Node builds the SPA so the API can serve business-profile
# pages with server-injected SEO tags; the web service fronts everything
# else with its own image (see frontend/Dockerfile).
# ---------------------------------------------------------------------------

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./

# Vite inlines import.meta.env.VITE_* at build time, so every one of these has
# to arrive as a build arg. A Railway *service* variable is invisible to
# `npm run build` and the value silently ends up undefined — which for these
# looks exactly like "not configured": no Sentry, no analytics, no social row,
# with nothing in the logs to say why. This stage builds the bundle the API
# actually serves (see frontend/Caddyfile: the web service proxies /assets/*
# here rather than serving its own copy), so an argument missing here is
# missing in production no matter what the web service was given.
ARG VITE_SENTRY_DSN
ARG VITE_GA_MEASUREMENT_ID
ARG VITE_SOCIAL_INSTAGRAM
ARG VITE_SOCIAL_FACEBOOK
ARG VITE_SOCIAL_TIKTOK
ARG VITE_SUPPORT_WHATSAPP
ARG VITE_TURNSTILE_SITE_KEY
ARG VITE_CLARITY_PROJECT_ID
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN \
    VITE_GA_MEASUREMENT_ID=$VITE_GA_MEASUREMENT_ID \
    VITE_SOCIAL_INSTAGRAM=$VITE_SOCIAL_INSTAGRAM \
    VITE_SOCIAL_FACEBOOK=$VITE_SOCIAL_FACEBOOK \
    VITE_SOCIAL_TIKTOK=$VITE_SOCIAL_TIKTOK \
    VITE_SUPPORT_WHATSAPP=$VITE_SUPPORT_WHATSAPP \
    VITE_TURNSTILE_SITE_KEY=$VITE_TURNSTILE_SITE_KEY \
    VITE_CLARITY_PROJECT_ID=$VITE_CLARITY_PROJECT_ID

RUN npm run build


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libpq for psycopg, the image libraries Pillow links against, and gosu to
# drop root privileges at *runtime* rather than at build time (needed below).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 libjpeg62-turbo libwebp7 zlib1g curl gosu \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./frontend_dist

# Uploads live on a mounted volume so they survive redeploys. The container
# starts as root — a Railway volume is mounted with root ownership no matter
# what the image's user is, so ownership can only be fixed at container
# start (see docker-entrypoint.sh), after which it drops to appuser.
RUN mkdir -p /app/var/media \
 && adduser --disabled-password --gecos "" --uid 10001 appuser \
 && chown -R appuser:appuser /app \
 && chmod +x docker-entrypoint.sh

ENV FRONTEND_DIST_DIR=/app/frontend_dist \
    STORAGE_LOCAL_DIR=/app/var/media \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
