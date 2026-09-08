"""A stand-in for the directory API, recording what the client actually sent.

Deliberately not a mock of the client: the point of most of these tests is
which HTTP requests a tool makes, so the seam is the transport and the
assertions are about method, path and body.
"""

from __future__ import annotations

import json
from typing import Any

import httpx2 as httpx

from south_mcp.config import Config

TOKEN = "test-token"


class StubApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.bodies: list[Any] = []
        self.sign_ins = 0
        self.responses: dict[tuple[str, str], Any] = {}
        #: Paths that answer 401 once before succeeding, to exercise re-auth.
        self.expire_once: set[str] = set()

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    @property
    def config(self) -> Config:
        return Config(base_url="http://api.test", email="agent@test", password="secret")

    def on(self, method: str, path: str, payload: Any) -> None:
        self.responses[(method, path)] = payload

    def paths(self, method: str | None = None) -> list[str]:
        return [path for verb, path in self.calls if method is None or verb == method]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path == "/api/auth/admin/login":
            self.sign_ins += 1
            return httpx.Response(200, json={"access_token": TOKEN, "token_type": "bearer"})

        if path in self.expire_once:
            self.expire_once.discard(path)
            return httpx.Response(401, json={"error": {"code": "token_revoked", "message": "no"}})

        self.calls.append((request.method, path))
        self.bodies.append(json.loads(request.content) if request.content else None)

        payload = self.responses.get((request.method, path))
        if payload is None:
            return httpx.Response(404, json={"error": {"code": "not_found", "message": path}})
        return httpx.Response(200, json=payload)
