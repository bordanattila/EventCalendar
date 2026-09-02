"""
Sync endpoints for triggering and monitoring iCloud calendar sync.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from calendar_agent.config import settings


router = APIRouter()


class SyncStatusResponse(BaseModel):
    last_sync_at: str | None = None
    mode: str | None = None
    success: bool | None = None
    summary: str | None = None
    errors: list[str] = Field(default_factory=list)
    pull: dict[str, Any] | None = None
    push: dict[str, Any] | None = None
    delete: dict[str, Any] | None = None


class SyncTriggerResponse(BaseModel):
    success: bool
    summary: str
    last_sync_at: str | None = None
    errors: list[str] = Field(default_factory=list)


def _sync_state_path() -> Path:
    return settings.project_root / "sync" / "sync_state.json"


def _read_sync_state() -> dict | None:
    path = _sync_state_path()
    if not path.exists():
        return None
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _run_sync_blocking() -> dict:
    import sys

    project_root = settings.project_root
    sys.path.insert(0, str(project_root))
    from app.sync_runner import run_sync_subprocess

    return run_sync_subprocess()


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Return the last recorded sync run."""
    state = _read_sync_state()
    if state is None:
        return SyncStatusResponse(summary="Never synced")
    return SyncStatusResponse(**state)


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync():
    """Run a full iCloud sync (pull, push, delete)."""
    try:
        state = await asyncio.to_thread(_run_sync_blocking)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    errors = state.get("errors") or []
    return SyncTriggerResponse(
        success=bool(state.get("success", False)),
        summary=state.get("summary") or "Sync finished",
        last_sync_at=state.get("last_sync_at"),
        errors=errors,
    )
