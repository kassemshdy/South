#!/bin/sh
# Runs as root so it can fix ownership of the mounted media volume, then
# drops to the unprivileged appuser for everything else. Railway attaches
# volumes with root ownership regardless of what the image's USER is, so a
# volume mounted over $STORAGE_LOCAL_DIR is not writable by appuser until
# this chown runs — it can only happen here, at container start, after the
# volume is actually in place.
set -e

mkdir -p "$STORAGE_LOCAL_DIR"
chown -R appuser:appuser "$STORAGE_LOCAL_DIR"

exec gosu appuser sh -c '
  set -e
  alembic upgrade head
  python -m scripts.seed --ensure
  exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "${WEB_CONCURRENCY:-2}" --proxy-headers --forwarded-allow-ips="*"
'
