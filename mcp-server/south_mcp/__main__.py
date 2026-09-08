"""Entry point.

``python -m south_mcp`` speaks MCP over stdio -- the default, because it is
the safe one: the client is the process that spawned this one, nothing is
listening on a port, and the credentials never leave the machine.

``SOUTH_MCP_TRANSPORT=http`` serves it over HTTP instead, for a client that
cannot spawn a process. That reaches further, so it costs more: it refuses to
start without ``SOUTH_MCP_TOKEN``, because what it exposes is the whole
directory -- including listings no visitor may see -- and the power to write
to the ticket board.

Logging goes to stderr on purpose. Over stdio, stdout is the protocol channel,
so a stray print there corrupts the stream and the client reports a malformed
message rather than the thing that actually went wrong.
"""

from __future__ import annotations

import logging
import os
import sys

from south_mcp.auth import AuthError, load_auth_settings, load_verifier
from south_mcp.client import SouthClient
from south_mcp.config import ConfigError, load_config
from south_mcp.server import build_server

ENV_TRANSPORT = "SOUTH_MCP_TRANSPORT"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    transport = os.environ.get(ENV_TRANSPORT, "stdio").strip().lower()
    if transport not in {"stdio", "http"}:
        print(f"{ENV_TRANSPORT} must be 'stdio' or 'http', not {transport!r}", file=sys.stderr)
        return 2

    try:
        config = load_config()
        # Over stdio there is no one to authenticate; over HTTP there is, and
        # this raises rather than serving the directory to whoever asks.
        verifier = load_verifier() if transport == "http" else None
        auth = load_auth_settings() if transport == "http" else None
    except (AuthError, ConfigError) as error:
        print(str(error), file=sys.stderr)
        return 2

    if config.is_production:
        logging.getLogger(__name__).warning(
            "Pointed at %s, which looks like a live environment.", config.base_url
        )

    client = SouthClient(config)
    try:
        server = build_server(config, client, token_verifier=verifier, auth=auth)
        if transport == "stdio":
            server.run("stdio")
        else:
            # Railway supplies PORT; bind every interface so its proxy can
            # reach the container, which 127.0.0.1 would refuse.
            server.run(
                "streamable-http",
                host="0.0.0.0",
                port=int(os.environ.get("PORT", "8080")),
            )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
