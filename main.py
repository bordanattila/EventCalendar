"""
Family Calendar Application
---------------------------
A Python Kivy-based monthly calendar app that displays the current time, day,
and date with weekday headers, interactive month navigation, and styled UI elements.

Created by Attila Bordan.
"""

from kivy.app import App
from UI.calendar_view import Calendar


class CalendarApp(App):
    """Initializes and runs the calendar application."""
    def build(self):
        return Calendar()


if __name__ == '__main__':
    CalendarApp().run()
