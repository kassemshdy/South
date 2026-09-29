"""The site's own contact details and social accounts, set by an administrator."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

#: Every setting there is, in the order the admin screen lists them. A key
#: with no row is unset, and the site shows nothing for it.
SITE_SETTING_KEYS: tuple[str, ...] = (
    "contact_phone",
    "contact_whatsapp",
    "contact_email",
    "social_facebook",
    "social_instagram",
)


class SiteSetting(Base):
    """One of the project's own public details, e.g. its Instagram page.

    These used to be build-time variables, so changing a phone number meant a
    Railway change and a redeploy. They are public by nature -- they are how a
    visitor reaches the team -- so every row is readable by anyone.
    """

    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
