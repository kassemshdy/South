from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PageCoverOut(BaseModel):
    page_key: str
    #: None when the page shows the site's default photograph.
    image_url: str | None = None
    updated_at: datetime | None = None
