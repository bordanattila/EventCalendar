"""
Database session and engine configuration.

Provides SQLAlchemy engine and session management.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column

from calendar_agent.config import settings


# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Event(Base):
    """
    ORM model for calendar events.
    
    MUST match the Kivy app's Event model in storage/db_manager.py:
    - Table: scheduled_event
    - Fields: id, title, date, time, location, notes, recurrence, recurrence_end
    """
    __tablename__ = "scheduled_event"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    date: Mapped[str] = mapped_column(String(15), index=True)  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(5))  # HH:MM or empty for all-day
    location: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(String(200))
    recurrence: Mapped[str] = mapped_column(String(10), index=True)  # none, daily, weekly, monthly
    recurrence_end: Mapped[str] = mapped_column(String(15), nullable=True)
    ical_uid: Mapped[str] = mapped_column(String(255), nullable=True)
    ical_etag: Mapped[str] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str] = mapped_column(String(255), nullable=True)
    event_end_time: Mapped[str] = mapped_column(String(255), nullable=True)
    
    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "notes": self.notes,
            "recurrence": self.recurrence,
            "recurrence_end": self.recurrence_end,
            "ical_uid": self.ical_uid,
            "ical_etag": self.ical_etag,
            "source": self.source,
            "sync_status": self.sync_status,
            "last_modified": self.last_modified,
            "event_end_time": self.event_end_time,
        }


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Session:
    """Get a database session (for FastAPI dependency injection)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

