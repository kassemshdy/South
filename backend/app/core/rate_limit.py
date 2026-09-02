"""Rate limiting.

Defined as a protocol with a database-backed default so limits hold across
multiple API workers or replicas. A Redis implementation can be dropped in later
without touching any caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.auth import RateLimitEvent


@dataclass(frozen=True)
class RateLimitRule:
    bucket: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitStatus:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter(Protocol):
    def check(self, rule: RateLimitRule, identifier: str) -> RateLimitStatus:
        """Report whether an action is currently allowed, without recording it."""
        ...

    def hit(self, rule: RateLimitRule, identifier: str) -> RateLimitStatus:
        """Record an attempt and report the resulting status."""
        ...


class DatabaseRateLimiter:
    """Sliding-window limiter stored in ``rate_limit_events``."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def _window_start(self, rule: RateLimitRule) -> datetime:
        return datetime.now(UTC) - timedelta(seconds=rule.window_seconds)

    def _events_in_window(self, rule: RateLimitRule, identifier: str) -> list[datetime]:
        rows = self._db.execute(
            select(RateLimitEvent.created_at)
            .where(
                RateLimitEvent.bucket == rule.bucket,
                RateLimitEvent.identifier == identifier,
                RateLimitEvent.created_at >= self._window_start(rule),
            )
            .order_by(RateLimitEvent.created_at)
        ).scalars()
        return list(rows)

    def _status(self, rule: RateLimitRule, timestamps: list[datetime]) -> RateLimitStatus:
        used = len(timestamps)
        if used < rule.limit:
            return RateLimitStatus(
                allowed=True, remaining=rule.limit - used, retry_after_seconds=0
            )

        # The window frees up when the oldest recorded attempt ages out.
        oldest = timestamps[0]
        retry_after = int(
            (oldest + timedelta(seconds=rule.window_seconds) - datetime.now(UTC)).total_seconds()
        )
        return RateLimitStatus(
            allowed=False, remaining=0, retry_after_seconds=max(retry_after, 1)
        )

    def check(self, rule: RateLimitRule, identifier: str) -> RateLimitStatus:
        return self._status(rule, self._events_in_window(rule, identifier))

    def hit(self, rule: RateLimitRule, identifier: str) -> RateLimitStatus:
        """Record an attempt.

        The returned status describes *this* attempt, not the next one: with a
        limit of 3, the third call is allowed and the fourth is refused.
        """
        timestamps = self._events_in_window(rule, identifier)
        if len(timestamps) >= rule.limit:
            return self._status(rule, timestamps)

        self._db.add(RateLimitEvent(bucket=rule.bucket, identifier=identifier))
        self._db.flush()
        return RateLimitStatus(
            allowed=True,
            remaining=rule.limit - len(timestamps) - 1,
            retry_after_seconds=0,
        )

    def purge_expired(self, older_than_seconds: int = 86_400) -> int:
        """Housekeeping so the table does not grow without bound."""
        cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
        result = self._db.execute(
            delete(RateLimitEvent).where(RateLimitEvent.created_at < cutoff)
        )
        return result.rowcount or 0

    def count(self, rule: RateLimitRule, identifier: str) -> int:
        return int(
            self._db.execute(
                select(func.count())
                .select_from(RateLimitEvent)
                .where(
                    RateLimitEvent.bucket == rule.bucket,
                    RateLimitEvent.identifier == identifier,
                    RateLimitEvent.created_at >= self._window_start(rule),
                )
            ).scalar_one()
        )
