from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
import datetime


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = 'scheduled_event'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    date: Mapped[str] = mapped_column(String(15))
    time: Mapped[str] = mapped_column(String(5))
    location: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(String(200))


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
        stmt = select(Event).where(
            Event.date >= start_date,
            Event.date < end_date,
        )
        events = session.scalars(stmt).all()

    event_dict: dict[str, list[Event]] = {}
    for event in events:
        event_dict.setdefault(event.date, []).append(event)
    print("Events returned for week:")
    for key, value in event_dict.items():
        print(f"{key}: {len(value)} events")

    return event_dict


def get_events_for_month(year: int, month: int) -> dict[str, list[Event]]:
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    with SessionLocal() as session:
        stmt = select(Event).where(
            Event.date >= str(start_date),
            Event.date < str(end_date),
        )
        events = session.scalars(stmt).all()

    event_dict: dict[str, list[Event]] = {}
    for event in events:
        event_dict.setdefault(event.date, []).append(event)

    return event_dict
