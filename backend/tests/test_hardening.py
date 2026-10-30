"""Hardening from the September 2026 security audit.

Each test pins one fix, stated as the attack it now refuses, so a later change
that reopens the hole fails here with a sentence explaining what was lost.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import DEFAULT_CONTENT_SECURITY_POLICY, Settings
from app.core.dependencies import get_client_ip
from app.core.downloads import content_disposition
from app.core.uploads import read_at_most
from app.main import allow_inline_scripts, create_app


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
    # Clarity's tag only loads the recorder, from a second host; allowing the
    # tag alone records nothing.
    assert {"https://www.clarity.ms", "https://scripts.clarity.ms"} <= set(
        directives["script-src"].split()
    )
    # A photo picked for upload is previewed from a blob: URL; refusing it
    # left every upload form showing an empty box.
    assert "blob:" in directives["img-src"].split()


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


# --- The fronts in front of the API ------------------------------------------------

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def test_both_fronts_cap_the_request_body_above_the_largest_application() -> None:
    """An anonymous multipart route would otherwise spool any size to disk
    before the API's own check; the cap must still admit a business
    application (two ID scans and a logo)."""
    settings = Settings()
    largest = 2 * settings.max_verification_doc_bytes + settings.max_upload_bytes
    for name in ("Caddyfile", "Caddyfile.staging"):
        match = re.search(r"max_size\s+(\d+)MB", (FRONTEND / name).read_text())
        assert match, name
        assert int(match.group(1)) * 1024 * 1024 > largest, name


def test_the_staging_front_sends_the_apis_security_headers() -> None:
    """Staging serves its pages itself, so the API's headers never reach
    them; the policy there must be the API's own, kept in step."""
    staging = (FRONTEND / "Caddyfile.staging").read_text()
    assert f'Content-Security-Policy "{DEFAULT_CONTENT_SECURITY_POLICY}"' in staging
    assert 'X-Frame-Options "DENY"' in staging
    assert "Strict-Transport-Security" in staging


def test_health_says_only_that_it_is_alive(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_cross_origin_requests_carry_no_credentials(client: TestClient) -> None:
    response = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-credentials") != "true"


# --- Download filenames cannot break the header ---------------------------------


def test_a_quote_in_the_filename_cannot_end_the_parameter() -> None:
    header = content_disposition('scan".pdf; filename="evil.html')
    # Only the two quotes that delimit the fallback survive, so the name
    # cannot close the string and append a parameter of its own.
    assert header.count('"') == 2


def test_a_line_break_in_the_filename_cannot_start_a_new_header() -> None:
    header = content_disposition("scan.pdf\r\nSet-Cookie: session=stolen")
    assert "\r" not in header
    assert "\n" not in header


# --- Static pages: inline scripts allowed, nothing else relaxed -------------------


def test_allowing_inline_scripts_touches_only_script_src() -> None:
    relaxed = allow_inline_scripts("default-src 'self'; script-src 'self'; object-src 'none'")
    assert relaxed == "default-src 'self'; script-src 'self' 'unsafe-inline'; object-src 'none'"
    # Idempotent, and adds a script-src where the policy had none.
    assert allow_inline_scripts(relaxed) == relaxed
    assert allow_inline_scripts("default-src 'self'").endswith("script-src 'self' 'unsafe-inline'")
