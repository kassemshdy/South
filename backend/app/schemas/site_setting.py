from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.phone import normalize_optional_phone
from app.core.urls import normalize_social_url
from app.models.enums import SocialPlatform


class SiteSettingsOut(BaseModel):
    """The site's public contact details; a field that is unset is null."""

    contact_phone: str | None = None
    contact_whatsapp: str | None = None
    contact_email: str | None = None
    social_facebook: str | None = None
    social_instagram: str | None = None


class SiteSettingsIn(BaseModel):
    """The whole set at once: a field left empty clears that setting.

    Every value is validated the way an owner's listing is, because each one
    is rendered as a link on every page: a phone number is normalised, and a
    social link must be an http(s) address on that platform's own site -- so a
    ``javascript:`` URL or a look-alike host can never reach the footer.
    """

    contact_phone: str | None = Field(default=None, max_length=25)
    contact_whatsapp: str | None = Field(default=None, max_length=25)
    contact_email: EmailStr | None = None
    social_facebook: str | None = Field(default=None, max_length=500)
    social_instagram: str | None = Field(default=None, max_length=500)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("contact_phone", "contact_whatsapp")
    @classmethod
    def _phones(cls, value: str | None) -> str | None:
        return normalize_optional_phone(value)

    @field_validator("social_facebook")
    @classmethod
    def _facebook(cls, value: str | None) -> str | None:
        return normalize_social_url(SocialPlatform.FACEBOOK, value) if value else None

    @field_validator("social_instagram")
    @classmethod
    def _instagram(cls, value: str | None) -> str | None:
        return normalize_social_url(SocialPlatform.INSTAGRAM, value) if value else None
