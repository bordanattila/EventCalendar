"""
Conflict detection and scheduling analysis tools.

These tools help identify scheduling conflicts and find free time.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from langchain.tools import tool

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
    
    Args:
        date: Date to check in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format (optional, assumes 1 hour duration)
        exclude_event_id: Event ID to exclude from conflict check (for updates)
    
    Returns:
        List of conflicting events, if any
    """
    try:
        repo = EventRepository()
        conflicts = repo.find_conflicts(
            date=date,
            start_time=start_time,
            end_time=end_time,
            exclude_event_id=exclude_event_id
        )
        
        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "count": len(conflicts)
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
    
    Args:
        date: Date to check in YYYY-MM-DD format
        min_duration_minutes: Minimum slot duration in minutes
    
    Returns:
        List of free time slots
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
            "busy_count": len(busy_times)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def find_crunch_days_tool(
    start_date: str,
    end_date: str,
    threshold_events: int = 5,
    threshold_hours: float = 6.0
) -> Dict[str, Any]:
    """
    Find "crunch days" - days with heavy schedules.
    
    A crunch day is defined as having many events or many hours scheduled.
    
    Args:
        start_date: Start of range in YYYY-MM-DD format
        end_date: End of range in YYYY-MM-DD format
        threshold_events: Minimum events to consider it a crunch day
        threshold_hours: Minimum scheduled hours to consider it a crunch day
    
    Returns:
        List of crunch days with details
    """
    try:
        repo = EventRepository()
        events = repo.get_events_in_range(start_date, end_date)
        
        # Group events by date
        events_by_date: Dict[str, List] = {}
        for event in events:
            date = event["date"]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        crunch_days = []
        normal_days = []
        
        for date, day_events in events_by_date.items():
            # Calculate total scheduled hours
            total_minutes = 0
            for event in day_events:
                start = datetime.strptime(event["time"], "%H:%M")
                end_time = event.get("end_time") or event["time"]
                end = datetime.strptime(end_time, "%H:%M")
                if end <= start:
                    end += timedelta(hours=1)  # Default 1 hour
                total_minutes += (end - start).seconds // 60
            
            total_hours = total_minutes / 60
            event_count = len(day_events)
            
            day_info = {
                "date": date,
                "event_count": event_count,
                "total_hours": round(total_hours, 1),
                "events": [{"title": e["title"], "time": e["time"]} for e in day_events]
            }
            
            if event_count >= threshold_events or total_hours >= threshold_hours:
                crunch_days.append(day_info)
            else:
                normal_days.append(day_info)
        
        return {
            "success": True,
            "crunch_days": sorted(crunch_days, key=lambda x: x["date"]),
            "crunch_count": len(crunch_days),
            "normal_days": sorted(normal_days, key=lambda x: x["date"]),
            "total_days_analyzed": len(events_by_date)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_day_summary_tool(date: str) -> Dict[str, Any]:
    """
    Get a summary of a specific day's schedule.
    
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
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

