"""A YouTube Short's own thumbnail, kept as a reel's cover.

The home page's reel cards are drawn from our own storage, so the page
makes no request to YouTube until someone opens a reel. When a reel is a
YouTube Short and the administrator gave it no cover, the server fetches
the video's thumbnail once, from ``i.ytimg.com`` and an address built from
the validated eleven-character id -- never from anything pasted -- crops it
to the card's 9:16, and stores it like an uploaded photo.

Best effort: any failure leaves the reel without a cover, which the card
draws as a coloured panel.
"""

from __future__ import annotations

import io
import logging

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

#: Most specific first: ``oardefault`` is the vertical frame YouTube makes
#: for Shorts; the others are landscape with the Short in the middle.
_NAMES = ("oardefault.jpg", "maxresdefault.jpg", "hqdefault.jpg")
_MAX_BYTES = 2 * 1024 * 1024
_TIMEOUT = 5.0


def fetch_short_cover(video_id: str) -> bytes | None:
    """The thumbnail as a 9:16 JPEG, or None if none could be had."""
    for name in _NAMES:
        try:
            response = httpx.get(
                f"https://i.ytimg.com/vi/{video_id}/{name}",
                timeout=_TIMEOUT,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            logger.warning("Could not fetch a YouTube thumbnail", extra={"video_id": video_id})
            return None
        if response.status_code != 200 or len(response.content) > _MAX_BYTES:
            continue
        try:
            return _tall(response.content)
        except Exception:  # an unreadable image is no cover, not an error
            continue
    return None


def _tall(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = image.size
    target = round(height * 9 / 16)
    if target < width:
        left = (width - target) // 2
        image = image.crop((left, 0, left + target, height))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()
