"""Serving the built SPA from the API, including SEO head injection."""

from __future__ import annotations

from pathlib import Path

import pytest
import starlette.responses
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.i18n import translate
from app.main import create_app, static_media_type
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
            "bio": ar("talent.designer_bio"),
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
    assert f'property="og:description" content="{ar("talent.designer_bio")}"' in html
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


def test_share_tags_stay_arabic_for_an_english_speaking_crawler(
    spa_client: TestClient, approved_slug: str
) -> None:
    """WhatsApp, Facebook and X fetch link targets with `Accept-Language: en`.
    The request middleware honours that header for API responses, but a share
    preview on this Arabic-first directory must not flip to English because of
    it — the injected head is pinned to the site's own locale."""
    english = {"Accept-Language": "en-US,en;q=0.9"}

    expected_title = translate(
        "seo.business.title_with_location",
        "ar",
        name=ar("business.seo_name"),
        location=ar("location.tyre"),
        site=translate("app.name", "ar"),
    )
    business_html = spa_client.get(f"/business/{approved_slug}", headers=english).text
    assert f"<title>{expected_title}</title>" in business_html
    assert f'property="og:title" content="{expected_title}"' in business_html
    assert 'property="og:locale" content="ar_LB"' in business_html

    # The home/default route carries fully translated tags, so it is the real
    # regression surface: its title and description come from the catalog, not
    # from a listing's own Arabic content.
    home_html = spa_client.get("/", headers=english).text
    assert f"<title>{translate('seo.default.title', 'ar')}</title>" in home_html
    assert (
        f'property="og:description" content="{translate("seo.default.description", "ar")}"'
        in home_html
    )
    assert f'property="og:site_name" content="{translate("app.name", "ar")}"' in home_html


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


def test_standalone_page_is_reachable_without_its_extension(spa_client: TestClient) -> None:
    """The presentation is a plain file in ``public/``, and the link people
    forward is ``/presentation``. Both spellings must reach the same document
    rather than falling through to the SPA shell."""
    with_extension = spa_client.get("/presentation.html")
    without = spa_client.get("/presentation")

    assert with_extension.status_code == 200
    assert without.status_code == 200
    assert without.content == with_extension.content
    # The SPA shell would have this; the deck is its own document.
    assert '<div id="root">' not in without.text


def test_extensionless_paths_without_a_file_still_serve_the_spa(spa_client: TestClient) -> None:
    """The ``.html`` lookup is a fallback, not a redirect: a client-side route
    that happens to have no file behind it must keep reaching the app."""
    response = spa_client.get("/businesses")

    assert response.status_code == 200
    assert '<div id="root">' in response.text


def test_a_traversal_path_cannot_escape_the_build_directory(spa_client: TestClient) -> None:
    """Both lookups resolve the path and then check containment. A request
    that climbs out of ``dist`` gets the SPA shell, never a file from the
    image — the API's own source sits a few directories up from the build."""
    for path in ("/../backend/app/main.py", "/../../etc/passwd", "/..%2f..%2fetc%2fpasswd"):
        response = spa_client.get(path)
        assert response.status_code in {200, 404}, path
        assert "create_app" not in response.text, path
        assert "root:" not in response.text, path


# --- Content types for build artefacts -------------------------------------


def test_a_font_is_served_as_a_font_and_not_as_text(spa_client: TestClient) -> None:
    """A live bug, reproduced from the direction a browser sees it.

    Every response carries ``X-Content-Type-Options: nosniff``, so a font
    served as ``text/plain`` is not merely mislabelled -- the browser refuses
    it, and an Arabic-first site silently renders in a fallback system font.

    That is what production was doing: ``FileResponse`` falls back to
    ``mimetypes.guess_type``, ``python:3.11-slim`` ships no ``/etc/mime.types``
    and Python 3.11's own table has no woff2 entry, so the guess was None.
    It worked on a developer's machine for the one reason that makes this
    class of bug expensive -- the machine had the system file the container
    lacks.
    """
    fonts = sorted(DIST.glob("assets/*.woff2"))
    assert fonts, "the build output ships no woff2; this test has stopped testing anything"

    response = spa_client.get(f"/assets/{fonts[0].name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "font/woff2"


def test_a_font_is_still_a_font_on_a_machine_with_no_mime_database(
    spa_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The container's conditions, reproduced, because that is where it broke.

    Starlette computes ``guess_type(path)[0] or "text/plain"``. Remove the
    entry the host system supplies and the guess is None, which is how a font
    went out as text/plain in production while every test here passed. With
    the entry gone this must still answer ``font/woff2`` -- otherwise the fix
    only works on machines that never needed it.
    """
    fonts = sorted(DIST.glob("assets/*.woff2"))
    assert fonts, "the build output ships no woff2; this test has stopped testing anything"

    # Patched on ``starlette.responses``, not on ``mimetypes``: Starlette does
    # ``from mimetypes import guess_type``, so the name is bound at import and
    # patching the mimetypes module leaves it untouched. My first version of
    # this test did exactly that and passed with the fix reverted -- a guard
    # that proves nothing, which is worse than no guard.
    monkeypatch.setattr(
        starlette.responses, "guess_type", lambda *args, **kwargs: (None, None)
    )

    response = spa_client.get(f"/assets/{fonts[0].name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "font/woff2"


def test_the_media_type_table_does_not_depend_on_the_host_system() -> None:
    """The reason the table is explicit rather than a distro package.

    ``mimetypes`` would answer this correctly on a machine with
    ``/etc/mime.types`` and incorrectly in the container, which is exactly the
    situation that let the bug ship. Asserting our own mapping keeps the test
    meaningful wherever it runs.
    """
    assert static_media_type(Path("x.woff2")) == "font/woff2"
    assert static_media_type(Path("x.WOFF2")) == "font/woff2"
    assert static_media_type(Path("x.woff")) == "font/woff"
    # Left to Starlette, which is reliable for these.
    assert static_media_type(Path("x.js")) is None
    assert static_media_type(Path("x.css")) is None
