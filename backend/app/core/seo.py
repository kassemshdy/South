"""Server-side SEO tag injection for the built SPA.

A Vite single-page app ships one index.html, so a crawler or a WhatsApp link
preview fetching /business/<slug> would otherwise see the generic default tags.
When the API serves the built frontend, this rewrites the head for business
profile URLs before the HTML goes out, which is what makes shared links show the
right name, description and image.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from app.core.i18n import translate

_TITLE_RE = re.compile(r"<title>.*?</title>", re.IGNORECASE | re.DOTALL)
_META_RE_TEMPLATE = r'<meta\s+(?:name|property)=["\']{key}["\'][^>]*>'


@dataclass(frozen=True)
class SeoTags:
    title: str
    description: str
    canonical_url: str
    image_url: str | None = None
    og_type: str = "website"


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _replace_meta(document: str, key: str, content: str) -> str:
    tag_pattern = re.compile(_META_RE_TEMPLATE.format(key=re.escape(key)), re.IGNORECASE)
    if key.startswith(("og:", "twitter:")):
        replacement = f'<meta property="{key}" content="{_escape(content)}">'
    else:
        replacement = f'<meta name="{key}" content="{_escape(content)}">'

    if tag_pattern.search(document):
        return tag_pattern.sub(replacement, document, count=1)
    return document.replace("</head>", f"  {replacement}\n</head>", 1)


def inject(document: str, tags: SeoTags) -> str:
    """Return ``document`` with its head rewritten for ``tags``."""
    result = _TITLE_RE.sub(f"<title>{_escape(tags.title)}</title>", document, count=1)

    for key, value in (
        ("description", tags.description),
        ("og:title", tags.title),
        ("og:description", tags.description),
        ("og:url", tags.canonical_url),
        ("og:type", tags.og_type),
        ("og:site_name", translate("app.name")),
        ("og:locale", "ar_LB"),
        ("twitter:card", "summary_large_image" if tags.image_url else "summary"),
        ("twitter:title", tags.title),
        ("twitter:description", tags.description),
    ):
        result = _replace_meta(result, key, value)

    if tags.image_url:
        result = _replace_meta(result, "og:image", tags.image_url)
        result = _replace_meta(result, "twitter:image", tags.image_url)

    canonical = f'<link rel="canonical" href="{_escape(tags.canonical_url)}">'
    canonical_pattern = re.compile(r'<link\s+rel=["\']canonical["\'][^>]*>', re.IGNORECASE)
    if canonical_pattern.search(result):
        result = canonical_pattern.sub(canonical, result, count=1)
    else:
        result = result.replace("</head>", f"  {canonical}\n</head>", 1)

    return result


def business_tags(
    *,
    name: str,
    short_description: str | None,
    category_name: str | None,
    location_name: str | None,
    image_url: str | None,
    canonical_url: str,
) -> SeoTags:
    site = translate("app.name")
    if location_name:
        title = translate(
            "seo.business.title_with_location", name=name, location=location_name, site=site
        )
        fallback = translate("seo.business.description", name=name, location=location_name)
    else:
        title = translate("seo.business.title", name=name, site=site)
        fallback = translate("seo.business.description_no_location", name=name)

    description = short_description or fallback
    return SeoTags(
        title=title,
        description=description[:300],
        canonical_url=canonical_url,
        image_url=image_url,
        og_type="business.business",
    )
