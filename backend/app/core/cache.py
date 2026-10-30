"""A short in-memory cache for what anonymous visitors read.

The owners asked for it (29 Oct 2026). Every public page used to cost the
database a few queries per request; the same lists, home sections and
taxonomy are now served from memory for ``PUBLIC_CACHE_SECONDS`` (60 by
default, 0 turns it off; the test suite runs with it off).

What it may hold is narrow on purpose:

- only GET/HEAD, only paths under ``CACHED_PREFIXES``, only a 200 JSON or
  XML answer, and only for a request with **no** ``Authorization`` header
  -- an owner or administrator always reads the database, and nothing a
  token can see is ever stored;
- the routes that count a view (a shop, a product, a service profile) are
  not cached as responses, which would stop the counter; they cache their
  payload through :func:`cached` and still record every view.

What makes it safe is invalidation: **any successful write** (POST, PUT,
PATCH, DELETE answered below 400) empties it. The API runs several worker
processes in one container, each with its own memory, so the write also
bumps a version file they all read (``/tmp`` is shared by the container);
a worker that sees a newer version drops everything before answering. An
approval, a suspension or an edit is therefore visible on the very next
request, and the TTL only bounds what changes by the clock (a story
expiring, a workshop starting).
"""

from __future__ import annotations

import contextlib
import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.i18n import current_locale, resolve_locale

T = TypeVar("T")

#: Public, anonymous reads worth keeping. Everything else is never cached:
#: /api/admin, /api/my, /api/me, /api/auth, orders and every form.
CACHED_PREFIXES: tuple[str, ...] = (
    "/api/businesses",
    "/api/items",
    "/api/talent",
    "/api/talent-skills",
    "/api/categories",
    "/api/locations",
    "/api/home",
    "/api/menu",
    "/api/site-settings",
    "/api/workshops",
    "/api/activities",
    "/api/job-openings",
    "/api/articles",
    "/api/pages",
    "/api/page-covers",
    "/api/reels",
    "/api/team",
    "/api/testimonials",
    "/api/search",
    "/sitemap.xml",
    "/robots.txt",
)

#: Detail routes that count a view: cached as payloads, never as responses.
_COUNTED = re.compile(
    r"^/api/(businesses|items|talent)/(?!(latest|stats|most-ordered|top-rated|top-viewed)$)[^/]+$"
)
#: Sub-routes of the prefixes above that belong to an owner, never cached.
_PRIVATE = re.compile(r"^/api/businesses/[^/]+/(items|manage|orders|readiness)$")

_WRITES = frozenset({"POST", "PUT", "PATCH", "DELETE"})
MAX_ENTRIES = 2000


@dataclass
class _Entry:
    expires: float
    value: Any


class PublicCache:
    def __init__(self, ttl_seconds: int, version_file: Path) -> None:
        self.ttl = ttl_seconds
        self._version_file = version_file
        self._entries: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = threading.Lock()
        self._version = self._read_version()

    @property
    def enabled(self) -> bool:
        return self.ttl > 0

    # --- invalidation ----------------------------------------------------

    def _read_version(self) -> str:
        try:
            return self._version_file.read_text()
        except OSError:
            return ""

    def invalidate(self) -> None:
        """Empty this worker's cache and tell the others to empty theirs."""
        token = f"{os.getpid()}-{time.time_ns()}"
        with contextlib.suppress(OSError):
            self._version_file.write_text(token)
        with self._lock:
            self._entries.clear()
            self._version = token

    def _sync(self) -> None:
        current = self._read_version()
        if current != self._version:
            with self._lock:
                self._entries.clear()
                self._version = current

    # --- reads -------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        self._sync()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires < time.monotonic():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._entries[key] = _Entry(time.monotonic() + self.ttl, value)
            self._entries.move_to_end(key)
            while len(self._entries) > MAX_ENTRIES:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)


_cache: PublicCache | None = None


def configure(ttl_seconds: int, version_file: str) -> PublicCache:
    global _cache
    _cache = PublicCache(ttl_seconds, Path(version_file))
    return _cache


def get_cache() -> PublicCache | None:
    return _cache


def cached(key: str, build: Callable[[], T]) -> T:
    """``build()``'s result, kept for the TTL under ``key`` and the locale.

    For the routes that must still run per request (they count a view):
    the payload comes from memory, the counting does not."""
    cache = _cache
    if cache is None or not cache.enabled:
        return build()
    full = f"payload:{current_locale.get()}:{key}"
    hit = cache.get(full)
    if hit is not None:
        return hit  # type: ignore[no-any-return]
    value = build()
    cache.set(full, value)
    return value


def _cacheable_path(path: str) -> bool:
    if _COUNTED.match(path) or _PRIVATE.match(path):
        return False
    return any(path == prefix or path.startswith(prefix + "/") for prefix in CACHED_PREFIXES)


class PublicCacheMiddleware:
    """Serves cacheable anonymous GETs from memory; any write empties it."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        cache = _cache
        if scope["type"] != "http" or cache is None or not cache.enabled:
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        if method in _WRITES:
            status_holder: dict[str, int] = {}

            async def send_write(message: Message) -> None:
                if message["type"] == "http.response.start":
                    status_holder["status"] = message["status"]
                await send(message)

            await self.app(scope, receive, send_write)
            if status_holder.get("status", 500) < 400:
                cache.invalidate()
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        path = scope["path"]
        if (
            method not in ("GET", "HEAD")
            or "authorization" in headers
            or not _cacheable_path(path)
        ):
            await self.app(scope, receive, send)
            return

        locale = resolve_locale(headers.get("accept-language"))
        query = scope.get("query_string", b"").decode()
        key = f"response:{locale}:{path}?{query}"
        hit = cache.get(key)
        if hit is not None:
            status, raw_headers, body = hit
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [*raw_headers, (b"x-cache", b"HIT")],
                }
            )
            await send({"type": "http.response.body", "body": b"" if method == "HEAD" else body})
            return

        start: dict[str, Any] = {}
        chunks: list[bytes] = []

        async def send_read(message: Message) -> None:
            if message["type"] == "http.response.start":
                start.update(message)
                message = {
                    **message,
                    "headers": [*message.get("headers", []), (b"x-cache", b"MISS")],
                }
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False) and method == "GET":
                    content_type = dict(start.get("headers", [])).get(b"content-type", b"")
                    if start.get("status") == 200 and (
                        content_type.startswith(b"application/json")
                        or content_type.startswith(b"application/xml")
                        or content_type.startswith(b"text/plain")
                    ):
                        cache.set(key, (200, list(start["headers"]), b"".join(chunks)))
            await send(message)

        await self.app(scope, receive, send_read)
