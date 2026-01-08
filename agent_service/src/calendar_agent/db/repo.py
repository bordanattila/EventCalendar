"""
Event Repository - Database operations for calendar events.

Provides CRUD operations and queries used by agent tools.
Matches the logic of the Kivy app's db_manager.py.
"""

import json
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .session import Event, get_session


def is_event_on_date(event: Dict, check_date: date) -> bool:
    """
    Check if an event (including recurring ones) falls on a given date.
    
    Mirrors the logic in app/api_utils.py
    """
    event_date_str = event.get("date", "")
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    
    recurrence = event.get("recurrence", "none").lower()
    
    # Non-recurring event
    if recurrence == "none":
        return event_date == check_date
    
    # Recurring event - check if within range
    if check_date < event_date:
        return False
    
    # Check recurrence_end
    recurrence_end = event.get("recurrence_end")
    if recurrence_end:
        try:
            end_date = datetime.strptime(recurrence_end, "%Y-%m-%d").date()
            if check_date > end_date:
                return False
        except ValueError:
            pass
    
    # Check recurrence pattern
    if recurrence == "daily":
        return True
    elif recurrence == "weekly":
        return event_date.weekday() == check_date.weekday()
    elif recurrence == "monthly":
        return event_date.day == check_date.day
    elif recurrence == "yearly":
        return event_date.month == check_date.month and event_date.day == check_date.day
    
    return False


