"""The container's start command must reach uvicorn.

``docker-entrypoint.sh`` hands its work to ``gosu appuser sh -c '...'``, one
single-quoted script. An apostrophe anywhere inside it, a comment included,
closes the quote early: everything after it is silently dropped, the script
exits 0, and no server ever starts. That is how two releases on 29 Oct 2026
failed their healthcheck ("The owners' full list ..."). This runs the real
file with every command stubbed and asserts the last step still happens.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "docker-entrypoint.sh"


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run(tmp_path: Path, **extra: str) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("python", "alembic", "uvicorn"):
        _stub(bin_dir, name, f'echo "RAN {name} $*"')
    _stub(bin_dir, "gosu", 'shift; exec "$@"')  # drop the user, run the rest
    _stub(bin_dir, "chown", "true")

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "STORAGE_LOCAL_DIR": str(tmp_path / "media"),
        "PORT": "8000",
    }
    env.pop("TELEGRAM_BACKFILL", None)
    env.pop("SKIP_MIGRATIONS", None)
    env.update(extra)
    result = subprocess.run(
        ["sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=30
    )

    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
def test_the_start_command_reaches_uvicorn(tmp_path: Path) -> None:
    ran = _run(tmp_path)
    for step in ("scripts.backup_db", "scripts.repair_alembic_stamp", "alembic upgrade", "scripts.seed", "scripts.import_locations", "scripts.replicate_media"):
        assert step in ran, f"{step} never ran:\n{ran}"
    assert "RAN uvicorn" in ran, f"uvicorn never started:\n{ran}"


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
def test_a_site_sharing_the_database_never_migrates_it(tmp_path: Path) -> None:
    """Staging on the live database once moved it to a revision live did not
    have, and every live release failed until it was put back (3 Nov 2026)."""
    ran = _run(tmp_path, SKIP_MIGRATIONS="1")
    assert "alembic" not in ran, ran
    assert "RAN uvicorn" in ran, f"uvicorn never started:\n{ran}"
