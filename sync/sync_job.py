"""iCloud sync job — pull, push, and delete reconciliation for calendar.db."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import caldav
import dateutil.tz
from dotenv import load_dotenv

SYNC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SYNC_DIR.parent
sys.path.insert(0, str(SYNC_DIR))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "storage"))

load_dotenv(PROJECT_ROOT / ".env", override=True)

from db_manager import Event, SessionLocal  # noqa: E402
from icloud_sync import _get_calendars, _get_etag  # noqa: E402
from ical_mapper import (  # noqa: E402
    event_to_ical,
    ical_to_event,
    is_cancelled,
    is_master_event,
)

# Wide window — recurrence is expanded locally via is_event_on_date().
PULL_START = datetime(2020, 1, 1)
PULL_END = datetime(2030, 1, 1)
CONFLICT_LOG = SYNC_DIR / "sync.log"
SYNC_STATE_FILE = SYNC_DIR / "sync_state.json"

_SYNCABLE_FIELDS = (
    "title",
    "date",
    "time",
    "location",
    "notes",
    "recurrence",
    "recurrence_end",
    "event_end_time",
    "ical_etag",
    "last_modified",
)


@dataclass
class PullResult:
    inserted: int = 0
    updated: int = 0
    deleted: int = 0
    skipped_pending: int = 0
    conflicts_remote_won: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class PushResult:
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class DeleteResult:
    deleted: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncResult:
    pull: PullResult = field(default_factory=PullResult)
    push: PushResult = field(default_factory=PushResult)
    delete: DeleteResult = field(default_factory=DeleteResult)

    @property
    def success(self) -> bool:
        return not (self.pull.errors or self.push.errors or self.delete.errors)


def _require_credentials() -> tuple[str, str]:
    apple_id = os.getenv("ICLOUD_APPLE_ID")
    app_password = os.getenv("ICLOUD_APPLE_PASSWORD")
    if not apple_id or not app_password:
        raise SystemExit(
            "Missing ICLOUD_APPLE_ID or ICLOUD_APPLE_PASSWORD in .env "
            "(use an app-specific password, not your Apple ID password)"
        )
    return apple_id, app_password


def _connect_client() -> caldav.DAVClient:
    apple_id, app_password = _require_credentials()
    return caldav.DAVClient(
        url="https://caldav.icloud.com/",
        username=apple_id,
        password=app_password,
    )


def _calendar_config() -> tuple[str | None, str | None, str]:
    return (
        os.getenv("ICLOUD_CALENDAR_NAME"),
        os.getenv("ICLOUD_CALENDAR_URL"),
        os.getenv("DEFAULT_TIMEZONE", "America/New_York"),
    )


def _calendar_event_count(calendar, tz) -> int:
    start = PULL_START.replace(tzinfo=tz)
    end = PULL_END.replace(tzinfo=tz)
    try:
        return len(
            list(calendar.search(start=start, end=end, event=True, expand=False))
        )
    except Exception:
        return 0


def _get_push_calendar(client: caldav.DAVClient):
    """Return the single calendar local edits should be pushed to."""
    calendar_name, calendar_url, timezone = _calendar_config()
    calendars = _get_calendars(client.principal(), calendar_name, calendar_url)
    if len(calendars) == 1:
        return calendars[0]

    tz = dateutil.tz.gettz(timezone)
    ranked = sorted(
        ((cal, _calendar_event_count(cal, tz)) for cal in calendars),
        key=lambda item: item[1],
        reverse=True,
    )
    best, count = ranked[0]
    print(
        f"Warning: {len(calendars)} calendars matched — using the one with "
        f"{count} event(s). Set ICLOUD_CALENDAR_URL in .env to pick explicitly."
    )
    return best


def _build_remote_index(calendar, tz) -> dict[str, Any]:
    """
    Map ical_uid → CalDAV event object.

    iCloud rejects UID-only searches (412), so we scan the same date window as pull.
    """
    start = PULL_START.replace(tzinfo=tz)
    end = PULL_END.replace(tzinfo=tz)
    index: dict[str, Any] = {}

    for caldav_event in calendar.search(
        start=start, end=end, event=True, expand=False
    ):
        for component in caldav_event.icalendar_instance.walk("vevent"):
            if not is_master_event(component):
                continue
            uid = str(component.get("uid"))
            if uid:
                index[uid] = caldav_event

    return index


def _log_conflict(message: str) -> None:
    with CONFLICT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat()} {message}\n")


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _remote_is_newer(remote_lm: str | None, local_lm: str | None) -> bool:
    remote = _parse_iso(remote_lm)
    local = _parse_iso(local_lm)
    if remote and local:
        return remote > local
    return False


def _apply_mapped(event: Event, mapped: dict[str, Any]) -> None:
    for key in _SYNCABLE_FIELDS:
        setattr(event, key, mapped[key])
    event.source = "icloud"
    event.sync_status = "synced"


def _remote_changed(db_event: Event, mapped: dict[str, Any]) -> bool:
    if mapped["ical_etag"] and db_event.ical_etag != mapped["ical_etag"]:
        return True
    if mapped["ical_etag"]:
        return False
    return db_event.last_modified != mapped["last_modified"]


def pull_from_icloud(session_factory=SessionLocal) -> PullResult:
    """
    PULL: fetch iCloud master events and reconcile into calendar.db.

    - New UID          → insert (source=icloud, sync_status=synced)
    - Changed remote   → update (unless local row is pending_push/delete)
    - pending_push + remote newer → conflict, remote wins (logged)
    - Cancelled remote → delete from DB
    - iCloud row gone  → delete synced icloud rows missing from remote
    """
    result = PullResult()
    calendar_name, calendar_url, timezone = _calendar_config()

    tz = dateutil.tz.gettz(timezone)
    start = PULL_START.replace(tzinfo=tz)
    end = PULL_END.replace(tzinfo=tz)

    client = _connect_client()
    calendars = _get_calendars(client.principal(), calendar_name, calendar_url)
    remote_uids: set[str] = set()

    with session_factory() as session:
        for calendar in calendars:
            for caldav_event in calendar.search(
                start=start, end=end, event=True, expand=False
            ):
                for component in caldav_event.icalendar_instance.walk("vevent"):
                    if not is_master_event(component):
                        continue

                    try:
                        uid = str(component.get("uid"))
                    except Exception as exc:
                        result.errors.append(f"Missing UID: {exc}")
                        continue

                    if is_cancelled(component):
                        remote_uids.discard(uid)
                        db_event = (
                            session.query(Event).filter_by(ical_uid=uid).one_or_none()
                        )
                        if db_event and db_event.source == "icloud":
                            session.delete(db_event)
                            result.deleted += 1
                        continue

                    remote_uids.add(uid)

                    try:
                        mapped = ical_to_event(component, etag=_get_etag(caldav_event))
                    except ValueError as exc:
                        result.errors.append(f"UID {uid}: {exc}")
                        continue

                    db_event = (
                        session.query(Event).filter_by(ical_uid=uid).one_or_none()
                    )

                    if db_event is None:
                        session.add(Event(**mapped))
                        result.inserted += 1
                        continue

                    if db_event.sync_status == "pending_delete":
                        continue

                    if db_event.sync_status == "pending_push":
                        if _remote_is_newer(mapped.get("last_modified"), db_event.last_modified):
                            _log_conflict(
                                f"CONFLICT uid={uid} local={db_event.last_modified} "
                                f"remote={mapped.get('last_modified')} -> remote wins"
                            )
                            _apply_mapped(db_event, mapped)
                            result.updated += 1
                            result.conflicts_remote_won += 1
                        else:
                            result.skipped_pending += 1
                        continue

                    if _remote_changed(db_event, mapped):
                        _apply_mapped(db_event, mapped)
                        result.updated += 1

        stale = (
            session.query(Event)
            .filter(
                Event.source == "icloud",
                Event.sync_status == "synced",
                Event.ical_uid.isnot(None),
                Event.ical_uid.notin_(remote_uids),
            )
            .all()
        )
        for event in stale:
            session.delete(event)
            result.deleted += 1

        session.commit()

    return result


def push_to_icloud(
    session_factory=SessionLocal,
    remote_index: dict[str, Any] | None = None,
) -> PushResult:
    """
    PUSH: send local pending_push rows to iCloud.

    - No remote copy yet → CREATE
    - Remote copy exists → UPDATE
    """
    result = PushResult()
    _, _, timezone = _calendar_config()

    client = _connect_client()
    calendar = _get_push_calendar(client)
    tz = dateutil.tz.gettz(timezone)
    if remote_index is None:
        remote_index = _build_remote_index(calendar, tz)
    now = datetime.now().isoformat()

    with session_factory() as session:
        pending = (
            session.query(Event).filter(Event.sync_status == "pending_push").all()
        )

        for db_event in pending:
            try:
                ical_body = event_to_ical(db_event, timezone=timezone)
            except ValueError as exc:
                result.errors.append(f"Event {db_event.id}: {exc}")
                continue

            remote = remote_index.get(db_event.ical_uid)

            try:
                if remote is None:
                    saved = calendar.add_event(ical_body)
                    result.created += 1
                else:
                    remote.data = ical_body
                    saved = remote.save()
                    result.updated += 1

                db_event.ical_etag = _get_etag(saved)
                db_event.sync_status = "synced"
                db_event.last_modified = now
            except Exception as exc:
                result.errors.append(
                    f"Event {db_event.id} ({db_event.title!r}): {exc}"
                )

        session.commit()

    return result


def process_deletions(
    session_factory=SessionLocal,
    remote_index: dict[str, Any] | None = None,
) -> DeleteResult:
    """
    DELETE: remove pending_delete rows from iCloud, then hard-delete locally.
    """
    result = DeleteResult()

    client = _connect_client()
    calendar = _get_push_calendar(client)
    _, _, timezone = _calendar_config()
    tz = dateutil.tz.gettz(timezone)
    if remote_index is None:
        remote_index = _build_remote_index(calendar, tz)

    with session_factory() as session:
        tombstones = (
            session.query(Event).filter(Event.sync_status == "pending_delete").all()
        )

        for db_event in tombstones:
            remote = remote_index.get(db_event.ical_uid) if db_event.ical_uid else None
            if remote:
                try:
                    remote.delete()
                except Exception as exc:
                    result.errors.append(
                        f"Event {db_event.id} ({db_event.title!r}): {exc}"
                    )
                    continue

            session.delete(db_event)
            result.deleted += 1

        session.commit()

    return result


def read_sync_state() -> dict | None:
    if not SYNC_STATE_FILE.exists():
        return None
    try:
        return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_sync_state(
    result: SyncResult | PullResult | PushResult | DeleteResult,
    *,
    mode: str = "full",
) -> dict:
    """Persist the last sync run for the UI and API."""
    payload: dict[str, Any] = {
        "last_sync_at": datetime.now().isoformat(),
        "mode": mode,
        "success": True,
        "summary": _format_result(result),
    }

    if isinstance(result, SyncResult):
        payload["success"] = result.success
        payload["pull"] = {
            "inserted": result.pull.inserted,
            "updated": result.pull.updated,
            "deleted": result.pull.deleted,
            "skipped_pending": result.pull.skipped_pending,
            "conflicts_remote_won": result.pull.conflicts_remote_won,
            "errors": result.pull.errors,
        }
        payload["push"] = {
            "created": result.push.created,
            "updated": result.push.updated,
            "errors": result.push.errors,
        }
        payload["delete"] = {
            "deleted": result.delete.deleted,
            "errors": result.delete.errors,
        }
        payload["errors"] = (
            result.pull.errors + result.push.errors + result.delete.errors
        )
    elif isinstance(result, PullResult):
        payload["pull"] = {
            "inserted": result.inserted,
            "updated": result.updated,
            "deleted": result.deleted,
            "skipped_pending": result.skipped_pending,
            "conflicts_remote_won": result.conflicts_remote_won,
            "errors": result.errors,
        }
        payload["errors"] = result.errors
        payload["success"] = not result.errors
    elif isinstance(result, PushResult):
        payload["push"] = {
            "created": result.created,
            "updated": result.updated,
            "errors": result.errors,
        }
        payload["errors"] = result.errors
        payload["success"] = not result.errors
    else:
        payload["delete"] = {"deleted": result.deleted, "errors": result.errors}
        payload["errors"] = result.errors
        payload["success"] = not result.errors

    SYNC_STATE_FILE.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return payload


def last_sync_display_text() -> str:
    state = read_sync_state()
    if not state:
        return "Never synced"
    when = state.get("last_sync_at", "")
    try:
        when_dt = datetime.fromisoformat(when)
        when = when_dt.strftime("%b %d, %Y %I:%M %p")
    except ValueError:
        pass
    status = "OK" if state.get("success", True) else "Errors"
    return f"Last synced: {when} ({status})"


def run_sync() -> SyncResult:
    """Run full two-way sync: pull, push, then delete."""
    client = _connect_client()
    calendar = _get_push_calendar(client)
    _, _, timezone = _calendar_config()
    tz = dateutil.tz.gettz(timezone)
    remote_index = _build_remote_index(calendar, tz)

    return SyncResult(
        pull=pull_from_icloud(),
        push=push_to_icloud(remote_index=remote_index),
        delete=process_deletions(remote_index=remote_index),
    )


def _format_result(result: SyncResult | PullResult | PushResult | DeleteResult) -> str:
    if isinstance(result, SyncResult):
        lines = [
            "Sync complete:",
            (
                f"  Pull:    {result.pull.inserted} inserted, {result.pull.updated} updated, "
                f"{result.pull.deleted} deleted, {result.pull.skipped_pending} skipped, "
                f"{result.pull.conflicts_remote_won} conflicts (remote won)"
            ),
            f"  Push:    {result.push.created} created, {result.push.updated} updated",
            f"  Delete:  {result.delete.deleted} deleted",
        ]
        errors = result.pull.errors + result.push.errors + result.delete.errors
        if errors:
            lines.append(f"  Errors:  {len(errors)}")
        return "\n".join(lines)

    if isinstance(result, PullResult):
        return (
            f"Pull complete: {result.inserted} inserted, {result.updated} updated, "
            f"{result.deleted} deleted, {result.skipped_pending} skipped, "
            f"{result.conflicts_remote_won} conflicts (remote won)"
            + (f", {len(result.errors)} error(s)" if result.errors else "")
        )

    if isinstance(result, PushResult):
        return (
            f"Push complete: {result.created} created, {result.updated} updated"
            + (f", {len(result.errors)} error(s)" if result.errors else "")
        )

    return (
        f"Delete complete: {result.deleted} deleted"
        + (f", {len(result.errors)} error(s)" if result.errors else "")
    )


def _print_errors(errors: list[str]) -> None:
    for err in errors:
        print(f"  error: {err}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync calendar.db with iCloud CalDAV")
    parser.add_argument("--pull-only", action="store_true", help="Run pull step only")
    parser.add_argument("--push-only", action="store_true", help="Run push step only")
    parser.add_argument(
        "--delete-only", action="store_true", help="Run delete step only"
    )
    args = parser.parse_args()

    selected = sum([args.pull_only, args.push_only, args.delete_only])
    if selected > 1:
        raise SystemExit("Use only one of --pull-only, --push-only, --delete-only")

    if args.pull_only:
        result = pull_from_icloud()
        write_sync_state(result, mode="pull")
    elif args.push_only:
        result = push_to_icloud()
        write_sync_state(result, mode="push")
    elif args.delete_only:
        result = process_deletions()
        write_sync_state(result, mode="delete")
    else:
        result = run_sync()
        write_sync_state(result, mode="full")

    print(_format_result(result))

    if isinstance(result, SyncResult):
        _print_errors(result.pull.errors + result.push.errors + result.delete.errors)
    else:
        _print_errors(result.errors)


if __name__ == "__main__":
    main()
