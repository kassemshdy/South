"""Hardening from the September 2026 security audit.

Each test pins one fix, stated as the attack it now refuses, so a later change
that reopens the hole fails here with a sentence explaining what was lost.
"""

from __future__ import annotations

import io
from urllib.parse import quote

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings
from app.core.dependencies import get_client_ip
from app.core.uploads import content_disposition, read_at_most
from app.main import allow_inline_scripts, create_app
from tests.samples import ar


def _request(forwarded: str | None, peer: str = "10.0.0.99") -> Request:
    headers = [] if forwarded is None else [(b"x-forwarded-for", forwarded.encode())]
    return Request(
        {"type": "http", "method": "GET", "path": "/", "headers": headers, "client": (peer, 1234)}
    )


# --- Client address: X-Forwarded-For is read from the right -------------------


def test_a_forged_left_most_address_is_not_the_client() -> None:
    # Behind Railway's edge and Caddy, the chain the API sees is
    # "<whatever the client sent>, <real client>, <edge>". The old code read the
    # left-most entry, so any caller could pick their own rate-limit identity.
    settings = Settings(trusted_proxy_hops=2)
    request = _request("1.2.3.4, 203.0.113.7, 10.0.0.1")
    assert get_client_ip(request, settings) == "203.0.113.7"


def test_rotating_the_forged_address_does_not_change_the_client() -> None:
    settings = Settings(trusted_proxy_hops=2)
    seen = {
        get_client_ip(_request(f"198.51.100.{n}, 203.0.113.7, 10.0.0.1"), settings)
        for n in range(20)
    }
    assert seen == {"203.0.113.7"}


def test_one_trusted_hop_reads_the_last_entry() -> None:
    # The default, and what the test client relies on elsewhere in the suite:
    # a single entry is the caller.
    assert get_client_ip(_request("203.0.113.5"), Settings()) == "203.0.113.5"
    assert get_client_ip(_request("9.9.9.9, 203.0.113.5"), Settings()) == "203.0.113.5"


def test_no_header_falls_back_to_the_socket_peer() -> None:
    assert get_client_ip(_request(None, peer="10.1.2.3"), Settings()) == "10.1.2.3"


def test_a_chain_shorter_than_the_trusted_hops_is_not_trusted() -> None:
    # Fewer entries than proxies means the header did not come through them as
    # configured, so none of it is believed.
    settings = Settings(trusted_proxy_hops=2)
    assert get_client_ip(_request("1.2.3.4", peer="10.1.2.3"), settings) == "10.1.2.3"


# --- Content-Security-Policy ---------------------------------------------------


def test_every_response_carries_a_content_security_policy(client: TestClient) -> None:
    policy = client.get("/api/health").headers["content-security-policy"]
    directives = {d.split(" ", 1)[0]: d for d in (p.strip() for p in policy.split(";"))}

    assert directives["object-src"] == "object-src 'none'"
    assert directives["frame-ancestors"] == "frame-ancestors 'none'"
    assert directives["base-uri"] == "base-uri 'self'"
    # The point of the policy: an injected inline <script> is refused.
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in directives["script-src"]


def test_the_policy_can_be_switched_off_per_environment() -> None:
    app = create_app(Settings(content_security_policy=None))
    response = TestClient(app).get("/api/health")
    assert "content-security-policy" not in response.headers


# --- API docs are not served by a deployed process ------------------------------


def test_hardened_environments_do_not_serve_the_api_map() -> None:
    for env in ("staging", "production"):
        app = create_app(Settings(app_env=env))
        assert app.docs_url is None
        assert app.openapi_url is None
        # No lifespan, so the production-safety check does not run here; the
        # routes simply must not exist.
        http = TestClient(app)
        assert http.get("/api/docs").status_code == 404
        assert http.get("/api/openapi.json").status_code == 404


def test_development_still_serves_the_docs() -> None:
    app = create_app(Settings(app_env="development"))
    assert app.docs_url == "/api/docs"
    assert TestClient(app).get("/api/openapi.json").status_code == 200


# --- Uploads are read with a bound -------------------------------------------------


def test_an_oversized_upload_is_read_only_one_byte_past_the_limit() -> None:
    body = io.BytesIO(b"x" * 10_000_000)
    data = read_at_most(body, 1_000)
    # Enough for the caller's own "len(data) > limit" check to refuse it,
    # and not a byte more held in memory.
    assert len(data) == 1_001


def test_a_file_within_the_limit_is_read_whole() -> None:
    assert read_at_most(io.BytesIO(b"abc"), 1_000) == b"abc"
    assert read_at_most(io.BytesIO(b"x" * 1_000), 1_000) == b"x" * 1_000


def test_an_empty_upload_reads_as_empty() -> None:
    assert read_at_most(io.BytesIO(b""), 1_000) == b""


# --- Download filenames cannot break the header ---------------------------------


def test_a_quote_in_the_filename_cannot_end_the_parameter() -> None:
    header = content_disposition('scan".pdf; filename="evil.html')
    # Only the two quotes that delimit the fallback survive -- the name's own
    # are replaced, so it cannot close the string and append a parameter. A
    # ';' inside a quoted-string is just a character.
    assert header.count('"') == 2
    assert header.startswith('attachment; filename="scan_.pdf; filename=_evil.html"; ')


def test_a_line_break_in_the_filename_cannot_start_a_new_header() -> None:
    header = content_disposition("scan.pdf\r\nSet-Cookie: session=stolen")
    assert "\r" not in header
    assert "\n" not in header


def test_a_non_latin_filename_survives_the_download() -> None:
    name = f"{ar('category.restaurants')}.pdf"
    header = content_disposition(name)
    assert header.startswith("attachment; ")
    assert header.endswith(f"filename*=UTF-8''{quote(name, safe='')}")
    # The fallback is plain ASCII for clients that ignore filename*.
    header.split("; ")[1].encode("ascii")


def test_inline_disposition_is_kept_for_viewable_attachments() -> None:
    assert content_disposition("receipt.png", inline=True).startswith("inline; ")


def test_a_blank_filename_gets_a_neutral_name() -> None:
    assert '; filename="download";' in content_disposition("   ")


# --- Static pages: inline scripts allowed, nothing else relaxed -------------------


def test_allowing_inline_scripts_touches_only_script_src() -> None:
    relaxed = allow_inline_scripts("default-src 'self'; script-src 'self'; object-src 'none'")
    assert relaxed == "default-src 'self'; script-src 'self' 'unsafe-inline'; object-src 'none'"
    # Idempotent, and adds a script-src where the policy had none.
    assert allow_inline_scripts(relaxed) == relaxed
    assert allow_inline_scripts("default-src 'self'").endswith("script-src 'self' 'unsafe-inline'")
