"""
Pytest configuration and fixtures for Calendar Agent tests.
"""

import pytest
import os
from datetime import date, timedelta

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_calendar.db"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["DEBUG"] = "true"

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_client():
    """Create test client for the FastAPI app."""
    from calendar_agent.main import app
    from calendar_agent.db.session import init_db, engine, Base
    
    # Create test database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_events():
    """Sample events for testing."""
    today = date.today()
    return [
        {
            "title": "Team Standup",
            "date": today.isoformat(),
            "time": "09:00",
            "end_time": "09:30",
            "recurrence": "daily",
        },
        {
            "title": "Project Review",
            "date": today.isoformat(),
            "time": "14:00",
            "end_time": "15:00",
            "recurrence": "weekly",
        },
        {
            "title": "Dentist Appointment",
            "date": (today + timedelta(days=3)).isoformat(),
            "time": "10:00",
            "end_time": "11:00",
            "recurrence": "none",
        },
    ]


@pytest.fixture
def repo():
    """Get EventRepository for testing."""
    from calendar_agent.db.repo import EventRepository
    from calendar_agent.db.session import Base, engine
    
    # Ensure clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    return EventRepository()

