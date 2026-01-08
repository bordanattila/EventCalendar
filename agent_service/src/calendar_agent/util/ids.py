"""
ID generation utilities.

Provides functions for generating unique identifiers.
"""

import uuid
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID (e.g., "plan", "event")
    
    Returns:
        Unique identifier string
    """
    unique_part = uuid.uuid4().hex[:12]
    if prefix:
        return f"{prefix}_{unique_part}"
    return unique_part


def generate_timestamp_id(prefix: str = "") -> str:
    """
    Generate a timestamp-based ID.
    
    Useful for IDs that should be chronologically sortable.
    
    Args:
        prefix: Optional prefix for the ID
    
    Returns:
        Timestamp-based identifier string
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:6]
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"

