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
    """ORM model for calendar events."""
    __tablename__ = "scheduled_event"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    date: Mapped[str] = mapped_column(String(15), index=True)  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(5))  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=True)  # HH:MM (optional)
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    recurrence: Mapped[str] = mapped_column(String(50), default="none", index=True)
    recurrence_end: Mapped[str] = mapped_column(String(15), nullable=True)
    recurrence_rule: Mapped[str] = mapped_column(String(200), nullable=True)  # JSON string for complex rules
    
    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "end_time": self.end_time,
            "location": self.location,
            "notes": self.notes,
            "recurrence": self.recurrence,
            "recurrence_end": self.recurrence_end,
            "recurrence_rule": self.recurrence_rule,
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

