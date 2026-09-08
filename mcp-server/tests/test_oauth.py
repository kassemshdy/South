"""The OAuth authorization server.

Its job is narrow: let a client that speaks only OAuth present the shared
token. So the properties worth pinning are the ones that would let something
past *without* that token, and the ones that would let a token be reused.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from south_mcp.oauth import CODE_TTL_SECONDS, SouthOAuthProvider

TOKEN = "s" * 48
REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def run(coro):
    return asyncio.run(coro)


def a_client(client_id: str = "c1") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        redirect_uris=[AnyUrl(REDIRECT)],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
    )


def a_provider() -> SouthOAuthProvider:
    return SouthOAuthProvider(shared_token=TOKEN, public_url="https://mcp.test")


class _Params:
    """The subset of AuthorizationParams the provider reads."""

    def __init__(self) -> None:
        self.state = "st4te"
        self.scopes: list[str] = []
        self.code_challenge = "chal"
        self.redirect_uri = REDIRECT
        self.redirect_uri_provided_explicitly = True
        self.resource = None


def park(provider: SouthOAuthProvider, client_id: str = "c1") -> str:
    url = run(provider.authorize(a_client(client_id), _Params()))  # type: ignore[arg-type]
    return url.split("request=")[1]


# --- getting a code requires the token ------------------------------------


def test_the_right_token_yields_a_code_and_echoes_state() -> None:
    provider = a_provider()

    redirect = provider.approve(park(provider), TOKEN)

    assert redirect is not None
    assert redirect.startswith(REDIRECT)
    assert "code=" in redirect
    assert "state=st4te" in redirect


@pytest.mark.parametrize("wrong", ["", "z" * 48, TOKEN[:-1], TOKEN + "z"])
def test_a_wrong_token_yields_nothing(wrong: str) -> None:
    """The consent step is the only thing between the open internet and a
    token, so this is the single most important assertion in the file."""
    provider = a_provider()

    assert provider.approve(park(provider), wrong) is None


def test_a_parked_request_is_single_use() -> None:
    """Otherwise one intercepted consent URL could be redeemed repeatedly."""
    provider = a_provider()
    pending = park(provider)

    assert provider.approve(pending, TOKEN) is not None
    assert provider.approve(pending, TOKEN) is None


def test_an_unknown_request_id_yields_nothing() -> None:
    assert a_provider().approve("never-existed", TOKEN) is None


def test_a_stale_request_yields_nothing() -> None:
    provider = a_provider()
    pending = park(provider)
    provider._pending[pending].created_at = time.time() - CODE_TTL_SECONDS - 1

    assert provider.approve(pending, TOKEN) is None


def test_parked_requests_do_not_accumulate_forever() -> None:
    provider = a_provider()
    stale = park(provider)
    provider._pending[stale].created_at = time.time() - CODE_TTL_SECONDS - 1

    park(provider)  # authorize() sweeps

    assert stale not in provider._pending


# --- redeeming a code ------------------------------------------------------


def code_from(provider: SouthOAuthProvider, client_id: str = "c1") -> str:
    redirect = provider.approve(park(provider, client_id), TOKEN)
    assert redirect is not None
    return redirect.split("code=")[1].split("&")[0]


def test_a_code_issued_to_one_client_is_not_loadable_by_another() -> None:
    provider = a_provider()
    code = code_from(provider, "c1")

    assert run(provider.load_authorization_code(a_client("c2"), code)) is None
    assert run(provider.load_authorization_code(a_client("c1"), code)) is not None


def test_an_expired_code_is_not_loadable() -> None:
    provider = a_provider()
    code = code_from(provider)
    provider._codes[code].expires_at = time.time() - 1

    assert run(provider.load_authorization_code(a_client(), code)) is None


def test_exchanging_a_code_consumes_it() -> None:
    provider = a_provider()
    code = code_from(provider)
    loaded = run(provider.load_authorization_code(a_client(), code))

    run(provider.exchange_authorization_code(a_client(), loaded))

    assert run(provider.load_authorization_code(a_client(), code)) is None


def test_an_exchange_returns_both_tokens() -> None:
    provider = a_provider()
    loaded = run(provider.load_authorization_code(a_client(), code_from(provider)))

    issued = run(provider.exchange_authorization_code(a_client(), loaded))

    assert issued.access_token and issued.refresh_token
    assert issued.token_type == "Bearer"
    assert issued.expires_in and issued.expires_in > 0


# --- using and refreshing tokens ------------------------------------------


def issued_tokens(provider: SouthOAuthProvider):
    loaded = run(provider.load_authorization_code(a_client(), code_from(provider)))
    return run(provider.exchange_authorization_code(a_client(), loaded))


def test_an_issued_access_token_is_accepted() -> None:
    provider = a_provider()

    granted = run(provider.load_access_token(issued_tokens(provider).access_token))

    assert granted is not None
    assert granted.client_id == "c1"


def test_the_shared_token_still_works_alongside_oauth() -> None:
    """Adding the connector must not take away the simple path: a script or a
    routine sending the shared token needs no OAuth dance."""
    granted = run(a_provider().load_access_token(TOKEN))

    assert granted is not None
    assert granted.client_id == "south-mcp-shared-token"


def test_an_unknown_token_is_refused() -> None:
    assert run(a_provider().load_access_token("q" * 48)) is None


def test_an_expired_access_token_is_refused() -> None:
    provider = a_provider()
    access = issued_tokens(provider).access_token
    provider._access[access].expires_at = int(time.time()) - 1

    assert run(provider.load_access_token(access)) is None


def test_a_refresh_token_rotates_and_the_old_one_stops_working() -> None:
    """A copied refresh token is then useful only until the real client
    refreshes once."""
    provider = a_provider()
    first = issued_tokens(provider)
    loaded = run(provider.load_refresh_token(a_client(), first.refresh_token))

    second = run(provider.exchange_refresh_token(a_client(), loaded, []))

    assert second.refresh_token != first.refresh_token
    assert run(provider.load_refresh_token(a_client(), first.refresh_token)) is None
    assert run(provider.load_refresh_token(a_client(), second.refresh_token)) is not None


def test_a_refresh_token_is_bound_to_its_client() -> None:
    provider = a_provider()
    first = issued_tokens(provider)

    assert run(provider.load_refresh_token(a_client("other"), first.refresh_token)) is None


def test_revoking_an_access_token_stops_it() -> None:
    provider = a_provider()
    access = issued_tokens(provider).access_token
    loaded = run(provider.load_access_token(access))

    run(provider.revoke_token(loaded))

    assert run(provider.load_access_token(access)) is None


# --- registration ----------------------------------------------------------


def test_a_registered_client_can_be_read_back() -> None:
    provider = a_provider()
    run(provider.register_client(a_client("fresh")))

    assert run(provider.get_client("fresh")) is not None
    assert run(provider.get_client("never-registered")) is None


def test_registering_alone_grants_nothing() -> None:
    """Registration is open, because claude.ai's flow begins with it. What it
    must not do is confer access: a registered client still cannot get a
    token without the shared secret."""
    provider = a_provider()
    run(provider.register_client(a_client("fresh")))

    assert provider.approve(park(provider, "fresh"), "z" * 48) is None


def test_identity_assertion_is_refused_rather_than_faked() -> None:
    """There is no user to assert. Raising beats quietly issuing a token."""
    with pytest.raises(NotImplementedError):
        run(a_provider().exchange_identity_assertion(a_client(), None))