class EventRepository:
    """Repository for event database operations."""
    
    def __init__(self, session: Optional[Session] = None):
        """Initialize with optional session."""
        self._session = session
    
    # ==================== CREATE ====================
    
    def create_event(
        self,
        title: str,
        date: str,
        time: str,
        location: str = "",
        notes: str = "",
        recurrence: str = "none",
        recurrence_end: Optional[str] = None,
    ) -> Dict:
        """Create a new event."""
        with get_session() as session:
            event = Event(
                title=title,
                date=date,
                time=time,
                location=location or "",
                notes=notes or "",
                recurrence=recurrence,
                recurrence_end=recurrence_end,
            )
            session.add(event)
            session.flush()
            return event.to_dict()
    
    # ==================== READ ====================
    
    def get_event(self, event_id: int) -> Optional[Dict]:
        """Get a single event by ID."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            return event.to_dict() if event else None
    
    def list_events(
        self,
        start_date: str,
        end_date: str,
        include_recurring: bool = True
    ) -> List[Dict]:
        """
        List all events within a date range.
        
        Args:
            start_date: Start of range (YYYY-MM-DD)
            end_date: End of range (YYYY-MM-DD)
            include_recurring: Whether to expand recurring events
        
        Returns:
            List of events, with recurring events expanded to their occurrences
        """
        with get_session() as session:
            # Get non-recurring events in range
            regular = session.query(Event).filter(
                Event.recurrence == "none",
                Event.date >= start_date,
                Event.date <= end_date
            ).all()
            regular_dicts = [e.to_dict() for e in regular]
            
            if not include_recurring:
                return regular_dicts
            
            # Get all recurring events
            recurring = session.query(Event).filter(
                Event.recurrence != "none"
            ).all()
            recurring_dicts = [e.to_dict() for e in recurring]
        
        # Expand recurring events to specific dates
        result = list(regular_dicts)
        
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        current = start
        while current <= end:
            for event in recurring_dicts:
                if is_event_on_date(event, current):
                    # Create an occurrence with the specific date
                    occurrence = dict(event)
                    occurrence["occurrence_date"] = current.isoformat()
                    occurrence["is_recurring_instance"] = True
                    result.append(occurrence)
            current += timedelta(days=1)
        
        # Sort by date and time
        result.sort(key=lambda e: (e.get("occurrence_date", e["date"]), e["time"]))
        return result
    
    def get_events_by_date(self, target_date: str) -> List[Dict]:
        """Get all events for a specific date (including recurring)."""
        return self.list_events(target_date, target_date)
    
    def get_events_in_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get all events within a date range (alias for list_events)."""
        return self.list_events(start_date, end_date)
    
    def get_all_events(self, limit: int = 100) -> List[Dict]:
        """Get all events (raw, without recurring expansion)."""
        with get_session() as session:
            events = session.query(Event).order_by(Event.date, Event.time).limit(limit).all()
            return [e.to_dict() for e in events]
    
    def get_recurring_events(self) -> List[Dict]:
        """Get all recurring events."""
        with get_session() as session:
            events = session.query(Event).filter(
                Event.recurrence != "none"
            ).all()
            return [e.to_dict() for e in events]
    
    def search_events(self, query: str) -> List[Dict]:
        """Search events by title, notes, or location."""
        with get_session() as session:
            search_pattern = f"%{query}%"
            events = session.query(Event).filter(
                or_(
                    Event.title.ilike(search_pattern),
                    Event.notes.ilike(search_pattern),
                    Event.location.ilike(search_pattern)
                )
            ).all()
            return [e.to_dict() for e in events]
    
    # ==================== UPDATE ====================
    
    def update_event(
        self,
        event_id: int,
        title: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        recurrence: Optional[str] = None,
        recurrence_end: Optional[str] = None,
    ) -> Optional[Dict]:
        """Update an existing event (partial update)."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                return None
            
            if title is not None:
                event.title = title
            if date is not None:
                event.date = date
            if time is not None:
                event.time = time
            if location is not None:
                event.location = location
            if notes is not None:
                event.notes = notes
            if recurrence is not None:
                event.recurrence = recurrence
            if recurrence_end is not None:
                event.recurrence_end = recurrence_end
            
            session.flush()
            return event.to_dict()
    
    def move_event(self, event_id: int, new_date: str, new_time: Optional[str] = None) -> Optional[Dict]:
        """Move an event to a new date/time."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                return None
            
            event.date = new_date
            if new_time:
                event.time = new_time
            
            session.flush()
            return event.to_dict()
    
    def stop_recurrence(self, event_id: int, stop_date: Optional[str] = None) -> bool:
        """Stop a recurring event from this date onwards."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event or event.recurrence == "none":
                return False
            
            event.recurrence_end = stop_date or date.today().isoformat()
            session.flush()
            return True
    
    # ==================== DELETE ====================
    
    def delete_event(self, event_id: int) -> bool:
        """Delete an event by ID."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                return False
            session.delete(event)
            return True
    
    # ==================== CONFLICT DETECTION ====================
    
    def check_conflicts(
        self,
        start_date: str,
        start_time: str,
        end_time: Optional[str] = None,
        ignore_event_id: Optional[int] = None,
        duration_minutes: int = 60
    ) -> List[Dict]:
        """
        Check for scheduling conflicts.
        
        Args:
            start_date: Date to check (YYYY-MM-DD)
            start_time: Start time (HH:MM)
            end_time: End time (HH:MM), if None uses duration_minutes
            ignore_event_id: Event ID to exclude from check
            duration_minutes: Default duration if end_time not provided
        
        Returns:
            List of conflicting events
        """
        # Get all events on the date
        events = self.get_events_by_date(start_date)
        
        # Parse new event times
        new_start = datetime.strptime(start_time, "%H:%M")
        if end_time:
            new_end = datetime.strptime(end_time, "%H:%M")
        else:
            new_end = new_start + timedelta(minutes=duration_minutes)
        
        conflicts = []
        for event in events:
            # Skip the event we're updating
            if ignore_event_id and event["id"] == ignore_event_id:
                continue
            
            # Parse event times
            event_start = datetime.strptime(event["time"], "%H:%M")
            # Assume 1 hour duration for events without end time
            event_end = event_start + timedelta(hours=1)
            
            # Check for overlap: A overlaps B if A.start < B.end and A.end > B.start
            if new_start < event_end and new_end > event_start:
                conflicts.append(event)
        
        return conflicts
    
    def get_busy_times(self, target_date: str) -> List[Dict[str, str]]:
        """Get all busy time slots for a date."""
        events = self.get_events_by_date(target_date)
        busy = []
        
        for event in events:
            start = datetime.strptime(event["time"], "%H:%M")
            # Assume 1 hour duration
            end = start + timedelta(hours=1)
            busy.append({
                "start": event["time"],
                "end": end.strftime("%H:%M"),
                "title": event["title"],
                "event_id": event["id"]
            })
        
        # Sort by start time
        busy.sort(key=lambda x: x["start"])
        return busy
    
    def get_free_slots(
        self,
        target_date: str,
        min_duration_minutes: int = 30,
        day_start: str = "08:00",
        day_end: str = "22:00"
    ) -> List[Dict[str, Any]]:
        """Get free time slots for a date."""
        busy = self.get_busy_times(target_date)
        
        day_start_dt = datetime.strptime(day_start, "%H:%M")
        day_end_dt = datetime.strptime(day_end, "%H:%M")
        
        free_slots = []
        current = day_start_dt
        
        for slot in busy:
            slot_start = datetime.strptime(slot["start"], "%H:%M")
            if current < slot_start:
                gap_minutes = (slot_start - current).seconds // 60
                if gap_minutes >= min_duration_minutes:
                    free_slots.append({
                        "start": current.strftime("%H:%M"),
                        "end": slot_start.strftime("%H:%M"),
                        "duration_minutes": gap_minutes
                    })
            slot_end = datetime.strptime(slot["end"], "%H:%M")
            current = max(current, slot_end)
        
        # Check remaining time until end of day
        if current < day_end_dt:
            gap_minutes = (day_end_dt - current).seconds // 60
            if gap_minutes >= min_duration_minutes:
                free_slots.append({
                    "start": current.strftime("%H:%M"),
                    "end": day_end_dt.strftime("%H:%M"),
                    "duration_minutes": gap_minutes
                })
        
        return free_slots
    
    def crunch_days(
        self,
        start_date: str,
        end_date: str,
        threshold_events: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Find "crunch days" - days with too many events.
        
        Args:
            start_date: Start of range (YYYY-MM-DD)
            end_date: End of range (YYYY-MM-DD)
            threshold_events: Min events to consider "crunch"
        
        Returns:
            List of crunch days with event counts
        """
        events = self.list_events(start_date, end_date)
        
        # Group by date
        events_by_date: Dict[str, List] = {}
        for event in events:
            event_date = event.get("occurrence_date", event["date"])
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)
        
        crunch_days = []
        for event_date, day_events in events_by_date.items():
            if len(day_events) >= threshold_events:
                crunch_days.append({
                    "date": event_date,
                    "event_count": len(day_events),
                    "events": [
                        {"title": e["title"], "time": e["time"]}
                        for e in day_events
                    ]
                })
        
        return sorted(crunch_days, key=lambda x: x["date"])
