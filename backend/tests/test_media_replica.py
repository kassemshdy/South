"""The off-site copy only adds: nothing in the replica is replaced or deleted."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.services import media_replica


class Bucket:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = dict(files)
        self.saved: list[str] = []

    def keys(self) -> set[str]:
        return set(self.files)

    def read(self, key: str) -> bytes:
        if key == "businesses/broken.jpg":
            raise OSError("unreadable")
        return self.files[key]

    def save(self, *, key: str, data: bytes, content_type: str) -> object:
        self.files[key] = data
        self.saved.append(key)
        return None


def test_missing_files_and_backups_are_added_and_nothing_is_replaced() -> None:
    site = Bucket(
        {
            "businesses/1/logo.jpg": b"logo",
            "verification/3/id.pdf": b"scan",
            "backups/db/20261106T090000Z-daily.dump": b"dump",
            "pages/a.jpg": b"site",
        }
    )
    replica = Bucket({"pages/a.jpg": b"replica", "backups/db/20261001T000000Z-daily.dump": b"old"})

    assert media_replica.replicate(site, replica) == (3, 1, 0)
    assert replica.files["pages/a.jpg"] == b"replica"
    assert replica.files["verification/3/id.pdf"] == b"scan"
    assert replica.files["backups/db/20261106T090000Z-daily.dump"] == b"dump"
    # A backup the site has since pruned stays in the replica.
    assert "backups/db/20261001T000000Z-daily.dump" in replica.files
    assert "backups/db/20261001T000000Z-daily.dump" not in site.files


def test_a_file_that_cannot_be_read_does_not_stop_the_rest() -> None:
    site = Bucket({"businesses/broken.jpg": b"", "businesses/ok.jpg": b"ok"})
    replica = Bucket({})
    assert media_replica.replicate(site, replica) == (1, 0, 1)
    assert replica.saved == ["businesses/ok.jpg"]


def test_nothing_happens_without_a_replica_bucket() -> None:
    settings = get_settings().model_copy(update={"replica_s3_bucket": None})
    assert media_replica.replica_settings(settings) is None
    assert media_replica.replicate_configured(settings, object()) is None


def test_the_replica_uses_its_own_keys_and_aws_by_default() -> None:
    settings = get_settings().model_copy(
        update={
            "s3_bucket": "railway-bucket",
            "s3_endpoint_url": "https://t3.storageapi.dev",
            "s3_access_key_id": "railway-key",
            "s3_addressing_style": "virtual",
            "replica_s3_bucket": "janoubona-backup",
            "replica_s3_region": "eu-central-1",
            "replica_s3_access_key_id": "aws-key",
            "replica_s3_secret_access_key": "aws-secret",
        }
    )
    replica = media_replica.replica_settings(settings)
    assert replica is not None
    assert replica.s3_bucket == "janoubona-backup"
    assert replica.s3_endpoint_url is None  # AWS itself
    assert replica.s3_region == "eu-central-1"
    assert replica.s3_access_key_id == "aws-key"
    assert replica.s3_secret_access_key == "aws-secret"


def test_only_one_worker_copies_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import create_engine, text

    settings = get_settings()
    ran: list[str] = []
    monkeypatch.setattr(media_replica, "replicate_configured", lambda *a: ran.append("x"))
    holder = create_engine(settings.database_url)
    try:
        with holder.connect() as connection:
            connection.execute(text("select pg_advisory_lock(7242027)"))
            assert media_replica.replicate_if_first(settings, object()) is False
            connection.execute(text("select pg_advisory_unlock(7242027)"))
        assert media_replica.replicate_if_first(settings, object()) is True
    finally:
        holder.dispose()
    assert ran == ["x"]
