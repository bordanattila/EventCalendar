import calendar

from sqlalchemy import String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.utils import is_event_on_date
import datetime


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = 'scheduled_event'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    date: Mapped[str] = mapped_column(String(15), index=True)
    time: Mapped[str] = mapped_column(String(5))
    location: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(String(200))
    recurrence: Mapped[str] = mapped_column(String(10), index=True)
    recurrence_end: Mapped[str] = mapped_column(String(15), nullable=True)

#
# engine = create_engine('sqlite:///calendar.db')
# with engine.connect() as conn:
#     conn.execute(text("ALTER TABLE scheduled_event ADD COLUMN recurrence_end TEXT"))

engine = create_engine('sqlite:///calendar.db', echo=True)

# Create tables
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def save_event_to_db(event_data: dict[str, str]) -> None:
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
    Returns a dictionary of events keyed by date (YYYY-MM-DD) for a given week
    containing the given `date`, starting from Sunday to Saturday.
    """
    # Get Sunday as the first day of the week
    # weekday: Mon=0 ... Sun=6
    sunday = datetime.date.fromisocalendar(year, week_number, 7)
    start_date = sunday
    end_date = start_date + datetime.timedelta(days=7)

    with SessionLocal() as session:
        regular = session.query(Event).filter(
            Event.recurrence == 'None',
            Event.date >= str(start_date),
            Event.date < str(end_date)
        ).all()
        recurring = session.query(Event).filter(Event.recurrence != 'None').all()

    all_events = regular + recurring

    event_dict: dict[str, list[Event]] = {}
    for single_date in (start_date + datetime.timedelta(days=n) for n in range(7)):
        key = str(single_date)
        event_dict[key] = [
            e for e in all_events if is_event_on_date(e, single_date)
        ]

    print("Weekly event dict:", {k: [e.title for e in v] for k, v in event_dict.items()})
    return event_dict


def get_events_for_month(year: int, month: int) -> dict[str, list[Event]]:
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
    Permanently disable recurrence for a recurring event by setting recurrence_end to today.
    Returns True if update succeeded.
    """
    with SessionLocal() as session:
        db_event = session.query(Event).get(event_id)
        if db_event and db_event.recurrence.lower() != "none":
            db_event.recurrence_end = datetime.date.today().strftime('%Y-%m-%d')
            session.commit()
            return True
    return False


def update_event_in_db(event_id: int, updated_data: dict[str, str]) -> None:
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
