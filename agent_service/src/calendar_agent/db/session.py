"""
Database session and engine configuration.

Provides SQLAlchemy engine and session management.
Uses the SAME database and model as the Kivy calendar app.
"""

import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column

from calendar_agent.config import settings


def get_database_url() -> str:
    """
    Get the database URL, pointing to the same SQLite file as the Kivy app.
    
    For local development:
    - If DATABASE_URL is set, use that
    - Otherwise, look for calendar.db in common locations:
      1. agent_service/var/calendar.db (copy for agent testing)
      2. ../../calendar.db (the Pi app's database at project root)
    """
    if settings.database_url and not settings.database_url.startswith("sqlite:///./"):
        return settings.database_url
    
    # Check for local copy in var/
    agent_root = Path(__file__).parent.parent.parent.parent
    var_db = agent_root / "var" / "calendar.db"
    if var_db.exists():
        return f"sqlite:///{var_db.absolute()}"
    
    # Check for main app's database at project root
    project_root = agent_root.parent
    main_db = project_root / "calendar.db"
    if main_db.exists():
        return f"sqlite:///{main_db.absolute()}"
    
    # Fall back to creating in var/
    var_db.parent.mkdir(exist_ok=True)
    return f"sqlite:///{var_db.absolute()}"


# Create engine pointing to the app's database
DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
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
    time: Mapped[str] = mapped_column(String(5))  # HH:MM
    location: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(String(200))
    recurrence: Mapped[str] = mapped_column(String(10), index=True)  # none, daily, weekly, monthly
    recurrence_end: Mapped[str] = mapped_column(String(15), nullable=True)
    
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


def get_db_info() -> dict:
    """Get database connection info (for debugging)."""
    return {
        "url": DATABASE_URL,
        "exists": Path(DATABASE_URL.replace("sqlite:///", "")).exists() if "sqlite" in DATABASE_URL else None,
    }
