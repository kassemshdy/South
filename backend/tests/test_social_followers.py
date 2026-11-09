"""Instagram/Facebook follower counts through Apify (the owners' request,
9 Nov 2026). Apify itself is stood in for; no test leaves the machine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessSocialLink
from app.models.enums import SocialPlatform
from app.models.user import User
from app.services import social_followers
from tests.conftest import admin_headers
from tests.test_views import approved_business, owner_headers  # noqa: F401


class FakeApify(social_followers.ApifyFollowers):
    def __init__(self, answers: dict[str, list[dict[str, Any]]]) -> None:
        super().__init__("token", httpx.Client())
        self.answers = answers
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def _run(self, actor: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        self.asked.append((actor, payload))
        return self.answers.get(actor, [])


def test_usernames_are_read_from_the_links_owners_typed() -> None:
    assert social_followers.instagram_username("https://www.instagram.com/Bondoq_wa_Lawz/?hl=en") == (
        "bondoq_wa_lawz"
    )
    assert social_followers.instagram_username("instagram.com/p/abc123") is None
    assert social_followers.facebook_key("https://m.facebook.com/Shop.Page/?ref=x") == (
        "facebook.com/shop.page"
    )


def test_counts_are_stored_and_staff_sort_by_them(
    client: TestClient,
    db: Session,
    admin: User,
    approved_business: Business,  # noqa: F811
) -> None:
    db.add_all(
        [
            BusinessSocialLink(
                business_id=approved_business.id,
                platform=SocialPlatform.INSTAGRAM,
                url="https://instagram.com/shop_one",
            ),
            BusinessSocialLink(
                business_id=approved_business.id,
                platform=SocialPlatform.FACEBOOK,
                url="https://www.facebook.com/ShopOne",
            ),
        ]
    )
    db.commit()
    apify = FakeApify(
        {
            social_followers.INSTAGRAM_ACTOR: [{"username": "shop_one", "followersCount": 1520}],
            social_followers.FACEBOOK_ACTOR: [
                {"facebookUrl": "https://facebook.com/shopone/", "followers": 870}
            ],
        }
    )
    moment = datetime(2026, 11, 9, 20, 0, tzinfo=UTC)
    assert social_followers.refresh(db, apify, moment) == 1
    assert apify.asked[0] == (social_followers.INSTAGRAM_ACTOR, {"usernames": ["shop_one"]})

    listed = client.get(
        "/api/admin/businesses?sort=instagram", headers=admin_headers(client)
    ).json()["items"]
    shop = next(item for item in listed if item["id"] == str(approved_business.id))
    assert (shop["instagram_followers"], shop["facebook_followers"]) == (1520, 870)
    assert listed[0]["id"] == str(approved_business.id), "most followed first"


def test_refreshing_by_hand_needs_the_token_and_the_manager(
    client: TestClient,
    admin: User,
    owner_headers: dict[str, str],  # noqa: F811
) -> None:
    path = "/api/admin/businesses/followers/refresh"
    assert client.post(path, headers=admin_headers(client)).status_code == 503
    assert client.post(path, headers=owner_headers).status_code == 403
