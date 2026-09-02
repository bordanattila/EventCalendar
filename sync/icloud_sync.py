"""Fetch events from iCloud CalDAV (debug / import preview)."""

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import caldav
import dateutil.tz
from dotenv import load_dotenv

from ical_mapper import ical_to_event, is_cancelled, is_master_event

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_etag(caldav_event) -> str | None:
    props = getattr(caldav_event, "props", None) or {}
    return props.get("{DAV:}getetag") or getattr(caldav_event, "etag", None)


def _get_calendars(principal, calendar_name: str | None, calendar_url: str | None):
    if calendar_url:
        return [principal.calendar(cal_url=calendar_url)]
    if calendar_name:
        calendars = [
            cal for cal in principal.calendars() if cal.get_display_name() == calendar_name
        ]
        if not calendars:
            raise SystemExit(f'No calendar named "{calendar_name}" found')
        if len(calendars) > 1:
            print(
                f'Warning: {len(calendars)} calendars named "{calendar_name}" '
                "— searching all of them"
            )
        return calendars
    return list(principal.calendars())


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch events from iCloud CalDAV")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print all iCal VEVENT properties (for mapping/debugging)",
    )
    parser.add_argument(
        "--masters",
        action="store_true",
        help="Fetch series masters (expand=False) — use for DB import preview",
    )
    args = parser.parse_args()

    apple_id = os.getenv("ICLOUD_APPLE_ID")
    app_password = os.getenv("ICLOUD_APPLE_PASSWORD")
    calendar_name = os.getenv("ICLOUD_CALENDAR_NAME")
    calendar_url = os.getenv("ICLOUD_CALENDAR_URL")
    timezone = os.getenv("DEFAULT_TIMEZONE", "America/New_York")

    if not apple_id or not app_password:
        raise SystemExit(
            "Missing ICLOUD_APPLE_ID or ICLOUD_APPLE_PASSWORD in .env "
            "(use an app-specific password, not your Apple ID password)"
        )

    client = caldav.DAVClient(
        url="https://caldav.icloud.com/",
        username=apple_id,
        password=app_password,
    )
    calendars = _get_calendars(client.principal(), calendar_name, calendar_url)

    tz = dateutil.tz.gettz(timezone)
    start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    expand = not args.masters

    events_found = 0
    for calendar in calendars:
        for caldav_event in calendar.search(
            start=start, end=end, event=True, expand=expand
        ):
            for component in caldav_event.icalendar_instance.walk("vevent"):
                if is_cancelled(component):
                    continue
                if args.masters and not is_master_event(component):
                    continue

                mapped = ical_to_event(component, etag=_get_etag(caldav_event))
                end_display = f"-{mapped['event_end_time']}" if mapped["event_end_time"] else ""
                time_display = mapped["time"] or "all-day"
                recur = ""
                if mapped["recurrence"] != "none":
                    recur = f" [{mapped['recurrence']}"
                    if mapped["recurrence_end"]:
                        recur += f" until {mapped['recurrence_end']}"
                    recur += "]"

                print(
                    f"{mapped['title']} @ {mapped['date']} {time_display}{end_display}{recur}"
                )
                events_found += 1

                if args.verbose:
                    print("  --- mapped ---")
                    for key, value in mapped.items():
                        print(f"  {key}: {value}")
                    print("  --- iCal fields ---")
                    for key in component.keys():
                        print(f"  {key}: {component.get(key)}")
                    etag = _get_etag(caldav_event)
                    if etag:
                        print(f"  (CalDAV ETag): {etag}")
                    print("  --- raw VEVENT ---")
                    raw = component.to_ical().decode().replace("\r\n", "\n")
                    print("\n".join(f"  {line}" for line in raw.split("\n")))
                    print()

    if events_found == 0:
        mode = "master events" if args.masters else "events"
        print(f"No {mode} found for today ({start.date()})")


if __name__ == "__main__":
    main()
