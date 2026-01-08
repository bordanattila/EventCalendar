"""
FastAPI application entrypoint for the Calendar Agent service.

This is the main module that creates and configures the FastAPI app.
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from calendar_agent import __version__
from calendar_agent.config import settings
from calendar_agent.api import api_router
from calendar_agent.db.session import init_db
from calendar_agent.util.logging import setup_logging, get_logger


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Initializes resources on startup and cleans up on shutdown.
    """
    # Startup
    logger.info(f"Starting Calendar Agent v{__version__}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"LLM model: {settings.llm_model}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Calendar Agent")


# Create FastAPI application
app = FastAPI(
    title="Calendar Agent API",
    description="""
AI-powered calendar assistant with natural language interface.

## Features

- **Natural Language Commands**: Send messages like "Add soccer every Tuesday at 6pm for 8 weeks"
- **Human-in-the-Loop**: Agent proposes changes, you approve before committing
- **Conflict Detection**: Automatically identifies scheduling overlaps
- **Recurring Events**: Full support for daily, weekly, monthly, and yearly recurrence

## Workflow

1. **POST /chat** - Send a natural language command
2. Review the proposed action plan
3. **POST /commit** - Apply the approved plan

## Example

```bash
# Request changes
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Add soccer every Tuesday at 6pm for 8 weeks"}'

# Review the plan in the response, then commit:
curl -X POST http://localhost:8000/commit \\
  -H "Content-Type: application/json" \\
  -d '{"plan_id": "plan_abc123"}'
```
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Calendar Agent API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


def run():
    """Run the server using uvicorn."""
    uvicorn.run(
        "calendar_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    run()

