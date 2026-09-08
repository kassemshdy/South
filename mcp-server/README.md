# South directory MCP server

Exposes the directory to an agent: read any part of it, write only to the
support ticket board.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
```

It needs `SOUTH_API_URL`, `SOUTH_AGENT_EMAIL` and `SOUTH_AGENT_PASSWORD` and
refuses to start without them. See [`../docs/MCP.md`](../docs/MCP.md) for the
tool list, what it deliberately cannot do, and how to run a routine against it.
