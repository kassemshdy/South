"""Sitemap and robots.txt.

Only what a visitor may already see is ever listed: draft, pending, rejected
and suspended listings must not be discoverable, nor an unavailable product,
and the sitemap is the easiest place to leak one by accident. Every loop below
draws its rows from the same repository helper the public endpoints use, so
there is no second definition of "public" here to drift from the first.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Response

from app.core.dependencies import AppSettings, DbSession
from app.repositories.business import BusinessRepository
from app.repositories.item import ItemRepository
from app.repositories.talent import TalentRepository, TalentSkillRepository
from app.repositories.taxonomy import CategoryRepository

router = APIRouter(include_in_schema=False)


@router.get("/sitemap.xml")
def sitemap(db: DbSession, settings: AppSettings) -> Response:
    base = settings.public_base_url.rstrip("/")
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    def add(path: str, *, changefreq: str, priority: str, lastmod: object | None = None) -> None:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{base}{path}"
        if lastmod is not None and hasattr(lastmod, "date"):
            SubElement(url, "lastmod").text = lastmod.date().isoformat()
        SubElement(url, "changefreq").text = changefreq
        SubElement(url, "priority").text = priority

    add("/", changefreq="daily", priority="1.0")
    add("/businesses", changefreq="daily", priority="0.9")

    for category in CategoryRepository(db).list_all():
        add(f"/businesses?category={category.slug}", changefreq="weekly", priority="0.7")

    for slug, updated_at in BusinessRepository(db).approved_slugs():
        add(f"/business/{slug}", changefreq="weekly", priority="0.8", lastmod=updated_at)

    # Products were missing entirely: they have public pages and a directory,
    # and a product is the most shareable thing here — a photo, a name and a
    # price — so it is the last thing that should have been invisible to a
    # crawler.
    add("/products", changefreq="daily", priority="0.9")

    for slug, updated_at in ItemRepository(db).public_slugs():
        add(f"/product/{slug}", changefreq="weekly", priority="0.7", lastmod=updated_at)

    add("/talent", changefreq="daily", priority="0.9")

    for skill in TalentSkillRepository(db).list_all():
        add(f"/talent?skill={skill.slug}", changefreq="weekly", priority="0.7")

    for slug, updated_at in TalentRepository(db).approved_slugs():
        add(f"/talent/{slug}", changefreq="weekly", priority="0.8", lastmod=updated_at)

    return Response(
        content=tostring(urlset, encoding="utf-8", xml_declaration=True),
        media_type="application/xml",
    )


@router.get("/robots.txt")
def robots(settings: AppSettings) -> Response:
    base = settings.public_base_url.rstrip("/")
    # Owner and admin areas hold private data and have no search value.
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /dashboard\n"
        "Disallow: /admin\n"
        "Disallow: /login\n"
        "Disallow: /api/\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )
    return Response(content=body, media_type="text/plain")
