# Restoring the database

Read this when the live site has lost its data — the API logged
`DATABASE IS EMPTY BUT UPLOADS EXIST`, or Sentry raised the same message as a
fatal error.

## What happened last time

On 2026-10-04 the production database ran in a plain `postgres:16-alpine`
container with no disk. It was redeployed, came back empty, and the API
rebuilt an empty schema on top without a word. A month of listings, accounts
and articles were lost, and nobody noticed for a day. There was no backup.

Since then:

- the database is Railway's own **`Postgres`** service, on a persistent disk;
- the API copies the database into the bucket **at every boot, before
  migrations**, and **once a day** (`app/services/db_backup.py`);
- an API that starts against an empty database while uploads exist raises a
  **fatal Sentry error** instead of starting quietly.

## Where the copies are

In the private bucket (`janoubona-media`), under `backups/db/`, named
`<UTC timestamp>-<boot|daily|manual>.dump` so the newest sorts last. The last
60 are kept. `/media` refuses the folder: a dump holds every account's
identity, so it is as private as an ID scan.

Each file is a `pg_dump --format=custom` archive of the whole database.

## Restore

1. **Stop new writes.** Nobody should enter data until this is finished:
   whatever is entered into the empty database is overwritten by the
   restore.
2. **Pick the backup.** Take the newest `backups/db/*.dump` from *before* the
   loss. A `boot` dump taken by the very start that found the database empty
   does not exist: the script refuses to back up an empty database.
3. **Download it** from the bucket (Railway dashboard → the bucket → the
   file, or any S3 client with the bucket's credentials).
4. **Restore into the live database**, replacing what is there:

   ```bash
   # DATABASE_URL: the api service's value, without "+psycopg"
   psql "$DATABASE_URL" -c "drop schema public cascade; create schema public;"
   pg_restore --no-owner --no-acl -d "$DATABASE_URL" backup.dump
   ```

   Use a `pg_restore` at least as new as the server (Postgres 18).
5. **Redeploy the `api` service.** Its start command runs migrations — a
   dump older than the code is brought up to date — and takes a fresh
   backup of the restored database.
6. **Check the site**: listings, an owner sign-in, the admin panel.

The procedure was rehearsed on 2026-10-05: a dump taken by
`scripts/backup_db.py` and restored into an empty database reproduced every
row count and the schema version exactly.

## Rules that keep it from happening

- **Never redeploy, delete or reconfigure the `Postgres` service** without a
  backup taken in the last hour and the owner's explicit go-ahead.
- Keep Railway's own backups switched on for `Postgres` (its Backups tab).
  The bucket copies are a second, independent line.
- A Sentry error reading `DATABASE IS EMPTY BUT UPLOADS EXIST` is an
  emergency: stop and restore before anything else.
