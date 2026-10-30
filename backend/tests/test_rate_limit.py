"""The limiter's own housekeeping and its one-key-at-a-time recording.

``rate_limit_events`` used to grow forever: ``purge_expired`` existed and
nothing called it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.auth import RateLimitEvent

RULE = RateLimitRule(bucket="test_bucket", limit=3, window_seconds=60)


def _count(db: Session) -> int:
    return int(db.execute(select(func.count()).select_from(RateLimitEvent)).scalar_one())


def test_recording_an_attempt_clears_out_what_no_window_can_count(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    stale = datetime.now(UTC) - timedelta(seconds=rate_limit.KEEP_SECONDS + 60)
    recent = datetime.now(UTC) - timedelta(hours=20)
    db.add_all(
        [
            RateLimitEvent(bucket="old", identifier="a", created_at=stale),
            RateLimitEvent(bucket="old", identifier="b", created_at=stale),
            RateLimitEvent(bucket="day", identifier="c", created_at=recent),
        ]
    )
    db.commit()

    monkeypatch.setattr(rate_limit, "PURGE_CHANCE", 1.0)
    DatabaseRateLimiter(db).hit(RULE, "someone")
    db.commit()

    # The two stale rows are gone; a row a one-day window still counts, and
    # the attempt just recorded, are kept.
    assert _count(db) == 2


def test_the_limit_still_holds_with_the_lock_taken(db: Session) -> None:
    limiter = DatabaseRateLimiter(db)
    results = [limiter.hit(RULE, "same").allowed for _ in range(4)]
    db.commit()
    assert results == [True, True, True, False]
