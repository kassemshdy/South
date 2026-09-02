"""Domain errors and the single standardized API error envelope.

Every error response has the shape::

    {"error": {"code": "...", "message": "...", "details": {...}}}

``message`` is Arabic and safe to show to end users; ``code`` is a stable
machine-readable identifier the frontend can branch on.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, user-visible failures."""

    status_code: int = 400
    code: str = "bad_request"
    message: str = "طلب غير صالح."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return {"error": payload}


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    message = "البيانات المدخلة غير صالحة."


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthenticated"
    message = "يجب تسجيل الدخول للمتابعة."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    message = "لا تملك صلاحية تنفيذ هذا الإجراء."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "العنصر المطلوب غير موجود."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "لا يمكن تنفيذ هذا الإجراء في الحالة الحالية."


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "عدد المحاولات كبير. يرجى المحاولة لاحقاً."

    def __init__(self, retry_after_seconds: int, message: str | None = None) -> None:
        super().__init__(message, details={"retry_after_seconds": retry_after_seconds})
        self.retry_after_seconds = retry_after_seconds


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"
    message = "حجم الملف كبير جداً."


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "unsupported_media_type"
    message = "نوع الملف غير مدعوم."
