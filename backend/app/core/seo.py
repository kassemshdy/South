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
from decimal import Decimal

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
    # Open Graph tags are identified by `property`; Twitter's card tags by
    # `name` (per Twitter's own spec) — mixing the two means Twitter/X's own
    # crawler never finds them.
    if key.startswith("og:"):
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


def talent_tags(
    *,
    display_name: str,
    skill_name: str | None,
    bio: str | None,
    location_name: str | None,
    image_url: str | None,
    canonical_url: str,
) -> SeoTags:
    site = translate("app.name")
    title = (
        translate("seo.talent.title_with_skill", name=display_name, skill=skill_name, site=site)
        if skill_name
        else translate("seo.talent.title", name=display_name, site=site)
    )
    if location_name:
        fallback = translate("seo.talent.description", name=display_name, location=location_name)
    else:
        fallback = translate("seo.talent.description_no_location", name=display_name)

    description = bio or fallback
    return SeoTags(
        title=title,
        description=description[:300],
        canonical_url=canonical_url,
        image_url=image_url,
        og_type="profile",
    )


def default_tags(*, canonical_url: str, image_url: str) -> SeoTags:
    """The site-wide fallback used for every route with no listing of its own
    (home, search, admin, dashboard) so a shared link always carries an
    absolute-URL image and canonical, not just the static, relative ones
    baked into the build's index.html."""
    return SeoTags(
        title=translate("seo.default.title"),
        description=translate("seo.default.description"),
        canonical_url=canonical_url,
        image_url=image_url,
    )


def format_price(price: Decimal | None, currency: str) -> str | None:
    """A price the way the site prints it (``formatPrice`` in the frontend):
    ``$12.50``, or ``150,000 LBP`` with no decimals for pounds."""
    if price is None:
        return None
    if currency == "LBP":
        return f"{price:,.0f} LBP"
    return f"${price:,.2f}"


def product_tags(
    *,
    title: str,
    price: Decimal | None,
    currency: str,
    business_name: str,
    image_url: str | None,
    canonical_url: str,
) -> SeoTags:
    """A product link's preview: its name and its price, nothing composed.

    The product is the most shared thing on the site -- a photo, a name and a
    price in a WhatsApp chat -- and a link to one used to preview as the
    homepage. The price is the description; with none set, the shop's name
    stands in, so the preview still says whose it is.
    """
    return SeoTags(
        title=translate("seo.page.title", name=title, site=translate("app.name")),
        description=format_price(price, currency) or business_name,
        canonical_url=canonical_url,
        image_url=image_url,
        og_type="product",
    )


#: The directory pages' own titles, served in the HTML itself: a link
#: preview reads the document the server sends and never runs the script
#: that would set them. The wording is the pages' own (their catalog keys),
#: copied rather than rewritten.
_PAGES: dict[str, tuple[str, str]] = {
    "products": ("seo.page.products.title", "seo.page.products.description"),
    "businesses": ("seo.page.businesses.title", "seo.page.businesses.description"),
    "talent": ("seo.page.talent.title", "seo.page.talent.description"),
}
_NAMED_PAGES: dict[str, tuple[str, str]] = {
    "products/local": ("seo.page.products_local.name", "seo.page.products.description"),
    "products/imported": ("seo.page.products_imported.name", "seo.page.products.description"),
    "offer": ("seo.page.offer.name", "seo.page.offer.description"),
    "browse": ("seo.page.browse.name", "seo.page.browse.description"),
}


def page_tags(path: str, *, canonical_url: str, image_url: str | None) -> SeoTags | None:
    """Tags for a directory or landing page, or None for any other path."""
    path = path.strip("/")
    if path in _PAGES:
        title_key, description_key = _PAGES[path]
        title = translate(title_key)
    elif path in _NAMED_PAGES:
        name_key, description_key = _NAMED_PAGES[path]
        title = translate("seo.page.title", name=translate(name_key), site=translate("app.name"))
    else:
        return None
    return SeoTags(
        title=title,
        description=translate(description_key),
        canonical_url=canonical_url,
        image_url=image_url,
    )
