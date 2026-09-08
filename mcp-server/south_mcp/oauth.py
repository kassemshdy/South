"""An OAuth authorization server, just large enough to be a claude.ai connector.

claude.ai's connector flow begins with dynamic client registration and an
authorization-code exchange. A bearer-token server has no ``/register``
endpoint to answer, so the flow fails before it starts -- which is what
"Couldn't register with South MCP's sign-in service" means.

**What this is honest about.** There is no per-user identity here. The MCP
signs in to the directory as one administrator, so there is no second person
for OAuth to identify. What the authorization step actually checks is that
whoever is connecting holds ``SOUTH_MCP_TOKEN``. The security still rests on
that one secret; the OAuth machinery around it exists so a client that speaks
only OAuth can present it. Anyone reading this should not conclude the
directory gained real user authentication.

**Why the consent page is not skipped.** The obvious shortcut -- have
``authorize`` redirect straight back with a code -- would hand a token to
anyone who can reach the endpoint, which is the whole internet. Then the
shared secret would protect nothing. So the authorization step stops and asks
for it.

**State lives in memory.** Registered clients, codes and tokens are lost on
restart, so a redeploy means re-authorising the connector. That is a real
limitation and the reason it is acceptable is narrow: the service rebuilds
only when ``mcp-server/**`` changes, which is rare. Persisting them would
mean giving this service storage of its own, and storage holding OAuth tokens
is a bigger commitment than the problem currently justifies.
"""

from __future__ import annotations

import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

logger = logging.getLogger(__name__)

#: An access token outlives a single tool call by a wide margin but not a
#: working day, so a leaked one stops working without anyone intervening.
ACCESS_TOKEN_TTL_SECONDS = 60 * 60

#: Long enough that a connector set up once keeps working; the refresh token
#: is only ever sent to the token endpoint, not on every request.
REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30

#: A code is redeemed within seconds of being issued. Anything longer is a
#: window for a code sitting in a browser history or a log.
CODE_TTL_SECONDS = 300


@dataclass
class _PendingAuthorization:
    """An authorization request waiting for someone to prove they hold the
    token. Keyed by an unguessable id so the parameters are never carried in
    the consent page's own URL, where a browser would keep them."""

    client_id: str
    params: AuthorizationParams
    created_at: float = field(default_factory=time.time)


