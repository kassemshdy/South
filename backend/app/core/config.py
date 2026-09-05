"""Application configuration, sourced exclusively from the environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# staging is production-hardened but permits the development OTP provider, so a
# deployed build can actually be signed into before an SMS gateway exists.
Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Runtime settings.

    Every value has a development-friendly default *except* the ones that would
    be dangerous to default in production; those are validated on startup by
    :meth:`enforce_production_safety`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General -----------------------------------------------------------
    app_env: Environment = "development"
    debug: bool = False
    log_level: str = "INFO"
    # Public origin of the deployed site; used for canonical URLs and sitemaps.
    public_base_url: str = "http://localhost:5173"

    # --- Database ----------------------------------------------------------
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/south_dev"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # --- Security ----------------------------------------------------------
    secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60 * 24 * 14  # 14 days
    # NoDecode: the value is a comma-separated string in .env, not JSON, so
    # the validator below does the parsing instead of pydantic-settings.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # --- OTP ---------------------------------------------------------------
    otp_provider: Literal["mock", "twilio"] = "mock"
    otp_code_length: int = 6
    otp_ttl_seconds: int = 300
    otp_max_verify_attempts: int = 5
    # When set in development, the mock provider always issues this code so the
    # app stays testable without an SMS gateway. Ignored outside development.
    otp_dev_fixed_code: str | None = "123456"
    otp_send_per_phone_limit: int = 3
    otp_send_per_phone_window_seconds: int = 900
    otp_send_per_ip_limit: int = 10
    otp_send_per_ip_window_seconds: int = 3600

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    # --- Storage -----------------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "var/media"
    # Path prefix the API serves local media from.
    storage_public_prefix: str = "/media"
    max_upload_bytes: int = 5 * 1024 * 1024
    max_gallery_images: int = 10
    # Identity documents run larger than the image cap above (PDFs, scans).
    max_verification_doc_bytes: int = 10 * 1024 * 1024

    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None

    # --- Admin bootstrap ---------------------------------------------------
    admin_email: str | None = "admin@example.com"
    admin_password: str | None = "ChangeMe!123"
    # Falls back to a translated default in the seed script when unset.
    admin_display_name: str | None = None

    # --- Frontend serving --------------------------------------------------
    # When set, the API also serves the built SPA from this directory and
    # injects per-business SEO tags into index.html.
    frontend_dist_dir: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"

    @property
    def allows_mock_otp(self) -> bool:
        """Environments where a fixed, non-secret OTP code is acceptable."""
        return self.app_env in ("development", "test", "staging")

    @property
    def is_hardened(self) -> bool:
        """Environments that must pass the production safety checks."""
        return self.app_env in ("staging", "production")

    @property
    def dev_fixed_otp_code(self) -> str | None:
        """The fixed OTP code, or None when it must not be honoured.

        Guarded here rather than at the call site so there is exactly one place
        that can enable it.
        """
        if not self.allows_mock_otp:
            return None
        return self.otp_dev_fixed_code

    def enforce_production_safety(self) -> None:
        """Refuse to boot a deployed process with development shortcuts.

        Applies to staging as well as production. The single difference is the
        mock OTP provider: staging may use it so the deployment is testable,
        production may never, because a fixed code is an authentication bypass.
        """
        if not self.is_hardened:
            return

        problems: list[str] = []
        if self.secret_key == "dev-insecure-secret-change-me":
            problems.append("SECRET_KEY must be set to a strong random value")
        if self.otp_provider == "mock" and not self.allows_mock_otp:
            problems.append(
                "OTP_PROVIDER=mock is not allowed in production; configure a real provider"
            )
        if self.otp_provider == "twilio" and not all(
            [self.twilio_account_sid, self.twilio_auth_token, self.twilio_from_number]
        ):
            problems.append("Twilio credentials are incomplete")
        if self.storage_backend == "s3" and not self.s3_bucket:
            problems.append("S3_BUCKET is required when STORAGE_BACKEND=s3")
        if self.debug:
            problems.append("DEBUG must be false in production")

        if problems:
            raise RuntimeError(
                "Unsafe production configuration:\n  - " + "\n  - ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
