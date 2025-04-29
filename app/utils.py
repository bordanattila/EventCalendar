"""
utils.py

Helper functions for date and time formatting used in the Family Calendar app.
"""

import datetime as dt
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex

import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("api_key")


def get_time():
    """
    Returns the current time as a string in HH:MM:SS format.

    Returns:
        str: The current time in ISO 8601 format (e.g., '14:30:25').
    """
    return dt.datetime.now().time().isoformat(timespec='seconds')


def get_date():
    """
    Returns the current date.

    Returns:
        datetime.date: The current date (e.g., 2025-04-04).
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


def create_themed_button(text, theme, on_press=None, bg_override=None, font_override=None, on_release=None):
    """
    Creates a styled button inside a BoxLayout using the given theme.
    Returns the BoxLayout with the themed Button inside.
    """

    box = BoxLayout(
        size_hint=(1, None),
        height=35,
        spacing=5,
        padding=[10, 0],
    )

    with box.canvas.before:
        # Shadow
        Color(0, 0, 0, 0.25)
        shadow = RoundedRectangle(pos=(box.x + 2, box.y - 2), size=box.size, radius=[10])

        # Background fill
        Color(*get_color_from_hex(bg_override or theme['button_color']))
        button_bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[10])

    def update_graphics(*_):
        shadow.pos = (box.x + 2, box.y - 2)
        shadow.size = box.size
        button_bg.pos = box.pos
        button_bg.size = box.size

    box.bind(pos=update_graphics, size=update_graphics)

    button = Button(
        text=text,
        background_normal='',
        background_color=get_color_from_hex(bg_override or theme['button_color']),
        color=get_color_from_hex(theme['text_color']),
        size_hint=(1, 1),
        halign='center',
        valign='middle',
        font_name=font_override if font_override else 'Roboto',
    )

    button.text_size = (None, None)

    if on_press:
        button.bind(on_press=on_press)
    if on_release:
        button.bind(on_release=on_release)

    box.add_widget(button)
    return box


def get_location():
    try:
        response = requests.get('https://ipinfo.io/json')
        data = response.json()
        loc = data.get('loc')
        city = data.get('city')
        lat, lon = map(float, loc.split(','))
        return lat, lon, city
    except Exception as e:
        print("Failed to get location", e)
        return None, None, None


def get_weather(lat, lon):
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}&units=metric&appid={API_KEY}"
        )
        response = requests.get(url)
        data = response.json()
        temp = round(data["main"]["temp"])
        icon = data["weather"][0]["icon"]
        return temp, icon
    except Exception as e:
        print("Failed to get weather:", e)
        return None, None


def is_event_on_date(event, target_date):
    """
    Check if a given event should be shown on current_date based on its recurrence rule
    :param event: an Event object with .date and .recurrence
    :param target_date: datetime.date
    :return: bool
    """
    try:
        # Parse the event's date
        event_date = dt.datetime.strptime(event.date, '%Y-%m-%d').date()
        recurrence = event.recurrence.lower()
        recurrence_end = (
            dt.datetime.strptime(event.recurrence_end, '%Y-%m-%d').date()
            if event.recurrence_end else None
        )

        # If this date is past the recurrence_end, don't show it
        if recurrence_end and target_date > recurrence_end:
            return False

        if recurrence == 'none':
            return event_date == target_date

        elif recurrence == 'daily':
            return target_date >= event_date

        elif recurrence == 'weekly':
            # Check if the weekday matches and the target is after the event date
            return target_date >= event_date and target_date.weekday() == event_date.weekday()

        elif recurrence == 'monthly':
            return target_date.day == event_date.day and target_date >= event_date

        elif recurrence == 'yearly':
            return (
                    target_date.month == event_date.month and
                    target_date.day == event_date.day and
                    target_date >= event_date
            )

        return False  # fallback
    except Exception as e:
        print(f"⚠️ Error checking recurrence: {e}")
        return False

