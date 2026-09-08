"""Configuration, read from the environment and never from a file in the repo.

Same discipline as the ``VITE_`` variables described in AGENTS.md: with no
credentials there is no server at all. It refuses to start rather than
booting into a state where every tool fails one call at a time, which from
the far side of a stdio pipe looks like a broken directory rather than a
missing password.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_BASE_URL = "SOUTH_API_URL"
ENV_EMAIL = "SOUTH_AGENT_EMAIL"
ENV_PASSWORD = "SOUTH_AGENT_PASSWORD"


class ConfigError(RuntimeError):
    """Raised at startup when the environment is incomplete."""


@dataclass(frozen=True)
class Config:
    base_url: str
    email: str
    password: str
    timeout_seconds: float = 20.0

    @property
    def is_production(self) -> bool:
        """Whether this is pointed at something a real visitor can reach.

        Only used to make the log line at startup say so out loud. A routine
        that thinks it is on staging and is actually on live is the failure
        worth spending a string on.
        """
        host = self.base_url.lower()
        return "localhost" not in host and "127.0.0.1" not in host and "develop" not in host


def load_config(environ: dict[str, str] | None = None) -> Config:
    env = os.environ if environ is None else environ

    missing = [name for name in (ENV_BASE_URL, ENV_EMAIL, ENV_PASSWORD) if not env.get(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". The MCP server signs in as a service account; it has no default credentials."
        )

    return Config(
        base_url=env[ENV_BASE_URL].rstrip("/"),
        email=env[ENV_EMAIL],
        password=env[ENV_PASSWORD],
    )
