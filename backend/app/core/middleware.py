"""Cross-cutting HTTP middleware: request ids, access logs, security headers."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.i18n import current_locale, resolve_locale
from app.core.logging import request_id_var

logger = logging.getLogger("app.access")

Handler = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id and logs one structured line per request."""

    async def dispatch(self, request: Request, call_next: Handler) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        # Held in a context variable so services deep in the stack can translate
        # without every function signature growing a locale argument. Starlette
        # copies the context into the threadpool that runs sync endpoints.
        locale_token = current_locale.set(
            resolve_locale(request.headers.get("accept-language"))
        )
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Logged with the traceback here; the exception handlers turn it
            # into a standardized envelope. Never swallowed.
            logger.exception(
                "Unhandled error",
                extra={"method": request.method, "path": request.url.path},
            )
            raise
        finally:
            current_locale.reset(locale_token)
            request_id_var.reset(token)

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers for both the API and the served SPA."""

    def __init__(self, app, *, enable_hsts: bool = False) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Handler) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"
        )
        if self._enable_hsts:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
