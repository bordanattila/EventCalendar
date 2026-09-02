"""
db_manager.py

Handles all interactions with the SQLite database for the Family Calendar app.

Features:
- SQLAlchemy ORM model for `Event`
- Save, update, and stop recurrence on events
- Fetch events for a given week or month, including recurring ones

Author: Attila Bordan
"""
import calendar
import datetime
import sys
import uuid
from pathlib import Path

from sqlalchemy import String, create_engine, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.api_utils import is_event_on_date


# ---------- Database Models ----------
class Base(DeclarativeBase):
    """Declarative base class for SQLAlchemy ORM."""
    pass


class Event(Base):
    """ORM model for scheduled events in the calendar."""
    __tablename__ = 'scheduled_event'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    date: Mapped[str] = mapped_column(String(15), index=True)
    time: Mapped[str] = mapped_column(String(5))
    location: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(String(200))
    recurrence: Mapped[str] = mapped_column(String(10), index=True)
    recurrence_end: Mapped[str] = mapped_column(String(15), nullable=True)
    ical_uid: Mapped[str] = mapped_column(String(255), nullable=True)
    ical_etag: Mapped[str] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str] = mapped_column(String(255), nullable=True)
    event_end_time: Mapped[str] = mapped_column(String(255), nullable=True)


# ---------- Database Initialization ----------

# Local SQLite database engine (always project-root calendar.db)
DB_PATH = PROJECT_ROOT / 'calendar.db'
engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)

# Create all tables based on Base metadata
Base.metadata.create_all(engine)

# Session factory
SessionLocal = sessionmaker(bind=engine)


# ---------- Database Operations ----------

def _default_end_time(start_time: str) -> str | None:
    if not start_time:
        return None
    start = datetime.datetime.strptime(start_time, '%H:%M')
    return (start + datetime.timedelta(hours=1)).strftime('%H:%M')


def save_event_to_db(event_data: dict[str, str]) -> None:
    """
    Saves a new event to the database.

    Args:
        event_data (dict): Dictionary containing title, date, time, location, notes, recurrence, and optionally recurrence_end.
    
    Raises:
        KeyError: If required keys are missing from event_data.
        Exception: If database operation fails.
    """
    # Validate required keys
    required_keys = ['title', 'date', 'time', 'location', 'notes', 'recurrence']
    missing_keys = [key for key in required_keys if key not in event_data]
    if missing_keys:
        raise KeyError(f"Missing required keys in event_data: {missing_keys}")
    
    try:
        with SessionLocal() as session:
            new_event = Event(
                title=event_data['title'],
                date=event_data['date'],
                time=event_data['time'],
                location=event_data['location'],
                notes=event_data['notes'],
                recurrence=event_data['recurrence'],
                recurrence_end=event_data.get('recurrence_end'),  # Optional field
                ical_uid=str(uuid.uuid4()),
                ical_etag=None,
                source="local",
                sync_status="pending_push",
                last_modified=datetime.datetime.now().isoformat(),
                event_end_time=_default_end_time(event_data['time']),
            )
            session.add_all([new_event])
            session.commit()
    except Exception as e:
        print(f"Error saving event to database: {e}")
        raise


def get_events_for_week(year: int, week_number: int) -> dict[str, list[Event]]:
    """
    Returns all events for a specific ISO week of a given year, grouped by date.

    Args:
        year (int): The calendar year.
        week_number (int): The ISO week number.

    Returns:
        dict: Keys are ISO-format dates, values are lists of Event objects.
    
    Raises:
        ValueError: If week_number is invalid.
        Exception: If database operation fails.
    """
    try:
        # Get Sunday as the first day of the week
        # weekday: Mon=0 ... Sun=6
        sunday = datetime.date.fromisocalendar(year, week_number, 7)
        start_date = sunday
        end_date = start_date + datetime.timedelta(days=7)
    except ValueError as e:
        print(f"Error: Invalid week number {week_number} for year {year}: {e}")
        return {}

    try:
        with SessionLocal() as session:
            # Separate regular (non-recurring) and recurring events
            regular = session.query(Event).filter(
                Event.recurrence == 'none',
                Event.date >= str(start_date),
                Event.date < str(end_date),
                Event.sync_status != 'pending_delete'
            ).all()
            recurring = session.query(Event).filter(
                Event.recurrence != 'none',
                Event.sync_status != 'pending_delete'
            ).all()

        all_events = regular + recurring

        # Build dictionary of events per day
        event_dict: dict[str, list[Event]] = {}
        for single_date in (start_date + datetime.timedelta(days=n) for n in range(7)):
            key = str(single_date)
            event_dict[key] = [
                e for e in all_events if is_event_on_date(e, single_date)
            ]

        print("Weekly event dict:", {k: [e.title for e in v] for k, v in event_dict.items()})
        return event_dict
    except Exception as e:
        print(f"Error fetching events for week: {e}")
        return {}


