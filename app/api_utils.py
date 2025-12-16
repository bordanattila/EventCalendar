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
        response = requests.get(f"https://ipinfo.io/json?token={token}", timeout=5)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        loc = data.get('loc')
        city = data.get('city')
        
        if not loc:
            print("Failed to get location: 'loc' field missing from response")
            return None, None, None
        
        try:
            lat, lon = map(float, loc.split(','))
            return lat, lon, city
        except (ValueError, AttributeError) as e:
            print(f"Failed to parse location data '{loc}': {e}")
            return None, None, None
    except requests.exceptions.RequestException as e:
        print(f"Failed to get location (network error): {e}")
        return None, None, None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Failed to get location (data error): {e}")
        return None, None, None
    except Exception as e:
        print(f"Failed to get location (unexpected error): {e}")
        return None, None, None


def get_weather(lat, lon):
    """
    Retrieves current temperature and weather icon from OpenWeatherMap API.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        tuple: (temperature: int, fahrenheit: int, icon_code: str) or (None, None, None) on failure
    """
    if lat is None or lon is None:
        print("Failed to get weather: Invalid coordinates")
        return None, None, None
    
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}&units=metric&appid={API_KEY}"
        )
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        
        # Validate response structure
        if "main" not in data or "temp" not in data["main"]:
            print("Failed to get weather: Invalid response structure (missing 'main.temp')")
            return None, None, None
        
        if "weather" not in data or not data["weather"] or "icon" not in data["weather"][0]:
            print("Failed to get weather: Invalid response structure (missing 'weather[0].icon')")
            return None, None, None
        
        celsius = round(data["main"]["temp"])
        fahrenheit = round((celsius * (9/5)) + 32)
        icon = data["weather"][0]["icon"]
        return celsius, fahrenheit, icon
    except requests.exceptions.RequestException as e:
        print(f"Failed to get weather (network error): {e}")
        return None, None, None
    except (KeyError, ValueError, TypeError, IndexError) as e:
        print(f"Failed to get weather (data error): {e}")
        return None, None, None
    except Exception as e:
        print(f"Failed to get weather (unexpected error): {e}")
        return None, None, None


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
        
        # Safely parse recurrence_end with validation
        recurrence_end = None
        if event.recurrence_end:
            try:
                recurrence_end = dt.datetime.strptime(event.recurrence_end, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                print(f"⚠️ Warning: Invalid recurrence_end format '{event.recurrence_end}': {e}")
                recurrence_end = None

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
