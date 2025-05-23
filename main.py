"""
Family Calendar Application
---------------------------
A Python Kivy-based monthly calendar app designed to run on a touchscreen interface
(e.g., Raspberry Pi). It features a real-time clock, monthly/weekly calendar views,
theme customization, and interactive event management.

Modules:
- Kivy for GUI rendering and layout
- Custom UI component: Calendar (from UI package)

Author: Attila Bordan
"""

from kivy.app import App
from UI.calendar_view import Calendar
from kivy.uix.floatlayout import FloatLayout
from kivy.config import Config
from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.core.window import Window
import time

#  Set the application to run in fullscreen mode on compatible displays
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.write()


class CalendarApp(App):
    """
    The main application class for the Family Calendar.

    Creates the root layout and adds the Calendar widget,
    initializing the UI when the app starts.
    """

    def build(self):
        root = FloatLayout()
        calendar = Calendar()

        # Attach calendar widget to the root layout
        root.add_widget(calendar)

        # Pass the root layout to the Calendar instance
        # to allow it to open popups or dialogs at the root level
        calendar.set_float_root(root)

        last_touch_time = [0]

        def filter_ghost_touches(window, touch):
            now = time.time()
            if now - last_touch_time[0] < 0.3:  # 300ms debounce
                print("👻 Ghost touch ignored")
                return True  # Ignore this touch
            last_touch_time[0] = now
            return False

        Window.bind(on_touch_down=filter_ghost_touches)

        return root


if __name__ == '__main__':
    CalendarApp().run()
