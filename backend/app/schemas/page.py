from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PageOut(BaseModel):
    """A static page's administrator-written text; an unset field is null and
    the page shows its built-in text in its place."""

    key: str
    title_ar: str | None = None
    title_en: str | None = None
    summary_ar: str | None = None
    summary_en: str | None = None
    body_ar: str | None = None
    body_en: str | None = None


class PageIn(BaseModel):
    """The whole page at once: a field left empty goes back to the built-in text."""

    title_ar: str | None = Field(default=None, max_length=200)
    title_en: str | None = Field(default=None, max_length=200)
    summary_ar: str | None = Field(default=None, max_length=1500)
    summary_en: str | None = Field(default=None, max_length=1500)
    body_ar: str | None = Field(default=None, max_length=20000)
    body_en: str | None = Field(default=None, max_length=20000)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        if isinstance(value, str):
            # Windows line endings from a pasted document become plain ones,
            # so a paragraph break is always the same thing.
            value = value.replace("\r\n", "\n").strip()
            return value or None
        return value
