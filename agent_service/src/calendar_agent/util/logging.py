"""
Logging configuration for the Calendar Agent service.

Provides structured logging setup and logger factory.
"""

import logging
import sys
from typing import Optional

from calendar_agent.config import settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom format string for log messages
    """
    log_level = level or ("DEBUG" if settings.debug else "INFO")
    
    format_str = format_string or (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Example usage:
# from calendar_agent.util.logging import get_logger
# logger = get_logger(__name__)
# logger.info("Processing request")

