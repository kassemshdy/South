"""Articles: admin-authored, published to one of two sections.

Nothing here is owner- or visitor-submitted, so the boundary that matters is
simpler than a business's: a draft must be invisible on every public route
(list and detail alike), and only an administrator may write, publish or
delete one.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

OWNER_PHONE = "03970001"


def _create(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {
        "section": "BLOG",
        "title": ar("article.first_title"),
        "body": ar("article.first_body"),
        **overrides,
    }
    response = client.post("/api/admin/articles", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_draft_is_invisible_on_every_public_route(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    article = _create(client, headers)

    listing = client.get("/api/articles", params={"section": "BLOG"})
    assert listing.status_code == 200
    assert article["id"] not in [a["id"] for a in listing.json()]

    detail = client.get(f"/api/articles/{article['slug']}")
    assert detail.status_code == 404


def test_publishing_makes_it_visible_in_its_own_section_only(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    article = _create(client, headers, section="NEWS")

    published = client.post(f"/api/admin/articles/{article['id']}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert published.json()["published_at"] is not None

    news = client.get("/api/articles", params={"section": "NEWS"})
    assert article["id"] in [a["id"] for a in news.json()]

    blog = client.get("/api/articles", params={"section": "BLOG"})
    assert article["id"] not in [a["id"] for a in blog.json()]

    detail = client.get(f"/api/articles/{article['slug']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == ar("article.first_title")
    # The public payload carries no moderation state.
    assert "is_published" not in detail.json()


def test_republishing_does_not_move_the_published_date(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    article = _create(client, headers)
    first = client.post(f"/api/admin/articles/{article['id']}/publish", headers=headers)
    first_published_at = first.json()["published_at"]

    client.post(f"/api/admin/articles/{article['id']}/unpublish", headers=headers)
    second = client.post(f"/api/admin/articles/{article['id']}/publish", headers=headers)
    assert second.json()["published_at"] == first_published_at


def test_unpublishing_removes_it_from_public_view(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    article = _create(client, headers)
    client.post(f"/api/admin/articles/{article['id']}/publish", headers=headers)
    client.post(f"/api/admin/articles/{article['id']}/unpublish", headers=headers)

    detail = client.get(f"/api/articles/{article['slug']}")
    assert detail.status_code == 404


def test_duplicate_slug_is_rejected(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    _create(client, headers, slug="a-shared-slug")

    response = client.post(
        "/api/admin/articles",
        json={
            "section": "BLOG",
            "title": ar("article.second_title"),
            "body": ar("article.first_body"),
            "slug": "a-shared-slug",
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_an_owner_cannot_reach_the_admin_article_api(client: TestClient) -> None:
    headers = sign_in(client, OWNER_PHONE)
    response = client.post(
        "/api/admin/articles",
        json={
            "section": "BLOG",
            "title": ar("article.first_title"),
            "body": ar("article.first_body"),
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_an_anonymous_visitor_cannot_reach_the_admin_article_api(client: TestClient) -> None:
    response = client.get("/api/admin/articles")
    assert response.status_code == 401


def test_deleting_an_article_removes_it_everywhere(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    article = _create(client, headers)
    client.post(f"/api/admin/articles/{article['id']}/publish", headers=headers)

    response = client.delete(f"/api/admin/articles/{article['id']}", headers=headers)
    assert response.status_code == 200

    detail = client.get(f"/api/articles/{article['slug']}")
    assert detail.status_code == 404

    admin_list = client.get("/api/admin/articles", headers=headers)
    assert article["id"] not in [a["id"] for a in admin_list.json()]


def test_admin_listing_includes_drafts_and_can_filter_by_section(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    blog = _create(client, headers, section="BLOG")
    news = _create(client, headers, section="NEWS", title=ar("article.second_title"))

    all_articles = client.get("/api/admin/articles", headers=headers)
    ids = [a["id"] for a in all_articles.json()]
    assert blog["id"] in ids
    assert news["id"] in ids

    blog_only = client.get("/api/admin/articles", params={"section": "BLOG"}, headers=headers)
    blog_ids = [a["id"] for a in blog_only.json()]
    assert blog["id"] in blog_ids
    assert news["id"] not in blog_ids


def test_an_article_names_a_category_and_place_and_its_page_carries_them(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    """The article page ends with the products and shops of what the article
    is about, so the public article carries the category and place."""
    headers = admin_headers(client)
    article = _create(client, headers, category_id=str(category.id), location_id=str(location.id))
    assert article["category"]["slug"] == category.slug
    assert article["location"]["slug"] == location.slug
    client.post(f"/api/admin/articles/{article['id']}/publish", headers=headers)

    public = client.get(f"/api/articles/{article['slug']}").json()
    assert public["category"]["slug"] == category.slug
    assert public["location"]["slug"] == location.slug


def test_an_article_link_is_cleared_with_null_and_kept_when_left_out(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    headers = admin_headers(client)
    article = _create(client, headers, category_id=str(category.id), location_id=str(location.id))
    response = client.put(
        f"/api/admin/articles/{article['id']}", json={"category_id": None}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["category"] is None
    assert response.json()["location"]["slug"] == location.slug


def test_an_unknown_category_or_place_is_refused(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    for field in ("category_id", "location_id"):
        payload = {
            "section": "BLOG",
            "title": ar("article.first_title"),
            "body": ar("article.first_body"),
            field: str(uuid.uuid4()),
        }
        response = client.post("/api/admin/articles", json=payload, headers=headers)
        assert response.status_code == 404, response.text


def test_deleting_the_category_keeps_the_article(
    client: TestClient, admin: User, category: Category, db: Session
) -> None:
    headers = admin_headers(client)
    article = _create(client, headers, category_id=str(category.id))
    db.delete(category)
    db.commit()
    response = client.get("/api/admin/articles", headers=headers)
    (kept,) = [a for a in response.json() if a["id"] == article["id"]]
    assert kept["category"] is None
