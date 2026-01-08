"""
Events CRUD endpoints for debugging and direct manipulation.

These endpoints bypass the AI agent for direct database access.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from calendar_agent.agent.schemas import EventCreate, EventUpdate, EventResponse
from calendar_agent.db.repo import EventRepository


router = APIRouter()


def get_repo() -> EventRepository:
    """Get repository instance."""
    return EventRepository()


@router.get("", response_model=List[dict])
async def list_events(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum events to return"),
):
    """
    List all events, optionally filtered by date range.
    
    ## Examples
    
    - Get all events: `GET /events`
    - Get events in range: `GET /events?start_date=2025-01-01&end_date=2025-01-31`
    - Get events on specific date: `GET /events?start_date=2025-01-15&end_date=2025-01-15`
    """
    repo = get_repo()
    
    if start_date and end_date:
        events = repo.get_events_in_range(start_date, end_date)
    elif start_date:
        events = repo.get_events_by_date(start_date)
    else:
        events = repo.get_all_events(limit=limit)
    
    return events


@router.get("/{event_id}", response_model=dict)
async def get_event(event_id: int):
    """
    Get a single event by ID.
    """
    repo = get_repo()
    event = repo.get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    return event


@router.post("", response_model=dict, status_code=201)
async def create_event(event: EventCreate):
    """
    Create a new event directly (bypasses AI agent).
    
    ## Example Request
    
    ```json
    {
        "title": "Team Meeting",
        "date": "2025-01-15",
        "time": "14:00",
        "end_time": "15:00",
        "location": "Conference Room A",
        "recurrence": "weekly"
    }
    ```
    """
    repo = get_repo()
    
    try:
        result = repo.create_event(
            title=event.title,
            date=event.date,
            time=event.time,
            end_time=event.end_time,
            location=event.location,
            notes=event.notes,
            recurrence=event.recurrence,
            recurrence_end=event.recurrence_end,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{event_id}", response_model=dict)
async def update_event(event_id: int, event: EventUpdate):
    """
    Update an existing event.
    
    Only fields provided will be updated.
    """
    repo = get_repo()
    
    # Build update dict with only provided fields
    update_data = {}
    if event.title is not None:
        update_data["title"] = event.title
    if event.date is not None:
        update_data["date"] = event.date
    if event.time is not None:
        update_data["time"] = event.time
    if event.end_time is not None:
        update_data["end_time"] = event.end_time
    if event.location is not None:
        update_data["location"] = event.location
    if event.notes is not None:
        update_data["notes"] = event.notes
    if event.recurrence is not None:
        update_data["recurrence"] = event.recurrence
    if event.recurrence_end is not None:
        update_data["recurrence_end"] = event.recurrence_end
    
    result = repo.update_event(event_id, **update_data)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    return result


@router.delete("/{event_id}")
async def delete_event(event_id: int):
    """
    Delete an event by ID.
    """
    repo = get_repo()
    success = repo.delete_event(event_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    return {"success": True, "message": f"Event {event_id} deleted"}


@router.get("/search/{query}", response_model=List[dict])
async def search_events(query: str):
    """
    Search events by title, location, or notes.
    
    ## Example
    
    `GET /events/search/meeting`
    """
    repo = get_repo()
    events = repo.search_events(query)
    return events


@router.get("/conflicts/{date}", response_model=dict)
async def check_conflicts(
    date: str,
    start_time: str = Query(..., description="Start time (HH:MM)"),
    end_time: Optional[str] = Query(None, description="End time (HH:MM)"),
):
    """
    Check for scheduling conflicts on a specific date and time.
    
    ## Example
    
    `GET /events/conflicts/2025-01-15?start_time=14:00&end_time=15:00`
    """
    repo = get_repo()
    conflicts = repo.find_conflicts(date, start_time, end_time)
    
    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": conflicts,
        "count": len(conflicts)
    }


@router.get("/free-slots/{date}", response_model=dict)
async def get_free_slots(
    date: str,
    min_duration: int = Query(30, description="Minimum slot duration in minutes"),
):
    """
    Get available free time slots for a specific date.
    
    ## Example
    
    `GET /events/free-slots/2025-01-15?min_duration=60`
    """
    repo = get_repo()
    free_slots = repo.get_free_slots(date, min_duration)
    busy_times = repo.get_busy_times(date)
    
    return {
        "date": date,
        "free_slots": free_slots,
        "busy_times": busy_times
    }

