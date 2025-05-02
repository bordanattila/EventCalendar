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

from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
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

# ---------- Database Initialization ----------

# Local SQLite database engine
engine = create_engine('sqlite:///calendar.db', echo=True)

# Create all tables based on Base metadata
Base.metadata.create_all(engine)

# Session factory
SessionLocal = sessionmaker(bind=engine)


# ---------- Database Operations ----------
def save_event_to_db(event_data: dict[str, str]) -> None:
    """
    Saves a new event to the database.

    Args:
        event_data (dict): Dictionary containing title, date, time, location, notes, and recurrence.
    """
    with SessionLocal() as session:
        new_event = Event(
            title=event_data['title'],
            date=event_data['date'],
            time=event_data['time'],
            location=event_data['location'],
            notes=event_data['notes'],
            recurrence=event_data['recurrence'],
        )
        session.add_all([new_event])
        session.commit()


def get_events_for_week(year: int, week_number: int) -> dict[str, list[Event]]:
    """
    Returns all events for a specific ISO week of a given year, grouped by date.

    Args:
        year (int): The calendar year.
        week_number (int): The ISO week number.

    Returns:
        dict: Keys are ISO-format dates, values are lists of Event objects.
    """
    # Get Sunday as the first day of the week
    # weekday: Mon=0 ... Sun=6
    sunday = datetime.date.fromisocalendar(year, week_number, 7)
    start_date = sunday
    end_date = start_date + datetime.timedelta(days=7)

    with SessionLocal() as session:
        # Separate regular (non-recurring) and recurring events
        regular = session.query(Event).filter(
            Event.recurrence == 'None',
            Event.date >= str(start_date),
            Event.date < str(end_date)
        ).all()
        recurring = session.query(Event).filter(Event.recurrence != 'None').all()

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


def get_events_for_month(year: int, month: int) -> dict[str, list[Event]]:
    """
    Returns all events for a given month, grouped by date.

    Args:
        year (int): Year of interest.
        month (int): Month of interest.

    Returns:
        dict: Keys are ISO-format dates, values are lists of Event objects.
    """
    _, num_days = calendar.monthrange(year, month)

    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    with SessionLocal() as session:
        regular = session.query(Event).filter(
            Event.recurrence == 'None',
            Event.date >= str(start_date),
            Event.date < str(end_date)
        ).all()

        recurring = session.query(Event).filter(Event.recurrence != 'None').all()

    all_events = regular + recurring

    event_dict: dict[str, list[Event]] = {}

    for day in range(1, num_days + 1):
        current_date = datetime.date(year, month, day)
        key = str(current_date)
        event_dict[key] = [e for e in all_events if is_event_on_date(e, current_date)]

    print("Loaded events for", year, month, "→", sum(len(v) for v in event_dict.values()), "total")
    return event_dict


def stop_recurring_event(event_id: int) -> bool:
    """
    Disables future recurrences of an event by setting its recurrence_end to today.

    Args:
        event_id (int): ID of the event to stop recurring.

    Returns:
        bool: True if the update succeeded, False otherwise.
    """
    with SessionLocal() as session:
        db_event = session.query(Event).get(event_id)
        if db_event and db_event.recurrence.lower() != "none":
            db_event.recurrence_end = datetime.date.today().strftime('%Y-%m-%d')
            session.commit()
            return True
    return False


def update_event_in_db(event_id: int, updated_data: dict[str, str]) -> None:
    """
    Updates an existing event in the database.

    Args:
        event_id (int): ID of the event to update.
        updated_data (dict): Dictionary containing new title, date, time, location, notes, recurrence.
    """
    with SessionLocal() as session:
        event = session.query(Event).get(event_id)
        if event:
            event.title = updated_data['title']
            event.date = updated_data['date']
            event.time = updated_data['time']
            event.location = updated_data['location']
            event.notes = updated_data['notes']
            event.recurrence = updated_data['recurrence']
            session.commit()
