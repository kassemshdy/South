"""Instagram and Facebook follower counts for the shops, through Apify
(the owners' request, 9 Nov 2026: sort shops in the admin by followers).

Apify runs ready-made scrapers on its own servers and accounts; this
service only calls its API with ``APIFY_TOKEN`` and stores the numbers.
Inert without the token. Once a day the API looks for shops with an
Instagram or Facebook link, asks Apify for their pages in batches, and
writes ``instagram_followers`` / ``facebook_followers`` with the time of
the check. A page Apify cannot read (a private account, a deleted page)
keeps its last number; nothing here is shown to visitors.

The token travels in an ``Authorization`` header, never in a URL.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.business import Business, BusinessSocialLink
from app.models.enums import BusinessStatus, SocialPlatform

logger = logging.getLogger(__name__)

API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
INSTAGRAM_ACTOR = "apify~instagram-profile-scraper"
FACEBOOK_ACTOR = "apify~facebook-pages-scraper"
#: Apify's synchronous runs stop after five minutes; batches stay well under.
BATCH = 40
LAST_RUN_KEY = "followers_refreshed_at"
CHECK_SECONDS = 15 * 60

_INSTAGRAM_USER = re.compile(r"instagram\.com/([A-Za-z0-9._]+)")


def instagram_username(url: str) -> str | None:
    match = _INSTAGRAM_USER.search(url)
    if not match:
        return None
    name = match.group(1).strip(".").lower()
    return None if name in {"p", "reel", "reels", "stories", "explore", "accounts"} else name


def facebook_key(url: str) -> str:
    """A page address reduced to what Apify's answer and ours share."""
    key = url.lower().split("?", 1)[0].rstrip("/")
    for prefix in ("https://", "http://", "www.", "m.", "web.", "ar-ar."):
        key = key.removeprefix(prefix)
    return key


def _chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class ApifyFollowers:
    def __init__(self, token: str, client: httpx.Client) -> None:
        self._token = token
        self._client = client

    def _run(self, actor: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        response = self._client.post(
            API.format(actor=actor),
            json=payload,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=330,
        )
        if response.status_code >= 400:
            logger.warning(
                "Apify run failed", extra={"actor": actor, "status": response.status_code}
            )
            return []
        data = response.json()
        return data if isinstance(data, list) else []

    def instagram(self, usernames: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for batch in _chunks(usernames, BATCH):
            for item in self._run(INSTAGRAM_ACTOR, {"usernames": batch}):
                name = str(item.get("username") or "").lower()
                followers = item.get("followersCount")
                if name and isinstance(followers, int):
                    counts[name] = followers
        return counts

    def facebook(self, urls: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for batch in _chunks(urls, BATCH):
            payload = {"startUrls": [{"url": url} for url in batch]}
            for item in self._run(FACEBOOK_ACTOR, payload):
                followers = item.get("followers")
                if followers is None:
                    followers = item.get("likes")
                page = item.get("facebookUrl") or item.get("pageUrl") or item.get("url")
                if isinstance(followers, int) and page:
                    counts[facebook_key(str(page))] = followers
        return counts


def refresh(db: Session, apify: ApifyFollowers, now: datetime | None = None) -> int:
    """Read every published shop's pages and store the counts; returns how
    many shops got at least one number."""
    moment = now or datetime.now(UTC)
    shops = (
        db.execute(
            select(Business)
            .options(selectinload(Business.social_links))
            .where(Business.status == BusinessStatus.APPROVED)
        )
        .scalars()
        .all()
    )
    instagram: dict[Business, str] = {}
    facebook: dict[Business, str] = {}
    for shop in shops:
        link: BusinessSocialLink
        for link in shop.social_links:
            if link.platform == SocialPlatform.INSTAGRAM:
                name = instagram_username(link.url)
                if name:
                    instagram[shop] = name
            elif link.platform == SocialPlatform.FACEBOOK:
                facebook[shop] = link.url

    ig_counts = apify.instagram(sorted(set(instagram.values()))) if instagram else {}
    fb_counts = apify.facebook(sorted(set(facebook.values()))) if facebook else {}

    updated = 0
    for shop in shops:
        found = False
        if shop in instagram and instagram[shop] in ig_counts:
            shop.instagram_followers = ig_counts[instagram[shop]]
            found = True
        if shop in facebook and facebook_key(facebook[shop]) in fb_counts:
            shop.facebook_followers = fb_counts[facebook_key(facebook[shop])]
            found = True
        if found:
            shop.followers_checked_at = moment
            updated += 1
    db.commit()
    logger.info(
        "Follower counts refreshed",
        extra={"shops": updated, "instagram": len(ig_counts), "facebook": len(fb_counts)},
    )
    return updated


def refresh_if_due(
    session_factory: Callable[[], Session],
    apify: ApifyFollowers,
    interval: timedelta,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> bool:
    with session_factory() as db:
        last = db.execute(
            text("select value from site_settings where key = :key"), {"key": LAST_RUN_KEY}
        ).scalar()
        moment = now()
        if last and moment - datetime.fromisoformat(last) < interval:
            return False
        # Recorded first, so a run that fails is not retried every 15 minutes.
        db.execute(
            text(
                "insert into site_settings (key, value) values (:key, :value)"
                " on conflict (key) do update set value = excluded.value"
            ),
            {"key": LAST_RUN_KEY, "value": moment.isoformat()},
        )
        db.commit()
        refresh(db, apify, moment)
        return True


async def run_daily(
    session_factory: Callable[[], Session], token: str, interval_hours: int
) -> None:
    interval = timedelta(hours=interval_hours)
    with httpx.Client(timeout=330) as client:
        apify = ApifyFollowers(token, client)
        while True:
            await asyncio.sleep(CHECK_SECONDS)
            try:
                await asyncio.to_thread(refresh_if_due, session_factory, apify, interval)
            except Exception:
                logger.exception("Refreshing follower counts failed")
