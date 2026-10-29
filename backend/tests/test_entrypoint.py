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


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
def test_the_start_command_reaches_uvicorn(tmp_path: Path) -> None:
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
    result = subprocess.run(
        ["sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=30
    )

    assert result.returncode == 0, result.stderr
    ran = result.stdout
    for step in ("scripts.backup_db", "alembic upgrade", "scripts.seed", "scripts.import_locations"):
        assert step in ran, f"{step} never ran:\n{ran}"
    assert "RAN uvicorn" in ran, f"uvicorn never started:\n{ran}"
