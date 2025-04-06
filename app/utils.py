"""
utils.py

Helper functions for date and time formatting used in the Family Calendar app.
"""

import datetime as DT

def get_time():
    """
    Returns the current time as a string in HH:MM:SS format.

    Returns:
        str: The current time in ISO 8601 format (e.g., '14:30:25').
    """
    return DT.datetime.now().time().isoformat(timespec='seconds')


def get_date():
    """
    Returns the current date.

    Returns:
        datetime.date: The current date (e.g., 2025-04-04).
    """
    return DT.date.today()


def get_day():
    """
    Returns the current day of the week as a string.

    Returns:
        str: Name of the weekday (e.g., 'Monday').
    """
    week_day = DT.date.today().weekday()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[week_day]


def is_dark_mode():
    """
    Determines whether the app should be in dark mode based on the current hour.
    Returns:
        bool: True if it's dark mode hours, False for light mode.
    """
    current_hour = DT.datetime.now().hour
    return not (7 <= current_hour < 20)
