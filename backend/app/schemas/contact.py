from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.phone import normalize_phone
from app.schemas.common import ORMModel

ContactTopic = Literal["feedback", "question", "other"]

# Every control character but tab and newline, NUL included: nothing a person
# types, and a NUL is refused by Postgres outright. The database is reached
# through bound parameters only, so quotes and SQL keywords are stored as the
# text they are rather than stripped.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(value: str) -> str:
    return _CONTROL.sub("", value.replace("\r\n", "\n").replace("\r", "\n")).strip()


class ContactMessageIn(BaseModel):
    """What the floating contact form sends. A name, something to say, and a
    way to answer -- a phone number, an email address, or both."""

    name: str = Field(min_length=2, max_length=80)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = Field(default=None, max_length=254)
    topic: ContactTopic = "question"
    message: str = Field(min_length=5, max_length=2000)
    page_path: str | None = Field(default=None, max_length=300)
    captcha_token: str | None = Field(default=None, max_length=4096)

    @field_validator("name", "message", mode="before")
    @classmethod
    def _clean(cls, value: object) -> object:
        return clean_text(value) if isinstance(value, str) else value

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if isinstance(value, str):
            value = clean_text(value)
            return normalize_phone(value) if value else None
        return value

    @field_validator("email", mode="before")
    @classmethod
    def _blank_email(cls, value: object) -> object:
        if isinstance(value, str):
            value = clean_text(value)
            return value or None
        return value

    @field_validator("page_path", mode="before")
    @classmethod
    def _path_only(cls, value: object) -> object:
        """A site path, without its query string; anything else is dropped."""
        if not isinstance(value, str):
            return value
        path = clean_text(value).split("?", 1)[0].split("#", 1)[0]
        return path[:300] if path.startswith("/") else None


class ContactMessageOut(ORMModel):
    """The administrator's view; there is no other."""

    id: uuid.UUID
    name: str
    phone: str | None = None
    email: str | None = None
    topic: str
    message: str
    page_path: str | None = None
    created_at: datetime
    solved_at: datetime | None = None