class SouthOAuthProvider(OAuthAuthorizationServerProvider):
    """The ten methods the library needs, over in-memory stores.

    ``load_access_token`` deliberately accepts the shared token as well as an
    OAuth-issued one, so adding the connector does not take away the simpler
    path: Claude Code over stdio, a script, or a routine sending a bearer
    header all keep working unchanged.
    """

    def __init__(self, shared_token: str, public_url: str) -> None:
        self._shared_token = shared_token
        self._public_url = public_url.rstrip("/")
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending: dict[str, _PendingAuthorization] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._access: dict[str, AccessToken] = {}
        self._refresh: dict[str, RefreshToken] = {}

    # --- clients ----------------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info
        # The client name is chosen by whoever registers, so it is logged as
        # data and never used to make a decision.
        logger.info(
            "Registered an OAuth client",
            extra={"client_id": client_info.client_id},
        )

    # --- authorization ----------------------------------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Park the request and send the browser to the consent page.

        Returns a URL on this server rather than the client's redirect_uri:
        redirecting straight back with a code would mean anyone who can reach
        this endpoint gets a token.
        """
        pending_id = secrets.token_urlsafe(24)
        self._pending[pending_id] = _PendingAuthorization(client.client_id, params)
        self._sweep()
        return f"{self._public_url}/authorize/consent?request={pending_id}"

    def approve(self, pending_id: str, token: str) -> str | None:
        """Redeem a parked request with the shared token.

        Returns the client's redirect URL carrying a fresh code, or None when
        the token is wrong or the request has expired or already been used.
        Called by the consent route, not by the library.
        """
        pending = self._pending.pop(pending_id, None)
        if pending is None:
            return None
        if time.time() - pending.created_at > CODE_TTL_SECONDS:
            return None
        if not hmac.compare_digest(token, self._shared_token):
            logger.warning("Consent rejected: wrong token")
            return None

        code = AuthorizationCode(
            code=secrets.token_urlsafe(32),
            scopes=pending.params.scopes or [],
            expires_at=time.time() + CODE_TTL_SECONDS,
            client_id=pending.client_id,
            code_challenge=pending.params.code_challenge,
            redirect_uri=pending.params.redirect_uri,
            redirect_uri_provided_explicitly=pending.params.redirect_uri_provided_explicitly,
            resource=pending.params.resource,
        )
        self._codes[code.code] = code

        separator = "&" if "?" in str(pending.params.redirect_uri) else "?"
        redirect = f"{pending.params.redirect_uri}{separator}code={code.code}"
        if pending.params.state:
            redirect += f"&state={pending.params.state}"
        return redirect

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._codes.get(authorization_code)
        # A code issued to one client must not be redeemable by another, and
        # an expired code must not be redeemable at all.
        if code is None or code.client_id != client.client_id:
            return None
        if code.expires_at < time.time():
            self._codes.pop(authorization_code, None)
            return None
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        # Single use: a replayed code must not mint a second token.
        self._codes.pop(authorization_code.code, None)
        return self._issue(client.client_id, authorization_code.scopes)

    # --- tokens -----------------------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        """An OAuth-issued token, or the shared token.

        The fallback is what keeps the simple path working: a script or a
        routine that sends ``Authorization: Bearer <SOUTH_MCP_TOKEN>`` needs
        no OAuth dance, and adding the connector did not take that away.
        """
        issued = self._access.get(token)
        if issued is not None:
            if issued.expires_at is not None and issued.expires_at < time.time():
                self._access.pop(token, None)
                return None
            return issued

        if hmac.compare_digest(token, self._shared_token):
            return AccessToken(
                token=token,
                client_id="south-mcp-shared-token",
                scopes=[],
                expires_at=None,
            )
        logger.warning("Rejected an MCP request with an invalid token")
        return None

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        stored = self._refresh.get(refresh_token)
        if stored is None or stored.client_id != client.client_id:
            return None
        if stored.expires_at is not None and stored.expires_at < time.time():
            self._refresh.pop(refresh_token, None)
            return None
        return stored

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Rotated, not reused: the old refresh token stops working, so a
        # copied one is useful only until the real client refreshes once.
        self._refresh.pop(refresh_token.token, None)
        return self._issue(client.client_id, scopes or refresh_token.scopes)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self._access.pop(token.token, None)
        self._refresh.pop(token.token, None)

    async def exchange_identity_assertion(
        self, client: OAuthClientInformationFull, params: Any
    ) -> OAuthToken:
        """Not supported: there is no identity to assert.

        ``identity_assertion_enabled`` stays off in the settings, so this is
        unreachable -- it raises rather than quietly issuing a token, because
        a token issued without a check is the failure this whole module is
        arranged to avoid.
        """
        raise NotImplementedError("South's MCP server asserts no user identity")

    # --- internals --------------------------------------------------------

    def _issue(self, client_id: str, scopes: list[str]) -> OAuthToken:
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        now = time.time()

        self._access[access] = AccessToken(
            token=access,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(now + ACCESS_TOKEN_TTL_SECONDS),
        )
        self._refresh[refresh] = RefreshToken(
            token=refresh,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(now + REFRESH_TOKEN_TTL_SECONDS),
        )
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(scopes) if scopes else None,
            refresh_token=refresh,
        )

    def _sweep(self) -> None:
        """Drop expired parked requests.

        In-memory stores that only ever grow are a slow leak, and a parked
        request nobody completed is the one entry with no other reason to be
        removed.
        """
        cutoff = time.time() - CODE_TTL_SECONDS
        for key in [k for k, v in self._pending.items() if v.created_at < cutoff]:
            self._pending.pop(key, None)
