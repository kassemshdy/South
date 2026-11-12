"""Links to videos of a services provider's work (the owners' review, 12 Nov
2026): YouTube, Instagram, TikTok or Facebook, several per profile.

Read, never fetched: nothing here makes a request. Only the platform and a
key of a pinned shape are kept, and the link and the embed address are
rebuilt from them on the platform's own host -- the same rule as
``youtube_video_id`` and ``app.core.instagram``: nothing a visitor's browser
is handed was typed by an owner.

A TikTok short link (``vm.tiktok.com/...``) names no video until it is
followed, so it is refused with a request for the full link rather than
fetched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, quote, urlsplit

from app.core.errors import AppError, ValidationError
from app.core.instagram import parse_instagram_post
from app.core.urls import youtube_video_id

YOUTUBE = "YOUTUBE"
INSTAGRAM = "INSTAGRAM"
TIKTOK = "TIKTOK"
FACEBOOK = "FACEBOOK"
PLATFORMS = (YOUTUBE, INSTAGRAM, TIKTOK, FACEBOOK)

_TIKTOK_HOSTS = frozenset({"tiktok.com", "www.tiktok.com", "m.tiktok.com"})
_TIKTOK_PATH = re.compile(r"^/@[A-Za-z0-9._]{1,40}/video/(?P<id>\d{8,25})/?$")
_FACEBOOK_HOSTS = frozenset(
    {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"}
)
# /<page>/videos/<id>, /reel/<id>, /watch?v=<id>, /share/v/<code>, /share/r/<code>
_FACEBOOK_VIDEO = re.compile(r"^/[A-Za-z0-9.\-]{1,80}/videos/(?:[^/]+/)?(?P<id>\d{5,25})/?$")
_FACEBOOK_REEL = re.compile(r"^/reel/(?P<id>\d{5,25})/?$")
_FACEBOOK_SHARE = re.compile(r"^/share/(?P<kind>[vr])/(?P<code>[A-Za-z0-9]{5,40})/?$")
_DIGITS = re.compile(r"^\d{5,25}$")


@dataclass(frozen=True)
class WorkVideo:
    platform: str
    key: str

    @property
    def url(self) -> str:
        if self.platform == YOUTUBE:
            return f"https://www.youtube.com/watch?v={self.key}"
        if self.platform == INSTAGRAM:
            return f"https://www.instagram.com/{self.key}/"
        if self.platform == TIKTOK:
            return f"https://www.tiktok.com/video/{self.key}"
        return f"https://www.facebook.com/{self.key}"

    @property
    def embed_url(self) -> str:
        if self.platform == YOUTUBE:
            return f"https://www.youtube-nocookie.com/embed/{self.key}"
        if self.platform == INSTAGRAM:
            return f"https://www.instagram.com/{self.key}/embed/"
        if self.platform == TIKTOK:
            return f"https://www.tiktok.com/embed/v2/{self.key}"
        return (
            "https://www.facebook.com/plugins/video.php?show_text=false&href="
            + quote(self.url, safe="")
        )


def _refuse() -> ValidationError:
    return ValidationError("talent.video_link_invalid", code="invalid_video_link")


def parse_work_video(raw: str) -> WorkVideo:
    """The video a pasted link names, or a validation error."""
    text = raw.strip()
    if not text:
        raise _refuse()
    if "://" not in text:
        text = f"https://{text}"
    try:
        parts = urlsplit(text)
    except ValueError as error:
        raise _refuse() from error
    if parts.scheme not in ("http", "https") or parts.username or parts.password:
        raise _refuse()
    host = (parts.hostname or "").lower()

    if host == "youtu.be" or host.endswith(("youtube.com", "youtube-nocookie.com")):
        try:
            return WorkVideo(YOUTUBE, youtube_video_id(text))
        except AppError as error:
            raise _refuse() from error

    if host.endswith("instagram.com"):
        post = parse_instagram_post(text)
        if post is None:
            raise _refuse()
        return WorkVideo(INSTAGRAM, f"{post.kind}/{post.code}")

    if host == "vm.tiktok.com" or host == "vt.tiktok.com":
        raise ValidationError("talent.video_link_tiktok_short", code="tiktok_short_link")
    if host in _TIKTOK_HOSTS:
        match = _TIKTOK_PATH.match(parts.path)
        if match is None:
            raise _refuse()
        return WorkVideo(TIKTOK, match["id"])

    if host in _FACEBOOK_HOSTS or host == "fb.watch":
        if host == "fb.watch":
            raise ValidationError("talent.video_link_facebook_short", code="facebook_short_link")
        path = parts.path
        if path.rstrip("/") == "/watch":
            video = parse_qs(parts.query).get("v", [""])[0]
            if _DIGITS.match(video):
                return WorkVideo(FACEBOOK, f"watch/?v={video}")
            raise _refuse()
        match = _FACEBOOK_REEL.match(path)
        if match is not None:
            return WorkVideo(FACEBOOK, f"reel/{match['id']}")
        share = _FACEBOOK_SHARE.match(path)
        if share is not None:
            return WorkVideo(FACEBOOK, f"share/{share['kind']}/{share['code']}/")
        match = _FACEBOOK_VIDEO.match(path)
        if match is not None:
            return WorkVideo(FACEBOOK, f"watch/?v={match['id']}")
        raise _refuse()

    raise _refuse()
