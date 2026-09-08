"""HTTP client for the directory's admin API.

Every write this client makes lands on a FastAPI route, which calls a service,
which calls a repository. The MCP server therefore cannot bypass a rule the
service layer enforces -- an assignee that must be an administrator, a
sort_order the server re-derives -- because there is no second path into the
database. That is the reason this is an HTTP client and not a set of direct
SQLAlchemy sessions.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx2 as httpx

from south_mcp.config import Config
from south_mcp.redaction import redact

logger = logging.getLogger(__name__)

LOGIN_PATH = "/api/auth/admin/login"


class ApiError(RuntimeError):
    """A failing API call, carrying the server's own error message.

    The API answers every failure with one envelope (``{"error": {"code",
    "message"}}``), so the message a tool reports back is the message the
    application chose -- not a status code an agent has to guess about.
    """

    def __init__(self, status: int, code: str | None, message: str) -> None:
        super().__init__(f"{status} {code or 'error'}: {message}")
        self.status = status
        self.code = code


class SouthClient:
    """Signs in once, keeps the token, re-authenticates when it expires.

    Access tokens last 14 days (``Settings.access_token_ttl_minutes``), far
    longer than any single agent run, so there is no refresh schedule here: a
    401 is the signal, and one retry after a fresh sign-in is enough. A second
    401 is a real credential problem and is raised rather than looped on.
    """

    def __init__(self, config: Config, transport: httpx.BaseTransport | None = None) -> None:
        self._config = config
        self._token: str | None = None
        self._http = httpx.Client(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
            follow_redirects=True,
            transport=transport,
        )

    # --- authentication ----------------------------------------------------

    def sign_in(self) -> None:
        response = self._http.post(
            LOGIN_PATH,
            json={"email": self._config.email, "password": self._config.password},
        )
        if response.status_code != 200:
            # Deliberately does not echo the payload: it contains the password.
            raise ApiError(
                response.status_code,
                "sign_in_failed",
                f"Could not sign in as {self._config.email}.",
            )
        self._token = str(response.json()["access_token"])
        logger.info("Signed in to %s", self._config.base_url)

    # --- requests ----------------------------------------------------------

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """One API call, returning already-redacted JSON."""
        if self._token is None:
            self.sign_in()

        response = self._send(method, path, **kwargs)
        if response.status_code == 401:
            self.sign_in()
            response = self._send(method, path, **kwargs)

        if response.status_code >= 400:
            raise ApiError(response.status_code, *_error_of(response))

        if not response.content:
            return None
        return redact(response.json())

    def get(self, path: str, **params: Any) -> Any:
        # Drop unset filters rather than sending `?status=None`, which the
        # API would reject as an invalid enum member.
        query = {key: value for key, value in params.items() if value is not None}
        return self.request("GET", path, params=query)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, json=payload or {})

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PUT", path, json=payload)

    def close(self) -> None:
        self._http.close()

    # --- internals ---------------------------------------------------------

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._token}"}
        return self._http.request(method, path, headers=headers, **kwargs)


def _error_of(response: httpx.Response) -> tuple[str | None, str]:
    try:
        error = response.json().get("error", {})
        return error.get("code"), error.get("message", response.text)
    except Exception:  # a proxy or gateway can answer in HTML, not the error envelope
        return None, response.text[:500]
