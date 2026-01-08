"""
Event Repository - Database operations for calendar events.

Provides CRUD operations and queries used by agent tools.
"""

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .session import Event, get_session


class EventRepository:
    """Repository for event database operations."""
    
    def __init__(self, session: Optional[Session] = None):
        """Initialize with optional session."""
        self._session = session
    
    def _get_session(self):
        """Get session, creating one if needed."""
        if self._session:
            return self._session
        return get_session()
    
    # ==================== CREATE ====================
    
    def create_event(
        self,
        title: str,
        date: str,
        time: Optional[str] = None,  # Optional for all-day events
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
                time=time or "",  # Empty string for all-day events
                location=location or "",
                notes=notes or "",
                recurrence=recurrence,
                recurrence_end=recurrence_end,
            )
            session.add(event)
            session.flush()
            event_dict = event.to_dict()
            return event_dict
    
    # ==================== READ ====================
    
    def get_event(self, event_id: int) -> Optional[Dict]:
        """Get a single event by ID."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            return event.to_dict() if event else None
    
    def get_events_by_date(self, target_date: str) -> List[Dict]:
        """Get all events for a specific date."""
        with get_session() as session:
            events = session.query(Event).filter(Event.date == target_date).all()
            return [e.to_dict() for e in events]
    
    def get_events_in_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get all events within a date range (inclusive)."""
        with get_session() as session:
            events = session.query(Event).filter(
                and_(
                    Event.date >= start_date,
                    Event.date <= end_date
                )
            ).order_by(Event.date, Event.time).all()
            return [e.to_dict() for e in events]
    
    def get_all_events(self, limit: int = 100) -> List[Dict]:
        """Get all events (with optional limit)."""
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
        """Search events by title or notes."""
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
    
    # ==================== DELETE ====================
    
    def delete_event(self, event_id: int) -> bool:
        """Delete an event by ID."""
        with get_session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                return False
            session.delete(event)
            return True
    
    def delete_events_by_title(self, title: str, date: Optional[str] = None) -> int:
        """Delete events matching title (and optionally date). Returns count deleted."""
        with get_session() as session:
            query = session.query(Event).filter(Event.title.ilike(f"%{title}%"))
            if date:
                query = query.filter(Event.date == date)
            count = query.count()
            query.delete(synchronize_session=False)
            return count
    
    # ==================== CONFLICT DETECTION ====================
    
    def find_conflicts(
        self,
        date: str,
        start_time: str,
        end_time: Optional[str] = None,
        exclude_event_id: Optional[int] = None
    ) -> List[Dict]:
        """Find events that conflict with a given time slot."""
        with get_session() as session:
            # Get all events on that date
            query = session.query(Event).filter(Event.date == date)
            if exclude_event_id:
                query = query.filter(Event.id != exclude_event_id)
            
            events = query.all()
            conflicts = []
            
            # Parse times for comparison
            new_start = datetime.strptime(start_time, "%H:%M")
            new_end = datetime.strptime(end_time or start_time, "%H:%M") + timedelta(hours=1)
            
            for event in events:
                # Skip all-day events (no time) for time-based conflict check
                if not event.time:
                    continue
                    
                event_start = datetime.strptime(event.time, "%H:%M")
                # Assume 1 hour duration for events
                event_end = event_start + timedelta(hours=1)
                
                # Check for overlap
                if new_start < event_end and new_end > event_start:
                    conflicts.append(event.to_dict())
            
            return conflicts
    
    def get_busy_times(self, date: str) -> List[Dict[str, str]]:
        """Get all busy time slots for a date."""
        with get_session() as session:
            events = session.query(Event).filter(Event.date == date).order_by(Event.time).all()
            busy = []
            for event in events:
                # Skip all-day events (no time)
                if not event.time:
                    continue
                # Assume 1 hour duration for events
                end_time = (
                    datetime.strptime(event.time, "%H:%M") + timedelta(hours=1)
                ).strftime("%H:%M")
                busy.append({
                    "start": event.time,
                    "end": end_time,
                    "title": event.title,
                    "event_id": event.id
                })
            return busy
    
    def get_free_slots(self, date: str, min_duration_minutes: int = 30) -> List[Dict[str, str]]:
        """Get free time slots for a date."""
        busy = self.get_busy_times(date)
        
        # Start at 8 AM, end at 10 PM
        day_start = datetime.strptime("08:00", "%H:%M")
        day_end = datetime.strptime("22:00", "%H:%M")
        
        free_slots = []
        current = day_start
        
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
        if current < day_end:
            gap_minutes = (day_end - current).seconds // 60
            if gap_minutes >= min_duration_minutes:
                free_slots.append({
                    "start": current.strftime("%H:%M"),
                    "end": day_end.strftime("%H:%M"),
                    "duration_minutes": gap_minutes
                })
        
        return free_slots

