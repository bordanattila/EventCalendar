"""
Time parsing and manipulation tools.

These tools help with date/time parsing and recurrence expansion.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
import pytz

from langchain.tools import tool

from calendar_agent.config import settings


WEEKDAY_MAP = {
    "monday": MO, "mon": MO,
    "tuesday": TU, "tue": TU,
    "wednesday": WE, "wed": WE,
    "thursday": TH, "thu": TH,
    "friday": FR, "fri": FR,
    "saturday": SA, "sat": SA,
    "sunday": SU, "sun": SU,
}

WEEKDAY_INDEX = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


@tool
def parse_datetime_tool(
    text: str,
    reference_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse a natural language date/time expression.
    
    Args:
        text: Natural language date/time like "next Tuesday at 3pm", "tomorrow 9am"
        reference_date: Reference date for relative expressions (YYYY-MM-DD format)
    
    Returns:
        Parsed date and time in standard formats
    """
    try:
        # Set reference date
        if reference_date:
            ref = datetime.strptime(reference_date, "%Y-%m-%d")
        else:
            ref = datetime.now(pytz.timezone(settings.default_timezone))
        
        # Parse the text
        parsed = date_parser.parse(text, fuzzy=True, default=ref)
        
        return {
            "success": True,
            "date": parsed.strftime("%Y-%m-%d"),
            "time": parsed.strftime("%H:%M"),
            "datetime": parsed.isoformat(),
            "weekday": parsed.strftime("%A"),
            "original_text": text
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not parse '{text}': {str(e)}",
            "original_text": text
        }


@tool
def get_next_weekday_tool(
    weekday: str,
    start_from: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the next occurrence of a specific weekday.
    
    Args:
        weekday: Day of week (e.g., "Tuesday", "tue")
        start_from: Start date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        The date of the next occurrence of that weekday
    """
    try:
        weekday_lower = weekday.lower()
        if weekday_lower not in WEEKDAY_INDEX:
            return {"success": False, "error": f"Unknown weekday: {weekday}"}
        
        target_index = WEEKDAY_INDEX[weekday_lower]
        
        if start_from:
            start = datetime.strptime(start_from, "%Y-%m-%d").date()
        else:
            start = date.today()
        
        current_index = start.weekday()
        days_ahead = target_index - current_index
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_date = start + timedelta(days=days_ahead)
        
        return {
            "success": True,
            "date": next_date.strftime("%Y-%m-%d"),
            "weekday": next_date.strftime("%A"),
            "days_from_now": days_ahead
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def expand_recurrence_tool(
    start_date: str,
    recurrence: str,
    count: int = 8,
    until: Optional[str] = None
) -> Dict[str, Any]:
    """
    Expand a recurrence rule into a list of dates.
    
    Args:
        start_date: First occurrence in YYYY-MM-DD format
        recurrence: Recurrence pattern (daily, weekly, monthly, yearly)
        count: Number of occurrences to generate
        until: End date in YYYY-MM-DD format (alternative to count)
    
    Returns:
        List of dates when the event occurs
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        dates = [start]
        
        recurrence_lower = recurrence.lower()
        
        # Determine delta based on recurrence
        if recurrence_lower == "daily":
            delta = timedelta(days=1)
        elif recurrence_lower == "weekly":
            delta = timedelta(weeks=1)
        elif recurrence_lower == "monthly":
            delta = relativedelta(months=1)
        elif recurrence_lower == "yearly":
            delta = relativedelta(years=1)
        elif recurrence_lower == "none":
            return {
                "success": True,
                "dates": [start_date],
                "count": 1,
                "recurrence": recurrence
            }
        else:
            return {"success": False, "error": f"Unknown recurrence: {recurrence}"}
        
        # Handle until date
        if until:
            end_date = datetime.strptime(until, "%Y-%m-%d").date()
            current = start
            while len(dates) < 1000:  # Safety limit
                current = current + delta if isinstance(delta, timedelta) else current + delta
                if current > end_date:
                    break
                dates.append(current)
        else:
            # Generate count occurrences
            current = start
            for _ in range(count - 1):
                current = current + delta if isinstance(delta, timedelta) else current + delta
                dates.append(current)
        
        return {
            "success": True,
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "count": len(dates),
            "recurrence": recurrence,
            "start_date": start_date,
            "end_date": dates[-1].strftime("%Y-%m-%d") if dates else start_date
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool  
def get_date_range_tool(
    range_type: str,
    reference_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get start and end dates for common date ranges.
    
    Args:
        range_type: One of "today", "tomorrow", "this_week", "next_week", "this_month", "next_month"
        reference_date: Reference date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Start and end dates for the range
    """
    try:
        if reference_date:
            ref = datetime.strptime(reference_date, "%Y-%m-%d").date()
        else:
            ref = date.today()
        
        range_lower = range_type.lower().replace(" ", "_")
        
        if range_lower == "today":
            start = end = ref
        elif range_lower == "tomorrow":
            start = end = ref + timedelta(days=1)
        elif range_lower == "this_week":
            start = ref - timedelta(days=ref.weekday())  # Monday
            end = start + timedelta(days=6)  # Sunday
        elif range_lower == "next_week":
            start = ref - timedelta(days=ref.weekday()) + timedelta(weeks=1)
            end = start + timedelta(days=6)
        elif range_lower == "this_month":
            start = ref.replace(day=1)
            next_month = start + relativedelta(months=1)
            end = next_month - timedelta(days=1)
        elif range_lower == "next_month":
            start = (ref.replace(day=1) + relativedelta(months=1))
            end = (start + relativedelta(months=1)) - timedelta(days=1)
        else:
            return {"success": False, "error": f"Unknown range type: {range_type}"}
        
        return {
            "success": True,
            "range_type": range_type,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "start_weekday": start.strftime("%A"),
            "end_weekday": end.strftime("%A"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

