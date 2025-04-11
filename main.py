"""
Family Calendar Application
---------------------------
A Python Kivy-based monthly calendar app that displays the current time, day,
and date with weekday headers, interactive month navigation, and styled UI elements.

Created by Attila Bordan.
"""

from kivy.app import App
from UI.calendar_view import Calendar
from kivy.uix.floatlayout import FloatLayout


class CalendarApp(App):
    """Initializes and runs the calendar application."""
    def build(self):
        root = FloatLayout()
        calendar = Calendar()
        root.add_widget(calendar)
        calendar.set_float_root(root)
        return root


if __name__ == '__main__':
    CalendarApp().run()
