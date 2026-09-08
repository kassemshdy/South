"""Bearer-token authentication for the HTTP transport.

Over stdio there is nothing to authenticate: the client is the process that
spawned the server, and the credentials come from the same environment. Over
HTTP the server is reachable by anyone who learns the URL, and what it exposes
is the whole directory -- including listings no visitor may see -- plus the
power to write to the ticket board. So the HTTP transport does not start
without a token, and there is no flag to turn that off.

The token is compared with :func:`hmac.compare_digest`. A plain ``==`` on a
secret leaks its length and then its content through timing, and the fix costs
one import.
"""

from __future__ import annotations

import hmac
import logging
import os

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from pydantic import AnyHttpUrl

logger = logging.getLogger(__name__)

ENV_TOKEN = "SOUTH_MCP_TOKEN"
ENV_PUBLIC_URL = "SOUTH_MCP_PUBLIC_URL"

#: Short tokens are guessable and a guessed token is full read access to the
#: directory. Long enough that brute force is not the weak link.
MIN_TOKEN_LENGTH = 32


class AuthError(RuntimeError):
    """Raised at startup when the HTTP transport has no usable token."""


class SharedSecretVerifier(TokenVerifier):
    """Accepts one pre-shared token and nothing else.

    Deliberately not OAuth. This is enough for a client that can send an
    ``Authorization`` header -- Claude Code, a script, a routine -- and it
    keeps the server's own attack surface to a string comparison. A
    claude.ai custom connector expects an OAuth authorization server; adding
    one is a larger piece of work and belongs behind its own decision, not
    smuggled in as a default.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._token):
            # No detail, and no echo of what was sent: a log line that
            # records a rejected token records a near-miss guess.
            logger.warning("Rejected an MCP request with an invalid token")
            return None
        return AccessToken(
            token=token,
            client_id="south-mcp-client",
            scopes=[],
            expires_at=None,
        )


def load_verifier(environ: dict[str, str] | None = None) -> SharedSecretVerifier:
    env = os.environ if environ is None else environ
    token = env.get(ENV_TOKEN, "")

    if not token:
        raise AuthError(
            f"{ENV_TOKEN} is not set. The HTTP transport exposes the whole "
            "directory and accepts ticket writes, so it will not start "
            "unauthenticated. Generate one with: python3 -c "
            "'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if len(token) < MIN_TOKEN_LENGTH:
        raise AuthError(
            f"{ENV_TOKEN} is {len(token)} characters; at least "
            f"{MIN_TOKEN_LENGTH} are required."
        )
    return SharedSecretVerifier(token)


def load_auth_settings(environ: dict[str, str] | None = None) -> AuthSettings:
    """The metadata the protocol requires alongside a token verifier.

    The library refuses a verifier without these, and rightly: a client needs
    somewhere to look up who issues tokens and which resource they are for.
    Both point at this server, because it issues its own single token rather
    than delegating to an authorization server -- which is also the honest
    description of what this is, and the thing an OAuth flow would replace.

    ``validate_token_resource`` stays off: there is one resource and one
    token, so binding them adds a way to misconfigure and nothing else.
    """
    env = os.environ if environ is None else environ
    public_url = env.get(ENV_PUBLIC_URL, "").rstrip("/")

    if not public_url:
        raise AuthError(
            f"{ENV_PUBLIC_URL} is not set. The HTTP transport publishes it as "
            "the token issuer and resource identifier, so it has to be the "
            "URL clients actually reach -- e.g. https://mcp-south.up.railway.app"
        )
    if not public_url.startswith("https://") and "localhost" not in public_url:
        raise AuthError(
            f"{ENV_PUBLIC_URL} must be https:// -- a bearer token sent over "
            "plain HTTP is a token anyone on the path can copy."
        )

    return AuthSettings(
        issuer_url=AnyHttpUrl(public_url),
        resource_server_url=AnyHttpUrl(public_url),
        validate_token_resource=False,
        # Dynamic registration on, because claude.ai's connector flow starts
        # by registering itself and fails at that step otherwise. Registering
        # grants nothing: a registered client still cannot get a token
        # without the shared secret at the consent step.
        client_registration_options=ClientRegistrationOptions(enabled=True),
        # No identity to assert -- the MCP acts as one administrator.
        identity_assertion_enabled=False,
    )
