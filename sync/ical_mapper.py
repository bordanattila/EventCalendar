"""Convert between iCal VEVENT components and EventCalendar DB dicts."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import dateutil.tz
from icalendar import Calendar, Event as ICalEvent

_FREQ_TO_RECURRENCE = {
    "DAILY": "daily",
    "WEEKLY": "weekly",
    "MONTHLY": "monthly",
    "YEARLY": "yearly",
}

_RECURRENCE_TO_FREQ = {value: key for key, value in _FREQ_TO_RECURRENCE.items()}


def _parse_rrule(vevent) -> tuple[str, str | None]:
    """Map iCal RRULE to (recurrence, recurrence_end)."""
    rrule = vevent.get("rrule")
    if not rrule:
        return "none", None

    freq_raw = rrule.get("FREQ", "NONE")
    freq = freq_raw[0] if isinstance(freq_raw, list) else freq_raw
    recurrence = _FREQ_TO_RECURRENCE.get(str(freq).upper(), "none")

    until_raw = rrule.get("UNTIL")
    if not until_raw:
        return recurrence, None

    until_val = until_raw[0] if isinstance(until_raw, list) else until_raw
    if isinstance(until_val, datetime):
        return recurrence, until_val.date().strftime("%Y-%m-%d")
    if isinstance(until_val, date):
        return recurrence, until_val.strftime("%Y-%m-%d")

    until_str = str(until_val)
    if len(until_str) >= 8 and until_str.isdigit():
        return recurrence, f"{until_str[:4]}-{until_str[4:6]}-{until_str[6:8]}"
    return recurrence, None


def _parse_dtstart_dtend(vevent) -> tuple[str, str, str | None]:
    """
    Parse DTSTART/DTEND into (date, time, event_end_time).

    All-day events use DATE values: time="" and event_end_time=None.
    DTEND for all-day events is exclusive and is not stored as end time.
    """
    dtstart = vevent.get("dtstart")
    if not dtstart:
        raise ValueError("VEVENT missing DTSTART")

    start_val = dtstart.dt
    end_val = vevent.get("dtend")
    end_val = end_val.dt if end_val else None

    if isinstance(start_val, datetime):
        date_str = start_val.strftime("%Y-%m-%d")
        time_str = start_val.strftime("%H:%M")
        event_end_time = end_val.strftime("%H:%M") if isinstance(end_val, datetime) else None
        return date_str, time_str, event_end_time

    if isinstance(start_val, date):
        return start_val.strftime("%Y-%m-%d"), "", None

    raise ValueError(f"Unsupported DTSTART type: {type(start_val)!r}")


def ical_to_event(vevent, etag: str | None = None) -> dict[str, Any]:
    """
    Convert a parsed iCal VEVENT component to a dict matching scheduled_event columns.

    Pass master events (expand=False) for DB import so RRULE is preserved.
    Expanded instances (RECURRENCE-ID set) map occurrence date/time but recurrence="none".
    """
    date_str, time_str, event_end_time = _parse_dtstart_dtend(vevent)
    recurrence, recurrence_end = _parse_rrule(vevent)

    title = str(vevent.get("summary") or "").strip() or "(no title)"
    location = str(vevent.get("location") or "").strip()
    notes = str(vevent.get("description") or "").strip()

    uid = vevent.get("uid")
    if not uid:
        raise ValueError("VEVENT missing UID")

    lm = vevent.get("last-modified")
    last_modified = lm.dt.isoformat() if lm else None

    return {
        "title": title[:50],
        "date": date_str,
        "time": time_str,
        "location": location[:50],
        "notes": notes[:200],
        "recurrence": recurrence,
        "recurrence_end": recurrence_end,
        "event_end_time": event_end_time,
        "ical_uid": str(uid),
        "ical_etag": etag,
        "source": "icloud",
        "sync_status": "synced",
        "last_modified": last_modified,
    }


def is_master_event(vevent) -> bool:
    """True if this VEVENT is a series master (safe to import into DB)."""
    return vevent.get("recurrence-id") is None


def is_cancelled(vevent) -> bool:
    status = vevent.get("status")
    return status is not None and str(status).upper() == "CANCELLED"


def _default_end_time(start_time: str) -> str:
    start = datetime.strptime(start_time, "%H:%M")
    return (start + timedelta(hours=1)).strftime("%H:%M")


def event_to_ical(event, timezone: str = "America/New_York") -> str:
    """
    Convert a DB Event (ORM object or dict-like row) to an iCal VCALENDAR string.

    Used by push sync to create/update events on iCloud.
    """
    title = event.title
    date_str = event.date
    time_str = event.time or ""
    location = event.location or ""
    notes = event.notes or ""
    recurrence = (event.recurrence or "none").lower()
    recurrence_end = event.recurrence_end
    uid = event.ical_uid
    event_end_time = event.event_end_time

    if not uid:
        raise ValueError("Event missing ical_uid — cannot push to iCloud")

    tz = dateutil.tz.gettz(timezone)
    if tz is None:
        raise ValueError(f"Unknown timezone: {timezone}")

    cal = Calendar()
    cal.add("prodid", "-//EventCalendar//sync//EN")
    cal.add("version", "2.0")

    ve = ICalEvent()
    ve.add("summary", title)
    ve.add("uid", uid)

    if location:
        ve.add("location", location)
    if notes:
        ve.add("description", notes)

    if time_str:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        ve.add("dtstart", start_dt)
        end_time = event_end_time or _default_end_time(time_str)
        end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        ve.add("dtend", end_dt)
    else:
        start_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        ve.add("dtstart", start_date)
        ve.add("dtend", start_date + timedelta(days=1))

    freq = _RECURRENCE_TO_FREQ.get(recurrence)
    if freq:
        rrule: dict[str, Any] = {"FREQ": freq}
        if recurrence_end:
            until = datetime.strptime(recurrence_end, "%Y-%m-%d").date()
            rrule["UNTIL"] = until
        ve.add("rrule", rrule)

    now = datetime.now(tz)
    ve.add("dtstamp", now)
    if event.last_modified:
        try:
            ve.add("last-modified", datetime.fromisoformat(event.last_modified))
        except ValueError:
            ve.add("last-modified", now)
    else:
        ve.add("last-modified", now)

    cal.add_component(ve)
    return cal.to_ical().decode()
