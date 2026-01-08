"""
Conflict detection and scheduling analysis tools.

These tools help identify scheduling conflicts and find free time.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool

from calendar_agent.db.repo import EventRepository


@tool
def check_conflicts_tool(
    date: str,
    start_time: str,
    end_time: Optional[str] = None,
    exclude_event_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check for scheduling conflicts on a given date and time.
    
    Use this tool when the user wants to:
    - Check if a time slot is available
    - See if an event would conflict with existing events
    - Validate a proposed event time
    
    Args:
        date: Date to check in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format (optional, assumes 1 hour duration)
        exclude_event_id: Event ID to exclude from conflict check (for updates)
    
    Returns:
        Dictionary with has_conflicts boolean and list of conflicting events
    """
    try:
        repo = EventRepository()
        conflicts = repo.check_conflicts(
            start_date=date,
            start_time=start_time,
            end_time=end_time,
            ignore_event_id=exclude_event_id
        )
        
        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "count": len(conflicts),
            "message": f"Found {len(conflicts)} conflicting event(s)" if conflicts else "No conflicts found"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_free_slots_tool(
    date: str,
    min_duration_minutes: int = 30
) -> Dict[str, Any]:
    """
    Get available free time slots for a given date.
    
    Use this tool when the user wants to:
    - Find available time for a new event
    - See when they're free on a specific day
    - Find a slot for a meeting of a specific duration
    
    Args:
        date: Date to check in YYYY-MM-DD format
        min_duration_minutes: Minimum slot duration in minutes
    
    Returns:
        List of free time slots with their durations
    """
    try:
        repo = EventRepository()
        free_slots = repo.get_free_slots(date, min_duration_minutes)
        busy_times = repo.get_busy_times(date)
        
        return {
            "success": True,
            "free_slots": free_slots,
            "busy_times": busy_times,
            "free_count": len(free_slots),
            "busy_count": len(busy_times),
            "message": f"Found {len(free_slots)} free slot(s) of at least {min_duration_minutes} minutes"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def find_crunch_days_tool(
    start_date: str,
    end_date: str,
    threshold_events: int = 4
) -> Dict[str, Any]:
    """
    Find "crunch days" - days with too many scheduled events.
    
    Use this tool when the user asks about:
    - Busy days
    - Crunch days
    - Overloaded schedule
    - Heavy days next week/month
    
    Args:
        start_date: Start of range in YYYY-MM-DD format
        end_date: End of range in YYYY-MM-DD format
        threshold_events: Minimum number of events to consider it a crunch day (default: 4)
    
    Returns:
        List of crunch days with event counts and details
    """
    try:
        repo = EventRepository()
        crunch_days = repo.crunch_days(start_date, end_date, threshold_events)
        
        # Also get total days and events for context
        all_events = repo.list_events(start_date, end_date)
        
        return {
            "success": True,
            "crunch_days": crunch_days,
            "crunch_count": len(crunch_days),
            "threshold": threshold_events,
            "total_events_in_range": len(all_events),
            "message": f"Found {len(crunch_days)} crunch day(s) with {threshold_events}+ events"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_day_summary_tool(date: str) -> Dict[str, Any]:
    """
    Get a summary of a specific day's schedule.
    
    Use this tool when the user wants to:
    - See what's planned for a day
    - Get an overview of their schedule
    - Check how busy a day is
    
    Args:
        date: Date to summarize in YYYY-MM-DD format
    
    Returns:
        Day summary with events, free time, and statistics
    """
    try:
        repo = EventRepository()
        events = repo.get_events_by_date(date)
        busy_times = repo.get_busy_times(date)
        free_slots = repo.get_free_slots(date)
        
        # Calculate statistics
        total_busy_minutes = 0
        for slot in busy_times:
            start = datetime.strptime(slot["start"], "%H:%M")
            end = datetime.strptime(slot["end"], "%H:%M")
            total_busy_minutes += (end - start).seconds // 60
        
        total_free_minutes = sum(slot["duration_minutes"] for slot in free_slots)
        
        return {
            "success": True,
            "date": date,
            "events": events,
            "event_count": len(events),
            "busy_hours": round(total_busy_minutes / 60, 1),
            "free_hours": round(total_free_minutes / 60, 1),
            "free_slots": free_slots,
            "first_event": events[0] if events else None,
            "last_event": events[-1] if events else None,
            "message": f"{len(events)} event(s), {round(total_busy_minutes/60, 1)}h busy, {round(total_free_minutes/60, 1)}h free"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def check_conflicts_for_move_tool(
    event_id: int,
    new_date: str,
    new_time: str
) -> Dict[str, Any]:
    """
    Check if moving an event would create conflicts.
    
    Use this tool when the user wants to:
    - Move an event to a new time
    - Reschedule an event
    - Check if a move is safe
    
    Args:
        event_id: ID of the event to move
        new_date: New date in YYYY-MM-DD format
        new_time: New start time in HH:MM format
    
    Returns:
        Whether the move is safe and any conflicts
    """
    try:
        repo = EventRepository()
        
        # Get the original event
        original = repo.get_event(event_id)
        if not original:
            return {"success": False, "error": f"Event {event_id} not found"}
        
        # Check conflicts at new time (excluding this event)
        conflicts = repo.check_conflicts(
            start_date=new_date,
            start_time=new_time,
            ignore_event_id=event_id
        )
        
        return {
            "success": True,
            "event": original,
            "new_date": new_date,
            "new_time": new_time,
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "safe_to_move": len(conflicts) == 0,
            "message": "Safe to move" if not conflicts else f"Would conflict with {len(conflicts)} event(s)"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
