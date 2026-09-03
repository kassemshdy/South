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
RUN npm run build


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libpq for psycopg, plus the image libraries Pillow links against.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 libjpeg62-turbo libwebp7 zlib1g curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./frontend_dist

# Uploads live on a mounted volume so they survive redeploys.
RUN mkdir -p /app/var/media \
 && adduser --disabled-password --gecos "" --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

ENV FRONTEND_DIST_DIR=/app/frontend_dist \
    STORAGE_LOCAL_DIR=/app/var/media \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# Migrations and seeding run at boot, in the container that actually has the
# media volume mounted — Railway's pre-deploy step runs in a separate,
# volume-less container, which previously left seeded image *rows* pointing
# at bytes that were never written anywhere durable.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed --ensure && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
