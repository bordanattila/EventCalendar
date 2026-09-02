"""Entry points for triggering iCloud sync from the Kivy UI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _import_sync_job():
    sync_dir = PROJECT_ROOT / "sync"
    storage_dir = PROJECT_ROOT / "storage"
    for path in (str(sync_dir), str(PROJECT_ROOT), str(storage_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import sync_job  # noqa: WPS433 — runtime import from sync/

    return sync_job


def run_sync_with_state() -> dict:
    """Run full sync in-process and return the persisted sync state."""
    sync_job = _import_sync_job()
    result = sync_job.run_sync()
    return sync_job.write_sync_state(result, mode="full")


def run_sync_subprocess(timeout: int = 300) -> dict:
    """Run sync via the project venv (used when caldav is not importable)."""
    python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)

    proc = subprocess.run(
        [str(python), "sync/sync_job.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    sync_job = _import_sync_job()
    state = sync_job.read_sync_state()
    if state is not None:
        return state

    return {
        "last_sync_at": None,
        "mode": "full",
        "success": proc.returncode == 0,
        "summary": proc.stdout.strip() or proc.stderr.strip() or "Sync finished",
        "errors": [] if proc.returncode == 0 else [proc.stderr.strip() or "Sync failed"],
    }
