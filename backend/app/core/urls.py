"""Validation for user-supplied URLs.

Owners paste links from their phones, and a directory that renders whatever it
is given is a stored-XSS and open-redirect vector. Every URL is parsed, forced
to http(s), and — for known platforms — checked against that platform's own
hosts, so an "Instagram" link cannot point somewhere else entirely.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from app.core.errors import ValidationError
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

PLATFORM_LABELS_AR: dict[SocialPlatform, str] = {
    SocialPlatform.INSTAGRAM: "إنستغرام",
    SocialPlatform.FACEBOOK: "فيسبوك",
    SocialPlatform.TIKTOK: "تيك توك",
    SocialPlatform.YOUTUBE: "يوتيوب",
    SocialPlatform.WHATSAPP: "واتساب",
    SocialPlatform.WEBSITE: "الموقع الإلكتروني",
}


def _base_host(host: str) -> str:
    host = host.lower().removeprefix("www.")
    return host


def normalize_url(raw: str, *, field: str = "الرابط") -> str:
    """Return a safe absolute URL, adding https:// when the scheme is missing."""
    value = (raw or "").strip()
    if not value:
        raise ValidationError(f"{field} مطلوب.", code="invalid_url")

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValidationError(
            f"{field} يجب أن يبدأ بـ http أو https.", code="invalid_url_scheme"
        )
    if not parsed.netloc or "." not in parsed.netloc:
        raise ValidationError(f"{field} غير صالح.", code="invalid_url")

    # Drop any credentials embedded in the URL.
    netloc = parsed.netloc.split("@")[-1]
    return urlunparse(
        (parsed.scheme.lower(), netloc, parsed.path, parsed.params, parsed.query, "")
    )


def normalize_social_url(platform: SocialPlatform, raw: str) -> str:
    label = PLATFORM_LABELS_AR.get(platform, "الرابط")
    url = normalize_url(raw, field=f"رابط {label}")

    allowed = PLATFORM_HOSTS.get(platform, frozenset())
    if not allowed:
        return url

    host = _base_host(urlparse(url).netloc.split(":")[0])
    if host not in allowed and not any(host.endswith(f".{item}") for item in allowed):
        raise ValidationError(
            f"رابط {label} يجب أن يكون من موقع {label}.", code="invalid_social_host"
        )
    return url


def normalize_maps_url(raw: str) -> str:
    return normalize_url(raw, field="رابط الخريطة")
