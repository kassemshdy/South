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
  # A copy of the database before this deploy changes anything -- or, if the
  # database came back empty beside existing uploads, a fatal alarm instead.
  # Never fails the boot. See app/services/db_backup.py.
  python -m scripts.backup_db --reason boot
  # A second site sharing this database (a staging copy on live data) sets
  # SKIP_MIGRATIONS: only a live release may move the database to a new
  # revision, or the next live release finds a revision it does not know.
  # repair_alembic_stamp first puts back a stamp such a site once left here
  # (see the script); on any other database it does nothing.
  if [ -z "$SKIP_MIGRATIONS" ]; then
    python -m scripts.repair_alembic_stamp
    alembic upgrade head
  fi
  python -m scripts.seed --ensure
  python -m scripts.copy_media_to_bucket
  # The off-site copy to Amazon S3, inert unless REPLICA_S3_BUCKET is set. In
  # the background: a first copy of every file outlasts the healthcheck.
  python -m scripts.replicate_media &
  # In the background: it reads every photo from the bucket, and on 6 Nov
  # 2026 a slow bucket held it past the 180-second healthcheck in front of
  # uvicorn, so the deploy was refused. A photo it has not reached yet only
  # shows its full image on cards meanwhile.
  python -m scripts.backfill_thumbnails &
  # Past data to the Telegram archive, only while TELEGRAM_BACKFILL is set.
  # In the background: Telegram allows ~20 messages a minute, and the site
  # must not wait on that to start serving.
  if [ -n "$TELEGRAM_BACKFILL" ]; then python -m scripts.telegram_backfill & fi
  # The full list of towns from the owners, once per database; see the script. In
  # the background, like the backfill: on 29 Oct 2026 it ran past the
  # 180-second healthcheck in front of uvicorn and the deploy was refused.
  python -m scripts.import_locations &
  exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "${WEB_CONCURRENCY:-2}" --proxy-headers --forwarded-allow-ips="*"
'
