"""
utils.py

Helper functions for date and time formatting used in the Family Calendar app.
"""

import datetime as dt
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex


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


def create_themed_button(text, theme, on_press=None, bg_override=None, font_override=None):
    """
    Creates a styled button inside a BoxLayout using the given theme.
    Returns the BoxLayout with the themed Button inside.
    """

    box = BoxLayout(
        size_hint=(1, 1),
        height=50,
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

    box.add_widget(button)
    return box
