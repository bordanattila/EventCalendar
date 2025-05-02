"""
api_utils.py

Handles external API interactions and logic for determining
event recurrence in the Family Calendar app.

Includes:
- IP-based geolocation
- Weather fetching via OpenWeatherMap
- Recurrence-based event matching

Author: Attila Bordan
"""

import datetime as dt
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('api_key')
token = os.getenv('TOKEN')


def get_location():
    """
    Attempts to retrieve the user's geographical location using their IP address.

    Returns:
        tuple: (latitude: float, longitude: float, city: str) or (None, None, None) on failure.
    """
    try:
        response = requests.get(f"https://ipinfo.io/json?token={token}")
        data = response.json()
        loc = data.get('loc')
        city = data.get('city')
        lat, lon = map(float, loc.split(','))
        return lat, lon, city
    except Exception as e:
        print("Failed to get location", e)
        return None, None, None


def get_weather(lat, lon):
    """
    Retrieves current temperature and weather icon from OpenWeatherMap API.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        tuple: (temperature: int, icon_code: str) or (None, None) on failure
    """
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
    Determines if an event should appear on a given date,
    including logic for handling recurrence rules.

    Args:
        event: An object with `.date`, `.recurrence`, and optionally `.recurrence_end`
        target_date (datetime.date): The day to evaluate

    Returns:
        bool: True if the event occurs on the target date.
    """
    try:
        event_date = dt.datetime.strptime(event.date, '%Y-%m-%d').date()
        recurrence = event.recurrence.lower()
        recurrence_end = (
            dt.datetime.strptime(event.recurrence_end, '%Y-%m-%d').date()
            if event.recurrence_end else None
        )

        if recurrence_end and target_date > recurrence_end:
            return False

        if recurrence == 'none':
            return event_date == target_date
        elif recurrence == 'daily':
            return target_date >= event_date
        elif recurrence == 'weekly':
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
