"""Application configuration, sourced exclusively from the environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# staging is production-hardened, with one deliberate relaxation: it may carry
# a known password for the demo accounts so a deployed build can be signed into
# without an administrator issuing credentials by hand.
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

    # Testimonial submission is an unauthenticated write of free text, so the
    # limits are part of the design rather than a later hardening pass. Two
    # rules, because they stop different things: per-IP stops one person
    # spraying the directory, per-business stops one listing being buried in
    # submissions its owner then has to wade through.
    testimonial_per_ip_limit: int = 5
    testimonial_per_ip_window_seconds: int = 3600
    testimonial_per_business_limit: int = 20
    testimonial_per_business_window_seconds: int = 86400

    # Same two-rule shape as testimonials, and for the same reason: one
    # sender spraying the directory and one listing being buried are
    # different problems. Orders are allowed to be more frequent per
    # address, because a household or a shared connection ordering twice is
    # ordinary.
    order_per_ip_limit: int = 10
    order_per_ip_window_seconds: int = 3600
    order_per_business_limit: int = 40
    order_per_business_window_seconds: int = 86400

    # Asking a talent profile for a piece of work. Its own numbers rather
    # than the order ones, because the shape of the traffic is different: a
    # commissioned job is a considered request, not something the same
    # household sends twice in an afternoon, so the per-address allowance is
    # lower and the per-profile one much lower -- one person receiving forty
    # job enquiries a day is a flood, where a shop receiving forty orders is
    # a good day.
    service_request_per_ip_limit: int = 5
    service_request_per_ip_window_seconds: int = 3600
    service_request_per_profile_limit: int = 15
    service_request_per_profile_window_seconds: int = 86400

    # Password sign-in: the guess budget for one identifier — the phone
    # number or the email address as typed. Low, because a person signing in
    # knows their password and a person who does not is guessing. Keyed on the
    # identifier rather than the caller's IP, because the identifier is what
    # an attacker works through: an IP limit alone lets one host walk a list
    # of numbers, and lets a shared connection lock out a whole village.
    # See AuthService.login.
    password_login_limit: int = 10
    password_login_window_seconds: int = 900

    # --- Human verification ------------------------------------------------
    # Cloudflare Turnstile. Unset means the public forms are not captcha
    # protected at all — see app/core/captcha.py for why that is the chosen
    # behaviour rather than a failure.
    turnstile_secret_key: str | None = None

    # --- Public registration ----------------------------------------------
    # Anonymous, so rate limited on the same pattern as testimonials: per
    # address first, then per day across the whole site, so one rotating
    # sender cannot bury the review queue.
    registration_per_ip_limit: int = 3
    registration_per_ip_window_seconds: int = 3600
    registration_per_day_limit: int = 100
    registration_per_day_window_seconds: int = 86400

    # --- Storage -----------------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "var/media"
    # Path prefix the API serves local media from.
    storage_public_prefix: str = "/media"
    max_upload_bytes: int = 5 * 1024 * 1024
    max_gallery_images: int = 10
    # Identity documents run larger than the image cap above (PDFs, scans).
    max_verification_doc_bytes: int = 10 * 1024 * 1024
    # A bug screenshot or a photo of a printed receipt runs larger than a
    # listing image but doesn't need PDF's headroom, so this gets its own cap
    # rather than reusing either.
    max_feedback_attachment_bytes: int = 8 * 1024 * 1024
    max_feedback_attachments_per_ticket: int = 8
    # A business's own papers — commercial register, licence, permit. Same
    # formats and same cap as an identity document, because it is the same
    # kind of artefact: a scan or a PDF a reviewer reads once.
    max_business_documents: int = 6

    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None

    # --- Admin bootstrap ---------------------------------------------------
    admin_email: str | None = "admin@example.com"
    # No default. A default password in a public repository is everybody's
    # password, so a deployed process refuses to start without a real one --
    # see ``enforce_production_safety``. Locally, set it in ``backend/.env``.
    admin_password: str | None = None
    # Falls back to a translated default in the seed script when unset.
    admin_display_name: str | None = None
    # The password the seed script puts on the demo owner accounts. Sign-in is
    # by password now, so without this nobody can open a seeded listing's
    # dashboard without an administrator issuing credentials first — which is
    # correct for real accounts and useless for a demo or an end-to-end run.
    # Refused in production below: these accounts are in the repository, so
    # their password would be too.
    seed_owner_password: str | None = None

    # --- Error tracking ----------------------------------------------------
    # Unset locally: without a DSN the SDK is never initialised at all, so a
    # developer's tracebacks stay on their own machine.
    sentry_dsn: str | None = None
    # Fraction of requests traced. Performance data is far higher volume than
    # errors, so this stays low by default and is tuned per environment.
    sentry_traces_sample_rate: float = 0.0
    # Ties an error to the deploy that introduced it. Railway exposes the
    # commit as RAILWAY_GIT_COMMIT_SHA; map it to this in the service config.
    sentry_release: str | None = None

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
    def is_hardened(self) -> bool:
        """Environments that must pass the production safety checks."""
        return self.app_env in ("staging", "production")

    def enforce_production_safety(self) -> None:
        """Refuse to boot a deployed process with development shortcuts.

        Applies to staging as well as production. The single difference is
        ``seed_owner_password``: staging may set one so the demo accounts can
        be signed into, production may never, because a password shared in a
        repository is not a password.
        """
        if not self.is_hardened:
            return

        problems: list[str] = []
        if self.secret_key == "dev-insecure-secret-change-me":
            problems.append("SECRET_KEY must be set to a strong random value")
        # The admin password is re-applied to the administrator on every
        # deploy, so this is also what rotates one that was ever the old
        # published default: a deploy with a real value replaces the hash.
        if not self.admin_password:
            problems.append("ADMIN_PASSWORD must be set to a strong password")
        elif self.admin_password in PUBLISHED_ADMIN_PASSWORDS:
            problems.append(
                "ADMIN_PASSWORD is a default published in this repository; "
                "set a strong password of your own"
            )
        if self.seed_owner_password and self.is_production:
            problems.append(
                "SEED_OWNER_PASSWORD is not allowed in production; "
                "issue credentials per account instead"
            )
        if self.storage_backend == "s3" and not self.s3_bucket:
            problems.append("S3_BUCKET is required when STORAGE_BACKEND=s3")
        if self.debug:
            problems.append("DEBUG must be false in production")

        if problems:
            raise RuntimeError(
                "Unsafe production configuration:\n  - " + "\n  - ".join(problems)
            )


#: Admin passwords this repository has shipped as defaults at some point. They
#: are readable in its public history, so a deployed process refuses them even
#: though no current file sets one.
PUBLISHED_ADMIN_PASSWORDS: frozenset[str] = frozenset({"ChangeMe!123"})


@lru_cache
def get_settings() -> Settings:
    return Settings()
