"""
Tests for recurrence handling functionality.
"""

import pytest
from datetime import date, timedelta


class TestRecurrenceExpansion:
    """Test suite for recurrence rule expansion."""
    
    def test_expand_daily_recurrence(self):
        """Test expanding daily recurrence."""
        from calendar_agent.tools.time_tools import expand_recurrence_tool
        
        start = date.today().isoformat()
        result = expand_recurrence_tool.invoke({
            "start_date": start,
            "recurrence": "daily",
            "count": 5
        })
        
        assert result["success"] is True
        assert result["count"] == 5
        assert len(result["dates"]) == 5
    
    def test_expand_weekly_recurrence(self):
        """Test expanding weekly recurrence."""
        from calendar_agent.tools.time_tools import expand_recurrence_tool
        
        start = date.today().isoformat()
        result = expand_recurrence_tool.invoke({
            "start_date": start,
            "recurrence": "weekly",
            "count": 8
        })
        
        assert result["success"] is True
        assert result["count"] == 8
        
        # Verify 7-day gaps between dates
        dates = result["dates"]
        for i in range(1, len(dates)):
            d1 = date.fromisoformat(dates[i-1])
            d2 = date.fromisoformat(dates[i])
            assert (d2 - d1).days == 7
    
    def test_expand_monthly_recurrence(self):
        """Test expanding monthly recurrence."""
        from calendar_agent.tools.time_tools import expand_recurrence_tool
        
        start = "2025-01-15"
        result = expand_recurrence_tool.invoke({
            "start_date": start,
            "recurrence": "monthly",
            "count": 3
        })
        
        assert result["success"] is True
        assert result["count"] == 3
        assert result["dates"] == ["2025-01-15", "2025-02-15", "2025-03-15"]
    
    def test_expand_recurrence_with_until(self):
        """Test expanding recurrence with end date."""
        from calendar_agent.tools.time_tools import expand_recurrence_tool
        
        result = expand_recurrence_tool.invoke({
            "start_date": "2025-01-01",
            "recurrence": "weekly",
            "until": "2025-01-22"
        })
        
        assert result["success"] is True
        assert result["count"] == 4  # Jan 1, 8, 15, 22
    
    def test_expand_none_recurrence(self):
        """Test 'none' recurrence returns single date."""
        from calendar_agent.tools.time_tools import expand_recurrence_tool
        
        result = expand_recurrence_tool.invoke({
            "start_date": "2025-01-15",
            "recurrence": "none",
            "count": 5
        })
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["dates"] == ["2025-01-15"]


class TestNextWeekday:
    """Test suite for next weekday calculation."""
    
    def test_get_next_tuesday(self):
        """Test getting next Tuesday."""
        from calendar_agent.tools.time_tools import get_next_weekday_tool
        
        result = get_next_weekday_tool.invoke({"weekday": "Tuesday"})
        
        assert result["success"] is True
        assert result["weekday"] == "Tuesday"
        assert "date" in result
    
    def test_get_next_weekday_abbreviation(self):
        """Test using weekday abbreviations."""
        from calendar_agent.tools.time_tools import get_next_weekday_tool
        
        result = get_next_weekday_tool.invoke({"weekday": "tue"})
        
        assert result["success"] is True
        assert result["weekday"] == "Tuesday"
    
    def test_invalid_weekday(self):
        """Test handling invalid weekday."""
        from calendar_agent.tools.time_tools import get_next_weekday_tool
        
        result = get_next_weekday_tool.invoke({"weekday": "Notaday"})
        
        assert result["success"] is False
        assert "error" in result


class TestDateRange:
    """Test suite for date range calculation."""
    
    def test_this_week_range(self):
        """Test getting this week's date range."""
        from calendar_agent.tools.time_tools import get_date_range_tool
        
        result = get_date_range_tool.invoke({"range_type": "this_week"})
        
        assert result["success"] is True
        assert "start_date" in result
        assert "end_date" in result
        assert result["start_weekday"] == "Monday"
        assert result["end_weekday"] == "Sunday"
    
    def test_next_week_range(self):
        """Test getting next week's date range."""
        from calendar_agent.tools.time_tools import get_date_range_tool
        
        result = get_date_range_tool.invoke({"range_type": "next_week"})
        
        assert result["success"] is True
        
        # Next week should start after this week
        this_week = get_date_range_tool.invoke({"range_type": "this_week"})
        assert result["start_date"] > this_week["end_date"]
    
    def test_this_month_range(self):
        """Test getting this month's date range."""
        from calendar_agent.tools.time_tools import get_date_range_tool
        
        result = get_date_range_tool.invoke({"range_type": "this_month"})
        
        assert result["success"] is True
        # Start should be first of month
        assert result["start_date"].endswith("-01")

