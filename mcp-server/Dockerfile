# The agent-facing MCP server, served over HTTP.
#
# Its own image rather than a mode of the API's: it needs none of the API's
# dependencies (no SQLAlchemy, no Pillow, no database driver) and pins a
# different pydantic, which is the whole reason it lives in its own tree.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOUTH_MCP_TRANSPORT=http

WORKDIR /app

COPY requirements.txt ./
# --no-cache-dir keeps the layer small; pytest comes along because the file is
# one list, and a few megabytes is cheaper than a second requirements file to
# keep in step.
RUN pip install --no-cache-dir -r requirements.txt

COPY south_mcp ./south_mcp

# Never root: this process holds an admin credential for the directory, so a
# container escape should not also be a root shell.
RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

# No CMD-time secrets. SOUTH_API_URL, SOUTH_AGENT_EMAIL, SOUTH_AGENT_PASSWORD,
# SOUTH_MCP_TOKEN and SOUTH_MCP_PUBLIC_URL come from the environment, and the
# process exits 2 rather than starting without them.
CMD ["python", "-m", "south_mcp"]
