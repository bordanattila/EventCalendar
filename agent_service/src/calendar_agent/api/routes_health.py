"""
Health check endpoints.

Provides basic health and readiness checks.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from calendar_agent import __version__


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    service: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    database: bool
    openai: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns service status and version.
    """
    return HealthResponse(
        status="healthy",
        version=__version__,
        service="calendar-agent"
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Verifies database and OpenAI connectivity.
    """
    from calendar_agent.config import settings
    from calendar_agent.db.session import engine
    
    # Check database
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            db_ok = True
    except Exception:
        pass
    
    # Check OpenAI key is configured
    openai_ok = bool(settings.openai_api_key)
    
    return ReadinessResponse(
        ready=db_ok and openai_ok,
        database=db_ok,
        openai=openai_ok
    )

