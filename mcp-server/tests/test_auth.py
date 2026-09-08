"""The HTTP transport's authentication.

Over stdio there is nothing to authenticate. Over HTTP the server is reachable
by anyone who learns the URL, and what it exposes is the whole directory --
including listings no visitor may see -- plus writes to the ticket board. These
tests pin that there is no path to serving that unauthenticated.
"""

from __future__ import annotations

import asyncio

import pytest

from south_mcp.auth import ENV_TOKEN, AuthError, SharedSecretVerifier, load_verifier

TOKEN = "x" * 40


def verify(token: str, against: str = TOKEN):
    return asyncio.run(SharedSecretVerifier(against).verify_token(token))


def test_the_right_token_is_accepted() -> None:
    granted = verify(TOKEN)

    assert granted is not None
    assert granted.token == TOKEN


@pytest.mark.parametrize(
    "wrong",
    [
        "",
        "y" * 40,
        TOKEN[:-1],
        TOKEN + "x",
        TOKEN.upper(),
        " " + TOKEN,
    ],
    ids=["empty", "different", "truncated", "extended", "case-changed", "padded"],
)
def test_anything_else_is_rejected(wrong: str) -> None:
    assert verify(wrong) is None


def test_no_token_means_no_http_server() -> None:
    """Not a warning, not a degraded mode: a refusal. An unauthenticated
    server here would publish every pending listing in the directory."""
    with pytest.raises(AuthError) as raised:
        load_verifier({})

    assert ENV_TOKEN in str(raised.value)


def test_an_empty_token_is_the_same_as_none() -> None:
    with pytest.raises(AuthError):
        load_verifier({ENV_TOKEN: ""})


def test_a_short_token_is_refused() -> None:
    """A guessed token is full read access, so the length floor is enforced
    at startup rather than left to whoever sets the variable."""
    with pytest.raises(AuthError) as raised:
        load_verifier({ENV_TOKEN: "short"})

    assert "5 characters" in str(raised.value)


def test_a_long_enough_token_loads() -> None:
    verifier = load_verifier({ENV_TOKEN: TOKEN})

    assert asyncio.run(verifier.verify_token(TOKEN)) is not None
    assert asyncio.run(verifier.verify_token("y" * 40)) is None


def test_the_verifier_does_not_leak_the_token_when_it_rejects() -> None:
    """A rejection carries no detail — not even how far it matched — because
    that is exactly the feedback a guess needs."""
    assert verify("y" * 40) is None
