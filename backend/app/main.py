"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.api.v1 import seo as seo_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, RateLimitedError
from app.core.i18n import translate
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.observability import configure_error_tracking
from app.core.seo import business_tags, default_tags, inject, talent_tags
from app.database.session import SessionLocal
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    settings.enforce_production_safety()
    logger.info(
        "Application starting",
        extra={
            "env": settings.app_env,
            "otp_provider": settings.otp_provider,
            "storage_backend": settings.storage_backend,
        },
    )
    yield
    logger.info("Application stopping")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=not settings.is_development)
    # Before the app is built, so a failure during startup is still reported.
    configure_error_tracking(settings)

    app = FastAPI(
        title="South Lebanon Business Directory API",
        version="1.0.0",
        description=(
            "REST API for an Arabic-first business directory. Public endpoints "
            "expose approved businesses only."
        ),
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        expose_headers=["X-Request-Id"],
        max_age=600,
    )

    _register_exception_handlers(app)

    app.include_router(api_router)
    app.include_router(seo_router.router)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    _mount_media(app, settings)
    _mount_frontend(app, settings)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Every error leaves the API in the same envelope shape."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimitedError):
            headers["Retry-After"] = str(exc.retry_after_seconds)
        logger.info(
            "Handled application error",
            extra={"code": exc.code, "status_code": exc.status_code, "path": request.url.path},
        )
        # Rendered here, at the edge, so the message is in the caller's language
        # regardless of how deep in the stack it was raised.
        return JSONResponse(exc.to_payload(), status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Field errors are surfaced so the Arabic forms can highlight the right
        # input rather than showing a generic failure.
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
                "message": error.get("msg", translate("error.field_invalid")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            {
                "error": {
                    "code": "validation_error",
                    "message": translate("error.validation_fields"),
                    "details": {"fields": fields},
                }
            },
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": str(exc.detail) if exc.detail else translate("error.http_generic"),
                }
            },
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Logged with a traceback; the client never sees internal details.
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            {
                "error": {
                    "code": "internal_error",
                    "message": translate("error.internal"),
                }
            },
            status_code=500,
        )


def _mount_media(app: FastAPI, settings: Settings) -> None:
    """Serve locally stored uploads when the local storage backend is active."""
    if settings.storage_backend != "local":
        return
    media_root = Path(settings.storage_local_dir).resolve()
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.storage_public_prefix,
        StaticFiles(directory=str(media_root)),
        name="media",
    )


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    """Serve the built SPA, injecting per-business SEO tags into index.html.

    Only used in the single-container production layout; in development the Vite
    dev server serves the frontend and proxies /api here.
    """
    if not settings.frontend_dist_dir:
        return

    dist = Path(settings.frontend_dist_dir).resolve()
    index_file = dist / "index.html"
    if not index_file.exists():
        logger.warning(
            "FRONTEND_DIST_DIR is set but index.html is missing", extra={"path": str(dist)}
        )
        return

    assets_dir = dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    base_url = settings.public_base_url.rstrip("/")
    default_image_url = f"{base_url}/og-image.png"

    def _absolute(image: str | None) -> str:
        """A stored path is site-relative (``/media/...``); anything else
        (an external URL, or nothing at all) falls back to the share image,
        so a link preview never carries a relative URL a crawler can't
        resolve on its own."""
        if image and image.startswith("/"):
            return f"{base_url}{image}"
        return image or default_image_url

    def _render_index(path: str) -> HTMLResponse:
        document = index_file.read_text(encoding="utf-8")
        tags = None

        if path.startswith("business/"):
            slug = path.removeprefix("business/").split("/")[0]
            db = SessionLocal()
            try:
                business = BusinessRepository(db).get_by_slug(slug, public_only=True)
                if business is not None:
                    tags = business_tags(
                        name=business.name,
                        short_description=business.short_description,
                        category_name=business.category.name_ar if business.category else None,
                        location_name=business.location.name_ar if business.location else None,
                        image_url=_absolute(business.cover_url or business.logo_url),
                        canonical_url=f"{base_url}/business/{quote(business.slug)}",
                    )
            finally:
                db.close()
        elif path.startswith("talent/"):
            slug = path.removeprefix("talent/").split("/")[0]
            db = SessionLocal()
            try:
                profile = TalentRepository(db).get_by_slug(slug, public_only=True)
                if profile is not None:
                    tags = talent_tags(
                        display_name=profile.display_name,
                        skill_name=profile.skill.name_ar if profile.skill else None,
                        headline=profile.headline,
                        bio=profile.bio,
                        location_name=profile.location.name_ar if profile.location else None,
                        image_url=_absolute(profile.photo_url),
                        canonical_url=f"{base_url}/talent/{quote(profile.slug)}",
                    )
            finally:
                db.close()

        if tags is None:
            # Every other route (home, search, dashboard, a business/talent
            # slug that isn't public) still gets an absolute-URL image and
            # canonical instead of the static, relative ones baked into the
            # build — a shared link works the same everywhere on the site.
            trimmed = path.rstrip("/")
            canonical = f"{base_url}/{trimmed}" if trimmed else base_url
            tags = default_tags(canonical_url=canonical, image_url=default_image_url)

        # Explicit and unambiguous: this document is rebuilt per-request (the
        # SEO tags depend on the slug/path), so an edge or CDN in front of the
        # app must never substitute its own default caching heuristic for a
        # bare "/" or similar path — that silently served stale tags across
        # multiple deploys until this header was added.
        return HTMLResponse(
            inject(document, tags),
            headers={"Cache-Control": "no-store, must-revalidate"},
        )

    def _build_file(relative: str) -> Path | None:
        """A real file in the build output, or None.

        Resolved and then checked against ``dist`` so a crafted path can't
        escape it — the containment check is the point, not the existence one.
        """
        candidate = (dist / relative).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist):
            return candidate
        return None

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> Response:
        # Real files in the build output (favicon, manifest, images) are served
        # as-is; everything else falls through to index.html so client-side
        # routing survives a hard refresh or a shared deep link.
        if full_path and full_path != "index.html":
            exact = _build_file(full_path)
            if exact is not None:
                return FileResponse(exact)

            # A standalone page shipped in public/ — the presentation deck — is
            # reachable without its extension, so the link someone forwards is
            # `/presentation` rather than `/presentation.html`. Only ever a
            # fallback: an extensionless path that matches no file is still a
            # client-side route, and a real SPA route always wins because the
            # exact lookup above ran first.
            if "." not in full_path.rsplit("/", 1)[-1]:
                page = _build_file(f"{full_path}.html")
                if page is not None:
                    return FileResponse(page)

        return _render_index(full_path)


app = create_app()
