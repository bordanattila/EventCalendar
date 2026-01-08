"""API routes for the Calendar Agent service."""

from fastapi import APIRouter

from .routes_health import router as health_router
from .routes_chat import router as chat_router
from .routes_commit import router as commit_router
from .routes_events import router as events_router


# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(commit_router, prefix="/commit", tags=["Commit"])
api_router.include_router(events_router, prefix="/events", tags=["Events"])

__all__ = ["api_router"]

