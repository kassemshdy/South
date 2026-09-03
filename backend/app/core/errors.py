"""Domain errors and the single standardized API error envelope.

Every error response has the shape::

    {"error": {"code": "...", "message": "...", "details": {...}}}

``code`` is a stable machine-readable identifier the frontend branches on.
``message`` is rendered from a translation key at response time, so the same
error reads correctly in whichever language the caller asked for.
"""

from __future__ import annotations

from typing import Any

from app.core.i18n import translate


class AppError(Exception):
    """Base class for expected, user-visible failures."""

    status_code: int = 400
    code: str = "bad_request"
    message_key: str = "error.bad_request"

    def __init__(
        self,
        message_key: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.message_key = message_key or self.message_key
        self.code = code or self.code
        self.details = details or {}
        self.params = params or {}
        if status_code is not None:
            self.status_code = status_code
        # Exception.__str__ should still be useful in logs and tracebacks.
        super().__init__(f"{self.code}: {self.message_key}")

    def message(self, locale: str | None = None) -> str:
        return translate(self.message_key, locale, **self.params)

    def to_payload(self, locale: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message(locale)}
        if self.details:
            payload["details"] = self.details
        return {"error": payload}


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    message_key = "error.validation"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthenticated"
    message_key = "error.unauthenticated"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    message_key = "error.permission_denied"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message_key = "error.not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message_key = "error.conflict"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    message_key = "error.rate_limited"

    def __init__(
        self, retry_after_seconds: int, message_key: str | None = None
    ) -> None:
        super().__init__(
            message_key, details={"retry_after_seconds": retry_after_seconds}
        )
        self.retry_after_seconds = retry_after_seconds


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"
    message_key = "error.payload_too_large"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "unsupported_media_type"
    message_key = "error.unsupported_media_type"
