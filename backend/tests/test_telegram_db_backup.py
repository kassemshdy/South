"""The periodic .sql copy of the database for the Telegram group."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services import telegram_archive
from app.services import telegram_db_backup as backup
from tests.conftest import make_owner


def _runner(seen: list[list[str]]) -> Any:
    """pg_dump stands in: each section answers with its own marker."""

    def run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen.append(args)
        section = next(a for a in args if a.startswith("--section=")).split("=")[1]
        return subprocess.CompletedProcess(args, 0, stdout=f"-- {section}\n".encode())

    return run


class _Telegram:
    def __init__(self, status: int = 200) -> None:
        self.sent: list[dict[str, Any]] = []
        self.status = status

    def post(self, url: str, *, data: dict[str, str], files: dict[str, Any]) -> Any:
        self.sent.append({"url": url, "data": data, "files": files})
        return type("Response", (), {"status_code": self.status})()


def test_the_copy_has_every_account_but_no_password_or_session_counter(db: Session) -> None:
    owner = make_owner("03971001")
    db.execute(text("update users set token_version = 7 where id = :id"), {"id": owner.id})
    db.commit()
    hashed = db.execute(
        text("select password_hash from users where id = :id"), {"id": owner.id}
    ).scalar()
    assert hashed

    seen: list[list[str]] = []
    dump = backup.sql_dump(get_settings().database_url, run=_runner(seen)).decode()

    # The three sections in order, the users rows between data and post-data,
    # and pg_dump told to leave the users rows to us.
    assert dump.index("-- pre-data") < dump.index("-- data") < dump.index("COPY public.users")
    assert dump.index("COPY public.users") < dump.index("-- post-data")
    assert any("--exclude-table-data=public.users" in args for args in seen)
    # The account is there; what it signs in with is not.
    assert owner.phone_number in dump
    assert hashed not in dump
    row = next(line for line in dump.splitlines() if owner.phone_number in line)
    columns = dump.split("COPY public.users (", 1)[1].split(")", 1)[0].replace('"', "").split(", ")
    values = dict(zip(columns, row.split("\t"), strict=True))
    assert values["password_hash"] == "\\N"
    assert values["token_version"] == "0"


def test_the_file_goes_once_an_hour_and_never_twice(db: Session) -> None:
    telegram = _Telegram()
    moment = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)

    def send(at: datetime) -> bool:
        return backup.send_if_due(
            get_settings().database_url,
            token="t0ken",
            chat_id="-100",
            interval=timedelta(hours=1),
            client=telegram,  # type: ignore[arg-type]
            now=lambda: at,
            run=_runner([]),
        )

    assert send(moment) is True
    sent = telegram.sent[0]
    name, data, kind = sent["files"]["document"]
    assert name == "janoubona-20261028T0900Z.sql"
    assert kind == "application/sql" and b"COPY public.users" in data
    assert sent["data"]["chat_id"] == "-100"

    assert send(moment + timedelta(minutes=30)) is False, "not twice within the hour"
    assert send(moment + timedelta(hours=1, minutes=1)) is True
    assert len(telegram.sent) == 2


def test_a_failed_send_is_tried_again_at_the_next_look(db: Session) -> None:
    failing = _Telegram(status=500)
    moment = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
    kwargs: dict[str, Any] = {
        "token": "t0ken",
        "chat_id": "-100",
        "interval": timedelta(hours=1),
        "now": lambda: moment,
        "run": _runner([]),
    }
    url = get_settings().database_url
    assert backup.send_if_due(url, client=failing, **kwargs) is False  # type: ignore[arg-type]
    working = _Telegram()
    assert backup.send_if_due(url, client=working, **kwargs) is True  # type: ignore[arg-type]


def test_a_large_copy_goes_gzipped() -> None:
    moment = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
    assert backup.file_for(b"x", moment)[0].endswith(".sql")
    big = b"x" * (backup.MAX_PLAIN_BYTES + 1)
    name, data = backup.file_for(big, moment)
    assert name.endswith(".sql.gz") and len(data) < len(big)


@pytest.mark.parametrize(
    ("env", "token", "expected"),
    [("production", "t0ken", True), ("production", None, False), ("development", "t0ken", False)],
)
def test_it_runs_only_in_production_with_telegram_configured(
    monkeypatch: pytest.MonkeyPatch, env: str, token: str | None, expected: bool
) -> None:
    started: list[str] = []

    async def fake(*_args: Any, **_kwargs: Any) -> None:
        started.append("hourly")

    monkeypatch.setattr(backup, "run_hourly", fake)
    # The archive would start with the token too, for every later test: the
    # suite never talks to Telegram.
    monkeypatch.setattr(telegram_archive, "configure", lambda *_args: None)
    settings = Settings(
        app_env=env,  # type: ignore[arg-type]
        secret_key="x" * 64,
        admin_password="a-strong-staging-password-1",
        telegram_bot_token=token,
        telegram_chat_id="-100",
        db_backup_interval_hours=0,
    )
    from fastapi.testclient import TestClient

    with TestClient(create_app(settings)):
        pass
    assert bool(started) is expected
