"""Recognising a link to one Instagram post or reel.

The home page's reels row embeds Instagram's own player, so what an
administrator pastes has to name exactly one post. The link is read, never
fetched: nothing here makes a request, so a pasted address cannot make the
server talk to anything. Only the post's kind and code are kept, and the
canonical and embed addresses are rebuilt from them on ``www.instagram.com``,
so whatever else the pasted link carried -- a tracking ``igsh`` parameter, a
username, a different host -- goes no further.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

HOSTS = frozenset({"instagram.com", "www.instagram.com", "m.instagram.com"})

#: ``/reels/`` is how the app shares a reel; ``/tv/`` is the old IGTV path,
#: still served. Instagram's newer share links put the account first:
#: ``/<username>/reel/<code>/``.
_PATH = re.compile(
    r"^/(?:[A-Za-z0-9._]{1,30}/)?(?P<kind>reels?|p|tv)/(?P<code>[A-Za-z0-9_-]{5,64})/?$"
)


@dataclass(frozen=True)
class InstagramPost:
    kind: str
    code: str

    @property
    def url(self) -> str:
        return f"https://www.instagram.com/{self.kind}/{self.code}/"

    @property
    def embed_url(self) -> str:
        return f"https://www.instagram.com/{self.kind}/{self.code}/embed/"


def parse_instagram_post(value: str) -> InstagramPost | None:
    """The post a link names, or None when it is not a link to one post."""
    text = value.strip()
    if not text:
        return None
    if "://" not in text:
        text = f"https://{text}"
    try:
        parts = urlsplit(text)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or parts.username or parts.password:
        return None
    if (parts.hostname or "").lower() not in HOSTS or parts.port not in (None, 443, 80):
        return None
    match = _PATH.match(parts.path)
    if match is None:
        return None
    kind = "reel" if match["kind"] in ("reel", "reels") else match["kind"]
    return InstagramPost(kind=kind, code=match["code"])
