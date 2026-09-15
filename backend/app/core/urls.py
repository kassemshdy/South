"""Validation for user-supplied URLs.

Owners paste links from their phones, and a directory that renders whatever it
is given is a stored-XSS and open-redirect vector. Every URL is parsed, forced
to http(s), and — for known platforms — checked against that platform's own
hosts, so an "Instagram" link cannot point somewhere else entirely.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse, urlunparse

from app.core.errors import ValidationError
from app.core.i18n import LazyText
from app.models.enums import SocialPlatform

_ALLOWED_SCHEMES = {"http", "https"}

PLATFORM_HOSTS: dict[SocialPlatform, frozenset[str]] = {
    SocialPlatform.INSTAGRAM: frozenset({"instagram.com", "instagr.am"}),
    SocialPlatform.FACEBOOK: frozenset({"facebook.com", "fb.com", "fb.me", "m.facebook.com"}),
    SocialPlatform.TIKTOK: frozenset({"tiktok.com", "vm.tiktok.com"}),
    SocialPlatform.YOUTUBE: frozenset({"youtube.com", "youtu.be", "m.youtube.com"}),
    SocialPlatform.WHATSAPP: frozenset(
        {"wa.me", "whatsapp.com", "api.whatsapp.com", "chat.whatsapp.com"}
    ),
    SocialPlatform.WEBSITE: frozenset(),  # any host is legitimate here
}

PLATFORM_LABEL_KEYS: dict[SocialPlatform, str] = {
    SocialPlatform.INSTAGRAM: "platform.instagram",
    SocialPlatform.FACEBOOK: "platform.facebook",
    SocialPlatform.TIKTOK: "platform.tiktok",
    SocialPlatform.YOUTUBE: "platform.youtube",
    SocialPlatform.WHATSAPP: "platform.whatsapp",
    SocialPlatform.WEBSITE: "platform.website",
}


def platform_label(platform: SocialPlatform) -> LazyText:
    """The platform's name, translated when the response is rendered."""
    return LazyText(PLATFORM_LABEL_KEYS.get(platform, "url.field.generic"))


def _base_host(host: str) -> str:
    host = host.lower().removeprefix("www.")
    return host


def normalize_url(raw: str, *, field: LazyText | None = None) -> str:
    """Return a safe absolute URL, adding https:// when the scheme is missing."""
    field = field or LazyText("url.field.generic")
    value = (raw or "").strip()
    if not value:
        raise ValidationError("url.required", code="invalid_url", params={"field": field})

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValidationError(
            "url.invalid_scheme", code="invalid_url_scheme", params={"field": field}
        )
    if not parsed.netloc or "." not in parsed.netloc:
        raise ValidationError("url.invalid", code="invalid_url", params={"field": field})

    # Drop any credentials embedded in the URL.
    netloc = parsed.netloc.split("@")[-1]
    return urlunparse(
        (parsed.scheme.lower(), netloc, parsed.path, parsed.params, parsed.query, "")
    )


def normalize_social_url(platform: SocialPlatform, raw: str) -> str:
    label = platform_label(platform)
    url = normalize_url(raw, field=LazyText("url.field.social", {"platform": label}))

    allowed = PLATFORM_HOSTS.get(platform, frozenset())
    if not allowed:
        return url

    host = _base_host(urlparse(url).netloc.split(":")[0])
    if host not in allowed and not any(host.endswith(f".{item}") for item in allowed):
        raise ValidationError(
            "url.invalid_social_host",
            code="invalid_social_host",
            params={"platform": label},
        )
    return url


# A YouTube id is exactly eleven characters of an unreserved alphabet. Pinning
# the shape is what lets the id be interpolated into an embed URL later
# without re-validating it there.
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

# The path prefixes YouTube itself hands out. `watch` is the odd one: its id
# lives in the query string rather than the path.
_YOUTUBE_PATH_PREFIXES = ("embed", "live", "shorts", "v")

_YOUTUBE_HOSTS = PLATFORM_HOSTS[SocialPlatform.YOUTUBE] | frozenset(
    {"youtube-nocookie.com", "www.youtube-nocookie.com"}
)


def youtube_video_id(raw: str) -> str:
    """Extract the video id from any shape of YouTube link an owner may paste.

    Returns the id, not the URL, and that is the point: the page composes
    ``youtube-nocookie.com/embed/<id>`` from it, so nothing a visitor's browser
    is handed was ever typed by an owner. A column holding eleven characters of
    ``[A-Za-z0-9_-]`` cannot carry a ``javascript:`` scheme, an open redirect
    or a tracking parameter, which a column holding "whatever they pasted"
    can — see this module's docstring.

    Accepts watch, youtu.be, shorts, live, embed and /v/ links, with or
    without a scheme, extra query parameters or a timestamp.
    """
    field = LazyText("url.field.video")
    url = normalize_url(raw, field=field)
    parsed = urlparse(url)

    host = _base_host(parsed.netloc.split(":")[0])
    if host not in {_base_host(item) for item in _YOUTUBE_HOSTS}:
        raise ValidationError("url.invalid_youtube", code="invalid_youtube_url")

    segments = [segment for segment in parsed.path.split("/") if segment]
    candidate: str | None = None

    if host in {"youtu.be"}:
        # youtu.be/<id> — the whole path is the id.
        candidate = segments[0] if segments else None
    elif segments and segments[0] == "watch":
        candidate = next(iter(parse_qs(parsed.query).get("v", [])), None)
    elif len(segments) >= 2 and segments[0] in _YOUTUBE_PATH_PREFIXES:
        candidate = segments[1]

    if not candidate or not _YOUTUBE_ID.match(candidate):
        raise ValidationError("url.invalid_youtube", code="invalid_youtube_url")
    return candidate


def normalize_maps_url(raw: str) -> str:
    return normalize_url(raw, field=LazyText("url.field.maps"))
