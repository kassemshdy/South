"""The database as a plain ``.sql`` file, sent to the Telegram group every hour.

The owners' decision (28 Oct 2026), beside the backups in the bucket
(``app.services.db_backup``): a copy they can open and keep themselves,
in the same group the archive posts to (``app.services.telegram_archive``),
under the same rule that the group's membership is the access control.

One thing is left out, as everywhere else Telegram is concerned: what
people sign in with. ``users.password_hash`` is emptied and
``users.token_version`` set back to 0 in the copy -- the rest of every row
is there, so the file restores a whole site, and an owner restored from it
is issued a new password as after any reset. ``pg_dump`` cannot leave out a
column, so the dump is taken in its three sections with the ``users`` rows
excluded from the data section, and those rows are written in between by a
``COPY`` that selects every column but replaces the two.

Inert without ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID``, like the
archive, and only in production. The API checks every few minutes whether
an hour has passed since the last file; the time of the last one is kept in
``site_settings``, so a deploy does not restart the hour, and an advisory
lock keeps the API's several workers from sending it twice.
"""

from __future__ import annotations

import asyncio
import gzip
import logging
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
from psycopg import sql
from sqlalchemy import create_engine, text

from app.core.i18n import translate
from app.services import db_backup

logger = logging.getLogger("app.services.telegram_db_backup")

#: The two columns never sent: the password and the session counter.
REDACTED_USER_COLUMNS = {"password_hash": "NULL", "token_version": "0"}

#: Where the time of the last file is kept.
LAST_SENT_KEY = "telegram_db_backup_at"

#: How often the API looks at the clock; the file goes once an hour.
CHECK_SECONDS = 300

#: sendDocument accepts up to 50 MB; above this the file goes gzipped.
MAX_PLAIN_BYTES = 45 * 1024 * 1024

_LOCK_KEY = 7_242_027

Runner = Callable[..., "subprocess.CompletedProcess[bytes]"]


def _pg_dump(database_url: str, *args: str, run: Runner) -> bytes:
    target, password = db_backup.libpq_url(database_url)
    # Only what pg_dump needs: see db_backup.dump.
    env = {"PATH": os.environ.get("PATH", "")}
    if password:
        env["PGPASSWORD"] = password
    result = run(
        ["pg_dump", "--format=plain", "--no-owner", "--no-acl", *args, target],
        capture_output=True,
        check=True,
        timeout=600,
        env=env,
    )
    return result.stdout


def users_copy(database_url: str) -> bytes:
    """The ``users`` rows as a ``COPY ... FROM stdin`` block, every column
    as it is but the two in ``REDACTED_USER_COLUMNS``."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            columns = [
                row[0]
                for row in connection.execute(
                    text(
                        "select column_name from information_schema.columns"
                        " where table_schema = 'public' and table_name = 'users'"
                        " order by ordinal_position"
                    )
                )
            ]
            selected = sql.SQL(", ").join(
                sql.SQL(REDACTED_USER_COLUMNS[name])
                if name in REDACTED_USER_COLUMNS
                else sql.Identifier(name)
                for name in columns
            )
            query = sql.SQL("COPY (SELECT {} FROM public.users) TO STDOUT").format(selected)
            raw = connection.connection.dbapi_connection
            assert raw is not None
            rows = bytearray()
            with raw.cursor() as cursor, cursor.copy(query) as copy:  # type: ignore[attr-defined]
                for chunk in copy:
                    rows += chunk
    finally:
        engine.dispose()
    header = "COPY public.users ({}) FROM stdin;\n".format(
        ", ".join(f'"{name}"' for name in columns)
    )
    return header.encode() + bytes(rows) + b"\\.\n\n"


def sql_dump(database_url: str, *, run: Runner = subprocess.run) -> bytes:
    """The whole database as plain SQL, restorable with ``psql``, without
    anyone's password hash or session counter."""
    return b"".join(
        (
            _pg_dump(database_url, "--section=pre-data", run=run),
            _pg_dump(
                database_url, "--section=data", "--exclude-table-data=public.users", run=run
            ),
            users_copy(database_url),
            _pg_dump(database_url, "--section=post-data", run=run),
        )
    )


def file_for(dump: bytes, now: datetime) -> tuple[str, bytes]:
    """The file's name and bytes: plain ``.sql``, gzipped only if too big
    for Telegram."""
    name = f"janoubona-{now.strftime('%Y%m%dT%H%MZ')}.sql"
    if len(dump) <= MAX_PLAIN_BYTES:
        return name, dump
    return f"{name}.gz", gzip.compress(dump)


def send_document(
    client: httpx.Client, *, token: str, chat_id: str, name: str, data: bytes, caption: str
) -> bool:
    response = client.post(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data={"chat_id": chat_id, "caption": caption},
        files={"document": (name, data, "application/sql")},
    )
    if response.status_code >= 400:
        # The URL carries the token, so only the status is logged.
        logger.warning("telegram database backup failed: %s", response.status_code)
        return False
    return True


def send_if_due(
    database_url: str,
    *,
    token: str,
    chat_id: str,
    interval: timedelta,
    client: httpx.Client,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    run: Runner = subprocess.run,
) -> bool:
    """Send the file if the last one is ``interval`` old; True when sent."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            locked = connection.execute(
                text("select pg_try_advisory_lock(:key)"), {"key": _LOCK_KEY}
            ).scalar()
            if not locked:
                return False
            try:
                last = connection.execute(
                    text("select value from site_settings where key = :key"),
                    {"key": LAST_SENT_KEY},
                ).scalar()
                moment = now()
                if last and moment - datetime.fromisoformat(last) < interval:
                    return False
                name, data = file_for(sql_dump(database_url, run=run), moment)
                caption = translate(
                    "telegram.db_backup", locale="ar", time=moment.strftime("%Y-%m-%d %H:%M UTC")
                )
                if not send_document(
                    client, token=token, chat_id=chat_id, name=name, data=data, caption=caption
                ):
                    return False
                connection.execute(
                    text(
                        "insert into site_settings (key, value) values (:key, :value)"
                        " on conflict (key) do update set value = excluded.value"
                    ),
                    {"key": LAST_SENT_KEY, "value": moment.isoformat()},
                )
                connection.commit()
                logger.info("Database sent to Telegram: %s, %d bytes", name, len(data))
                return True
            finally:
                connection.execute(text("select pg_advisory_unlock(:key)"), {"key": _LOCK_KEY})
    finally:
        engine.dispose()


async def run_hourly(
    database_url: str, *, token: str, chat_id: str, interval_hours: int
) -> None:
    """Look every few minutes; send when the last file is an interval old.
    A failure is reported and the next look tries again."""
    interval = timedelta(hours=interval_hours)
    with httpx.Client(timeout=120) as client:
        while True:
            await asyncio.sleep(CHECK_SECONDS)
            try:
                await asyncio.to_thread(
                    send_if_due,
                    database_url,
                    token=token,
                    chat_id=chat_id,
                    interval=interval,
                    client=client,
                )
            except Exception:
                logger.exception("Sending the database to Telegram failed")
