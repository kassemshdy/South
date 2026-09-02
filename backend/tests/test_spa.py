"""Serving the built SPA from the API, including SEO head injection."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.main import create_app
from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in

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
            "name": "مطعم الاختبار",
            "short_description": "وصف قصير للاختبار",
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

    assert "<title>مطعم الاختبار في صور | دليل الجنوب</title>" in html
    assert 'property="og:title" content="مطعم الاختبار في صور | دليل الجنوب"' in html
    assert 'property="og:description" content="وصف قصير للاختبار"' in html
    assert 'rel="canonical"' in html


def test_unknown_and_client_routes_serve_the_spa(spa_client: TestClient) -> None:
    for path in ("/", "/businesses", "/dashboard", "/business/does-not-exist"):
        response = spa_client.get(path)
        assert response.status_code == 200, path
        assert "<div id=\"root\">" in response.text, path


def test_static_files_are_served_with_their_real_content(spa_client: TestClient) -> None:
    """Regression: the SPA fallback used to return empty bodies for non-HTML files."""
    response = spa_client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.content.startswith(b"<svg")
    assert "svg" in response.headers["content-type"]
