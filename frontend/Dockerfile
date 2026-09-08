# ---------------------------------------------------------------------------
# Web service: Caddy serves the built SPA and proxies API traffic.
#
# The proxy is not decoration. It keeps one public origin, which means:
#   - the API's relative /media/... image URLs resolve correctly
#   - the browser never makes a cross-origin request, so no CORS preflights
#   - /business/* is answered by the API, which injects real SEO tags into
#     index.html so link previews work without JavaScript
#
# Build context is the repository root, not frontend/.
# ---------------------------------------------------------------------------

FROM node:22-alpine AS build
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

# Vite inlines import.meta.env.VITE_* at build time, so each one must be a
# build arg, not just a runtime variable on the container — Railway's own
# service variables aren't visible to `npm run build` otherwise.
#
# Keep this list in step with backend/Dockerfile, which builds the bundle that
# is actually served; this image's build only has to stay consistent with it.
ARG VITE_SENTRY_DSN
ARG VITE_GA_MEASUREMENT_ID
ARG VITE_SOCIAL_INSTAGRAM
ARG VITE_SOCIAL_FACEBOOK
ARG VITE_SOCIAL_TIKTOK
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN \
    VITE_GA_MEASUREMENT_ID=$VITE_GA_MEASUREMENT_ID \
    VITE_SOCIAL_INSTAGRAM=$VITE_SOCIAL_INSTAGRAM \
    VITE_SOCIAL_FACEBOOK=$VITE_SOCIAL_FACEBOOK \
    VITE_SOCIAL_TIKTOK=$VITE_SOCIAL_TIKTOK

RUN npm run build


FROM caddy:2-alpine AS runtime

COPY --from=build /build/dist /srv
COPY frontend/Caddyfile /etc/caddy/Caddyfile

# Railway injects PORT; the Caddyfile falls back to 8080 elsewhere.
ENV PORT=8080 \
    API_INTERNAL_HOST=api.railway.internal:8000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider "http://127.0.0.1:${PORT}/healthz" || exit 1
