"""
utils.py

Provides utility functions for working with the current time, date,
and determining display mode (light vs. dark) for the Family Calendar app.
"""

import datetime as dt


def get_time():
    """
    Returns the current time as a string in HH:MM:SS format.

    Returns:
        str: The current time in ISO 8601 format (e.g., '14:30:25').
    """
    return dt.datetime.now().time().isoformat(timespec='seconds')


def get_date():
    """
    Returns the current date in a human-readable format.

    Returns:
        str: Current month and year (e.g., 'April 2025').
    """
    return dt.date.today().strftime('%B %Y')


def get_day():
    """
    Returns the current day of the week as a string.

    Returns:
        str: Name of the weekday (e.g., 'Monday').
    """
    week_day = dt.date.today().weekday()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[week_day]


def is_dark_mode():
    """
    Determines whether the app should be in dark mode based on the current hour.
    Returns:
        bool: True if it's dark mode hours, False for light mode.
    """
    current_hour = dt.datetime.now().hour
    return not (7 <= current_hour < 20)
