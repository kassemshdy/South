"""Serving the built SPA from the API, including SEO head injection."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.i18n import translate
from app.main import create_app
from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

pytestmark = pytest.mark.skipif(
    not (DIST / "index.html").exists(),
    reason="frontend build not present; run `npm run build` in frontend/",
)


@pytest.fixture
def spa_client() -> TestClient:
    settings = Settings(
        frontend_dist_dir=str(DIST),
        public_base_url="https://example.test",
        database_url=get_settings().database_url,
    )
    return TestClient(create_app(settings))


@pytest.fixture
def approved_slug(
    client: TestClient, db: Session, category: Category, location: Location
) -> str:
    headers = sign_in(client, "03910001")
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.seo_name"),
            "short_description": ar("business.seo_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    business = db.get(Business, created["id"])
    assert business is not None
    business.status = BusinessStatus.APPROVED
    db.commit()
    return created["slug"]


def test_business_url_gets_server_rendered_seo_tags(
    spa_client: TestClient, approved_slug: str
) -> None:
    """Crawlers and link previews do not run JavaScript, so the tags must be
    in the HTML the server sends."""
    html = spa_client.get(f"/business/{approved_slug}").text

    expected_title = translate(
        "seo.business.title_with_location",
        "ar",
        name=ar("business.seo_name"),
        location=ar("location.tyre"),
        site=translate("app.name", "ar"),
    )

    assert f"<title>{expected_title}</title>" in html
    assert f'property="og:title" content="{expected_title}"' in html
    assert f'property="og:description" content="{ar("business.seo_short")}"' in html
    assert 'rel="canonical"' in html
    assert 'property="og:image" content="https://example.test/og-image.png"' in html


@pytest.fixture
def approved_talent_slug(
    client: TestClient, db: Session, admin: User, location: Location
) -> str:
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.commit()

    headers = sign_in(client, "03950101")
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "headline": ar("talent.designer_headline"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    ).json()

    profile = db.get(TalentProfile, created["id"])
    assert profile is not None
    profile.status = BusinessStatus.PENDING_REVIEW
    db.commit()

    approved = client.post(
        f"/api/admin/talent/{created['id']}/approve", headers=admin_headers(client)
    )
    assert approved.status_code == 200, approved.text
    return created["slug"]


def test_talent_url_gets_server_rendered_seo_tags(
    spa_client: TestClient, approved_talent_slug: str
) -> None:
    html = spa_client.get(f"/talent/{approved_talent_slug}").text

    expected_title = translate(
        "seo.talent.title_with_skill",
        "ar",
        name=ar("talent.designer"),
        skill=ar("skill.design"),
        site=translate("app.name", "ar"),
    )

    assert f"<title>{expected_title}</title>" in html
    assert f'property="og:title" content="{expected_title}"' in html
    assert f'property="og:description" content="{ar("talent.designer_headline")}"' in html
    # No photo was uploaded, so the site-wide share image is the fallback —
    # never a relative URL a crawler can't resolve on its own.
    assert 'property="og:image" content="https://example.test/og-image.png"' in html


def test_unknown_and_client_routes_serve_the_spa(spa_client: TestClient) -> None:
    for path in ("/", "/businesses", "/dashboard", "/business/does-not-exist"):
        response = spa_client.get(path)
        assert response.status_code == 200, path
        assert "<div id=\"root\">" in response.text, path


def test_generic_routes_get_the_default_absolute_share_image(spa_client: TestClient) -> None:
    """Every route without a listing of its own — home, a 404'd slug, the
    dashboard — still gets an absolute og:image instead of the relative one
    baked into the built index.html, so a shared link always resolves."""
    for path in ("/", "/products", "/business/does-not-exist"):
        html = spa_client.get(path).text
        assert 'property="og:image" content="https://example.test/og-image.png"' in html
        assert 'name="twitter:card" content="summary_large_image"' in html
        assert 'rel="canonical"' in html


def test_rendered_index_is_never_edge_cached(spa_client: TestClient) -> None:
    """Regression: an edge/CDN in front of the app once served a stale
    snapshot of "/" across multiple deploys, since nothing told it this
    document is rebuilt per-request. An explicit no-store is the only
    reliable way to stop a cache from substituting its own default."""
    for path in ("/", "/business/does-not-exist"):
        response = spa_client.get(path)
        assert response.headers["cache-control"] == "no-store, must-revalidate"


def test_static_files_are_served_with_their_real_content(spa_client: TestClient) -> None:
    """Regression: the SPA fallback used to return empty bodies for non-HTML files."""
    response = spa_client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.content.startswith(b"<svg")
    assert "svg" in response.headers["content-type"]
