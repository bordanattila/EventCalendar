"""
Tests for conflict detection functionality.
"""

import pytest
from datetime import date, timedelta


class TestConflictDetection:
    """Test suite for scheduling conflict detection."""
    
    def test_find_conflicts_basic(self, repo):
        """Test basic conflict detection."""
        today = date.today().isoformat()
        
        # Create an existing event
        repo.create_event(
            title="Existing Meeting",
            date=today,
            time="14:00",
            end_time="15:00",
        )
        
        # Check for conflicts at the same time
        conflicts = repo.find_conflicts(today, "14:00", "15:00")
        assert len(conflicts) == 1
        assert conflicts[0]["title"] == "Existing Meeting"
    
    def test_find_conflicts_partial_overlap(self, repo):
        """Test conflict detection with partial time overlap."""
        today = date.today().isoformat()
        
        # Create an existing event
        repo.create_event(
            title="Morning Meeting",
            date=today,
            time="10:00",
            end_time="11:30",
        )
        
        # Check for overlap starting before end
        conflicts = repo.find_conflicts(today, "11:00", "12:00")
        assert len(conflicts) == 1
    
    def test_no_conflicts(self, repo):
        """Test when there are no conflicts."""
        today = date.today().isoformat()
        
        # Create an event
        repo.create_event(
            title="Morning Meeting",
            date=today,
            time="09:00",
            end_time="10:00",
        )
        
        # Check for non-overlapping time
        conflicts = repo.find_conflicts(today, "14:00", "15:00")
        assert len(conflicts) == 0
    
    def test_exclude_event_from_conflicts(self, repo):
        """Test excluding an event from conflict check."""
        today = date.today().isoformat()
        
        # Create an event
        event = repo.create_event(
            title="My Meeting",
            date=today,
            time="14:00",
            end_time="15:00",
        )
        event_id = event["id"]
        
        # Should find conflict without exclusion
        conflicts = repo.find_conflicts(today, "14:00", "15:00")
        assert len(conflicts) == 1
        
        # Should not find conflict when excluding the event
        conflicts = repo.find_conflicts(today, "14:00", "15:00", exclude_event_id=event_id)
        assert len(conflicts) == 0
    
    def test_get_busy_times(self, repo):
        """Test getting busy time slots."""
        today = date.today().isoformat()
        
        # Create multiple events
        repo.create_event(title="Event 1", date=today, time="09:00", end_time="10:00")
        repo.create_event(title="Event 2", date=today, time="14:00", end_time="15:00")
        
        busy = repo.get_busy_times(today)
        assert len(busy) == 2
        assert busy[0]["title"] == "Event 1"
        assert busy[1]["title"] == "Event 2"
    
    def test_get_free_slots(self, repo):
        """Test getting free time slots."""
        today = date.today().isoformat()
        
        # Create events leaving gaps
        repo.create_event(title="Morning", date=today, time="09:00", end_time="10:00")
        repo.create_event(title="Afternoon", date=today, time="14:00", end_time="15:00")
        
        # Should find free slots between events
        free_slots = repo.get_free_slots(today, min_duration_minutes=60)
        
        # Should have slots: 8-9, 10-14, 15-22
        assert len(free_slots) >= 2
        
        # Verify there's a long gap between 10:00 and 14:00
        long_slot = next((s for s in free_slots if s["start"] == "10:00"), None)
        assert long_slot is not None
        assert long_slot["duration_minutes"] >= 240  # 4 hours

