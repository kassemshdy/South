"""Database backups to the bucket, and the alarm for a wiped database.

The production database was lost on 2026-10-04 because it had no disk and no
backup, and the API rebuilt an empty schema without a word. These pin the two
safeguards added after: a copy in the bucket that old copies cannot crowd
out, and a fatal report when the API meets an empty database beside uploads.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.main import PRIVATE_MEDIA_FOLDERS
from app.services import db_backup
from app.storage.base import StoredFile


class FakeBucket:
    """Just enough of S3Storage: save, delete and a listing."""

    def __init__(self, keys: set[str] | None = None) -> None:
        self.files: dict[str, bytes] = {key: b"" for key in (keys or set())}

    def save(self, *, key: str, data: bytes, content_type: str) -> StoredFile:
        self.files[key] = data
        return StoredFile(
            key=key, url=f"/media/{key}", size_bytes=len(data), content_type=content_type
        )

    def delete(self, key: str) -> None:
        self.files.pop(key, None)

    def keys(self) -> set[str]:
        return set(self.files)


def _runner(output: bytes, seen: list[list[str]]):  # type: ignore[no-untyped-def]
    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=output)

    return run


def test_a_backup_is_a_pg_dump_of_the_database_saved_in_the_private_folder() -> None:
    bucket = FakeBucket()
    seen: list[list[str]] = []
    key = db_backup.back_up(
        "postgresql+psycopg://user:secret@db.internal:5432/railway",
        bucket,  # type: ignore[arg-type]
        reason="boot",
        now=datetime(2026, 10, 5, 17, 30, tzinfo=UTC),
        run=_runner(b"PGDMP-archive", seen),
    )
    assert key == "backups/db/20261005T173000Z-boot.dump"
    assert bucket.files[key] == b"PGDMP-archive"
    # pg_dump reads a libpq URL: the SQLAlchemy driver suffix is dropped.
    assert seen[0][0] == "pg_dump"
    assert seen[0][-1] == "postgresql://user:secret@db.internal:5432/railway"
    assert "--format=custom" in seen[0]


def test_old_backups_are_pruned_and_the_newest_kept() -> None:
    old = {f"backups/db/202609{day:02d}T020000Z-daily.dump" for day in range(1, 31)}
    unrelated = {"businesses/x/logo/a.jpg"}
    bucket = FakeBucket(old | unrelated)
    removed = db_backup.prune(bucket, bucket.keys(), keep=10)  # type: ignore[arg-type]
    assert removed == 20
    kept = sorted(key for key in bucket.files if key.startswith("backups/"))
    assert kept == sorted(old)[-10:]
    # Only backups are ever pruned.
    assert "businesses/x/logo/a.jpg" in bucket.files


def test_backups_are_never_served_by_media() -> None:
    """A dump holds every account's identity: private like ID scans."""
    assert db_backup.FOLDER in PRIVATE_MEDIA_FOLDERS


def test_an_empty_database_beside_uploads_reads_as_wiped() -> None:
    assert db_backup.looks_wiped({"businesses/1/logo/a.jpg"})
    assert db_backup.looks_wiped({"backups/db/20261001T020000Z-daily.dump"})
    # A brand-new site has nothing uploaded: not an alarm.
    assert not db_backup.looks_wiped(set())


def test_an_empty_database_is_one_no_migration_ever_ran_on(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    assert db_backup.database_is_empty(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("create table alembic_version (version_num varchar(32))"))
    engine.dispose()
    assert not db_backup.database_is_empty(url)


def test_the_boot_script_raises_the_alarm_instead_of_backing_up_a_wiped_database(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from scripts import backup_db

    bucket = FakeBucket({"businesses/1/logo/a.jpg"})
    # The script configures logging for the container; leave pytest's capture.
    monkeypatch.setattr(backup_db, "configure_logging", lambda *a, **k: None)
    monkeypatch.setattr(backup_db, "get_storage", lambda: bucket)
    monkeypatch.setattr(db_backup, "database_is_empty", lambda _url: True)
    backed_up: list[str] = []
    monkeypatch.setattr(db_backup, "back_up", lambda *a, **k: backed_up.append("x"))

    with caplog.at_level(logging.CRITICAL):
        assert backup_db.main(["--reason", "boot"]) == 0
    assert "DATABASE IS EMPTY BUT UPLOADS EXIST" in caplog.text
    assert backed_up == []


def test_a_failed_backup_never_stops_the_site_from_starting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import backup_db

    monkeypatch.setattr(backup_db, "get_storage", lambda: FakeBucket())
    monkeypatch.setattr(db_backup, "database_is_empty", lambda _url: False)

    def broken(*_: object, **__: object) -> str:
        raise subprocess.CalledProcessError(1, ["pg_dump"])

    monkeypatch.setattr(db_backup, "back_up", broken)
    assert backup_db.main(["--reason", "boot"]) == 0


def test_only_one_api_worker_takes_the_daily_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Several workers share the schedule; a Postgres advisory lock picks one."""
    from app.core.config import get_settings

    url = get_settings().database_url
    taken: list[str] = []
    monkeypatch.setattr(db_backup, "back_up", lambda *a, **k: taken.append(k["reason"]))

    assert db_backup.back_up_if_first(url, FakeBucket(), reason="daily")  # type: ignore[arg-type]
    assert taken == ["daily"]

    # While another worker holds the lock, this one stands aside.
    holder = create_engine(url)
    with holder.connect() as connection:
        connection.execute(text("select pg_advisory_lock(:key)"), {"key": db_backup._LOCK_KEY})
        assert not db_backup.back_up_if_first(url, FakeBucket(), reason="daily")  # type: ignore[arg-type]
        connection.execute(text("select pg_advisory_unlock(:key)"), {"key": db_backup._LOCK_KEY})
    holder.dispose()
    assert taken == ["daily"]
