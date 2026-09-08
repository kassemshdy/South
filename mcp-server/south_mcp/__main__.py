"""Entry point: ``python -m south_mcp`` speaks MCP over stdio.

Logging goes to stderr on purpose. stdout is the protocol channel, so a stray
print there corrupts the stream and the client reports a malformed message
rather than the thing that actually went wrong.
"""

from __future__ import annotations

import logging
import sys

from south_mcp.client import SouthClient
from south_mcp.config import ConfigError, load_config
from south_mcp.server import build_server


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        config = load_config()
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 2

    if config.is_production:
        logging.getLogger(__name__).warning(
            "Pointed at %s, which looks like a live environment.", config.base_url
        )

    client = SouthClient(config)
    try:
        build_server(config, client).run("stdio")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
