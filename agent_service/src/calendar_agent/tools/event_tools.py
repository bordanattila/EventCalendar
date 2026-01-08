"""
Event management tools for the calendar agent.

These tools handle CRUD operations for calendar events.
"""

from typing import Optional, List, Dict, Any
from langchain.tools import tool

from calendar_agent.db.repo import EventRepository


@tool
def create_event_tool(
    title: str,
    date: str,
    time: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    recurrence: str = "none",
    recurrence_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new calendar event.
    
    Args:
        title: Event title/name (max 50 chars)
        date: Event date in YYYY-MM-DD format
        time: Start time in HH:MM format (24-hour), optional for all-day events
        location: Event location (optional, max 50 chars)
        notes: Additional notes (optional, max 200 chars)
        recurrence: Recurrence pattern - none, daily, weekly, monthly, yearly
        recurrence_end: End date for recurring events in YYYY-MM-DD format
    
    Returns:
        Created event details or error message
    """
    try:
        repo = EventRepository()
        event = repo.create_event(
            title=title,
            date=date,
            time=time,
            location=location,
            notes=notes,
            recurrence=recurrence,
            recurrence_end=recurrence_end,
        )
        return {"success": True, "event": event}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def update_event_tool(
    event_id: int,
    title: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    recurrence: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing calendar event.
    
    Args:
        event_id: ID of the event to update
        title: New title (optional, max 50 chars)
        date: New date in YYYY-MM-DD format (optional)
        time: New start time in HH:MM format (optional)
        location: New location (optional, max 50 chars)
        notes: New notes (optional, max 200 chars)
        recurrence: New recurrence pattern (optional)
    
    Returns:
        Updated event details or error message
    """
    try:
        repo = EventRepository()
        event = repo.update_event(
            event_id=event_id,
            title=title,
            date=date,
            time=time,
            location=location,
            notes=notes,
            recurrence=recurrence,
        )
        if event:
            return {"success": True, "event": event}
        else:
            return {"success": False, "error": f"Event {event_id} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def delete_event_tool(event_id: int) -> Dict[str, Any]:
    """
    Delete a calendar event by ID.
    
    Args:
        event_id: ID of the event to delete
    
    Returns:
        Success status
    """
    try:
        repo = EventRepository()
        success = repo.delete_event(event_id)
        if success:
            return {"success": True, "message": f"Event {event_id} deleted"}
        else:
            return {"success": False, "error": f"Event {event_id} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def list_events_tool(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List calendar events, optionally filtered by date range.
    
    Args:
        start_date: Start of date range in YYYY-MM-DD format (optional)
        end_date: End of date range in YYYY-MM-DD format (optional)
        limit: Maximum number of events to return
    
    Returns:
        List of events
    """
    try:
        repo = EventRepository()
        
        if start_date and end_date:
            events = repo.get_events_in_range(start_date, end_date)
        elif start_date:
            events = repo.get_events_by_date(start_date)
        else:
            events = repo.get_all_events(limit=limit)
        
        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def search_events_tool(query: str) -> Dict[str, Any]:
    """
    Search for events by title, location, or notes.
    
    Args:
        query: Search text to match against event fields
    
    Returns:
        List of matching events
    """
    try:
        repo = EventRepository()
        events = repo.search_events(query)
        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def move_event_tool(
    event_id: int,
    new_date: str,
    new_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Move an event to a new date and optionally new time.
    
    Args:
        event_id: ID of the event to move
        new_date: New date in YYYY-MM-DD format
        new_time: New time in HH:MM format (optional, keeps original if not specified)
    
    Returns:
        Updated event details or error message
    """
    try:
        repo = EventRepository()
        event = repo.move_event(event_id, new_date, new_time)
        if event:
            return {"success": True, "event": event}
        else:
            return {"success": False, "error": f"Event {event_id} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