def get_events_for_month(year: int, month: int) -> dict[str, list[Event]]:
    """
    Returns all events for a given month, grouped by date.

    Args:
        year (int): Year of interest.
        month (int): Month of interest.

    Returns:
        dict: Keys are ISO-format dates, values are lists of Event objects.
    
    Raises:
        ValueError: If month is invalid.
        Exception: If database operation fails.
    """
    try:
        _, num_days = calendar.monthrange(year, month)

        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, month + 1, 1)
    except (ValueError, calendar.IllegalMonthError) as e:
        print(f"Error: Invalid month {month} for year {year}: {e}")
        return {}

    try:
        with SessionLocal() as session:
            regular = session.query(Event).filter(
                Event.recurrence == 'none',
                Event.date >= str(start_date),
                Event.date < str(end_date),
                Event.sync_status != 'pending_delete'
            ).all()

            recurring = session.query(Event).filter(
                Event.recurrence != 'none',
                Event.sync_status != 'pending_delete'
            ).all()

        all_events = regular + recurring

        event_dict: dict[str, list[Event]] = {}

        for day in range(1, num_days + 1):
            current_date = datetime.date(year, month, day)
            key = str(current_date)
            event_dict[key] = [e for e in all_events if is_event_on_date(e, current_date)]

        print("Loaded events for", year, month, "→", sum(len(v) for v in event_dict.values()), "total")
        return event_dict
    except Exception as e:
        print(f"Error fetching events for month: {e}")
        return {}


def stop_recurring_event(event_id: int) -> bool:
    """
    Disables future recurrences of an event by setting its recurrence_end to today.

    Args:
        event_id (int): ID of the event to stop recurring.

    Returns:
        bool: True if the update succeeded, False otherwise.
    """
    try:
        with SessionLocal() as session:
            db_event = session.query(Event).get(event_id)
            if db_event and db_event.recurrence.lower() != "none":
                db_event.recurrence_end = datetime.date.today().strftime('%Y-%m-%d')
                db_event.sync_status = 'pending_push'
                db_event.last_modified = datetime.datetime.now().isoformat()
                session.commit()
                return True
        return False
    except Exception as e:
        print(f"Error stopping recurring event {event_id}: {e}")
        return False


def update_event_in_db(event_id: int, updated_data: dict[str, str]) -> None:
    """
    Updates an existing event in the database.

    Args:
        event_id (int): ID of the event to update.
        updated_data (dict): Dictionary containing new title, date, time, location, notes, recurrence, and optionally recurrence_end.
    
    Raises:
        KeyError: If required keys are missing from updated_data.
        Exception: If database operation fails.
    """
    # Validate required keys
    required_keys = ['title', 'date', 'time', 'location', 'notes', 'recurrence']
    missing_keys = [key for key in required_keys if key not in updated_data]
    if missing_keys:
        raise KeyError(f"Missing required keys in updated_data: {missing_keys}")
    
    try:
        with SessionLocal() as session:
            event = session.query(Event).get(event_id)
            if event:
                event.title = updated_data['title']
                event.date = updated_data['date']
                event.time = updated_data['time']
                event.location = updated_data['location']
                event.notes = updated_data['notes']
                event.recurrence = updated_data['recurrence']
                event.sync_status = 'pending_push'
                event.last_modified = datetime.datetime.now().isoformat()
                event.event_end_time = _default_end_time(updated_data['time'])
                # Update recurrence_end if provided
                if 'recurrence_end' in updated_data:
                    event.recurrence_end = updated_data['recurrence_end']
                session.commit()
            else:
                print(f"Warning: Event with ID {event_id} not found for update")
    except Exception as e:
        print(f"Error updating event {event_id}: {e}")
        raise


def delete_event(event_id: int) -> bool:
    """
    Removes selected event from the database.

    Args:
        event_id (int): ID of the event to delete.

    Returns:
        bool: True if the deletion succeeded, False otherwise.
    """
    try:
        with SessionLocal() as session:
            db_event = session.query(Event).get(event_id)
            if db_event:
                db_event.sync_status = 'pending_delete'
                # sync_job will delete the event from the database
                db_event.last_modified = datetime.datetime.now().isoformat()
                session.commit()
                return True
        return False
    except Exception as e:
        print(f"Error deleting event {event_id}: {e}")
        return False
