"""Sitemap and robots.txt.

Only what a visitor may already see is ever listed: draft, pending, rejected
and suspended listings must not be discoverable, nor an unavailable product,
and the sitemap is the easiest place to leak one by accident. Every loop below
draws its rows from the same repository helper the public endpoints use, so
there is no second definition of "public" here to drift from the first.
"""

from __future__ import annotations

from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Response

from app.api.v1 import jobs
from app.core.dependencies import AppSettings, DbSession
from app.repositories.business import BusinessRepository
from app.repositories.item import ItemRepository
from app.repositories.talent import TalentRepository

router = APIRouter(include_in_schema=False)

IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"


def _absolute_image(base: str, image: str | None) -> str | None:
    """A stored picture as an absolute, percent-encoded URL, or None.

    Stored paths are site-relative (``/media/...``); an external URL is kept
    as it is. Only http(s) is ever listed."""
    if not image:
        return None
    if image.startswith("/"):
        return f"{base}{quote(image, safe='/')}"
    return image if image.startswith(("https://", "http://")) else None


# HEAD as well as GET: some sitemap checkers ask for the headers first, and a
# 405 there reads as "could not be read".
@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
def sitemap(db: DbSession, settings: AppSettings) -> Response:
    base = settings.public_base_url.rstrip("/")
    # Google's image extension: each listing names its own picture, so
    # products and shops can be found in Google Images (the owners asked for
    # it after comparing with aljazeera.net's sitemaps, 29 Oct 2026).
    urlset = Element(
        "urlset",
        {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9", "xmlns:image": IMAGE_NS},
    )

    def add(
        path: str,
        *,
        changefreq: str,
        priority: str,
        lastmod: object | None = None,
        image: str | None = None,
    ) -> None:
        url = SubElement(urlset, "url")
        # Percent-encoded: the sitemap protocol wants ASCII URLs, and a shop
        # whose slug is Arabic would otherwise be listed with raw letters.
        SubElement(url, "loc").text = f"{base}{quote(path, safe='/?=&')}"
        if lastmod is not None and hasattr(lastmod, "date"):
            SubElement(url, "lastmod").text = lastmod.date().isoformat()
        SubElement(url, "changefreq").text = changefreq
        SubElement(url, "priority").text = priority
        picture = _absolute_image(base, image)
        if picture:
            SubElement(SubElement(url, "image:image"), "image:loc").text = picture

    add("/", changefreq="daily", priority="1.0")

    # No `/businesses` or its category pages: the site no longer links the
    # business directory (the CEO asked for it to speak only of goods and
    # products and of services and skills), and a sitemap advertising a page
    # the site itself hides would send search traffic somewhere a visitor
    # cannot navigate from. Each shop's own page stays listed below.

    for slug, updated_at, image in BusinessRepository(db).approved_slugs():
        add(
            f"/business/{slug}",
            changefreq="weekly",
            priority="0.8",
            lastmod=updated_at,
            image=image,
        )

    # Products were missing entirely: they have public pages and a directory,
    # and a product is the most shareable thing here — a photo, a name and a
    # price — so it is the last thing that should have been invisible to a
    # crawler.
    add("/products", changefreq="daily", priority="0.9")
    # Goods made in the South and imported goods, each its own page.
    add("/products/local", changefreq="daily", priority="0.8")
    add("/products/imported", changefreq="daily", priority="0.8")

    for slug, updated_at, image in ItemRepository(db).public_slugs():
        add(
            f"/product/{slug}",
            changefreq="weekly",
            priority="0.7",
            lastmod=updated_at,
            image=image,
        )

    # Services and job applications, the two halves of what used to be one
    # talent directory. `/talent` itself now forwards to services, so it is
    # not listed; the profiles keep their `/talent/<slug>` address.
    add("/services", changefreq="daily", priority="0.9")
    add("/jobs", changefreq="daily", priority="0.8")

    # No `/services?skill=...` entries: those pages declare `/services` as
    # their canonical, and a sitemap listing URLs whose canonical points
    # elsewhere is what Search Console reports as "Alternate page with proper
    # canonical tag" -- every entry flagged rather than indexed. A sitemap
    # lists canonical URLs only.

    # Job openings the platform posts (29 Oct 2026): only open ones, through
    # the same rule the public routes use.
    add("/vacancies", changefreq="daily", priority="0.8")
    for slug, updated_at in jobs.open_slugs(db):
        add(f"/vacancies/{slug}", changefreq="weekly", priority="0.7", lastmod=updated_at)

    for slug, updated_at, image in TalentRepository(db).approved_slugs():
        add(
            f"/talent/{slug}",
            changefreq="weekly",
            priority="0.8",
            lastmod=updated_at,
            image=image,
        )

    return Response(
        content=tostring(urlset, encoding="utf-8", xml_declaration=True),
        media_type="application/xml",
    )


@router.api_route("/robots.txt", methods=["GET", "HEAD"])
def robots(settings: AppSettings) -> Response:
    base = settings.public_base_url.rstrip("/")
    # Owner and admin areas hold private data and have no search value.
    #
    # The cart and the saved list are neither: they are one visitor's own
    # browser state, so they are identical for nobody else and a search
    # result leading to either would be empty for whoever clicked it.
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /dashboard\n"
        "Disallow: /admin\n"
        "Disallow: /login\n"
        "Disallow: /cart\n"
        "Disallow: /favourites\n"
        # The pages are rendered in the browser from the public API, so a
        # search engine that may not fetch it sees every page empty -- which
        # is how Google came to index almost nothing (29 Oct 2026). Only the
        # private API stays closed; crawler fetches are not counted as views
        # (app.services.analytics.is_crawler).
        "Disallow: /api/admin\n"
        "Disallow: /api/my\n"
        "Disallow: /api/me\n"
        "Disallow: /api/auth\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )
    return Response(content=body, media_type="text/plain")
