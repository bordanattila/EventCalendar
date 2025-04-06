"""
Family Calendar Application
---------------------------
A Python Kivy-based monthly calendar app that displays the current time, day,
and date with weekday headers, interactive month navigation, and styled UI elements.

Created by Attila Bordan.
"""

from kivy.app import App
from app.utils import is_dark_mode
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Line, Rectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import get_color_from_hex

import calendar
import datetime

from app.utils import get_time, get_date, get_day


class Calendar(GridLayout):
    """
    Main calendar component that includes:
    - Current time, date, and day bar
    - Month navigation buttons
    - Weekday headers with background colors
    - Dynamic calendar grid display for the selected month
    """
    def __init__(self, **kwargs):
        super(Calendar, self).__init__(**kwargs)
        self.cols = 1
        self.rows = 4
        self.dark_mode = is_dark_mode()

        # Set theme-dependent colors
        self.text_color = "FFFFFF" if self.dark_mode else "000000"
        self.bg_color = (0.1, 0.1, 0.1, 1) if self.dark_mode else (1, 1, 1, 1)

        Window.clearcolor = self.bg_color

        # --- Top Bar: Time / Day / Date ---
        self.date_time_bar_grid = GridLayout(cols=3, size_hint_y=0.05)
        self.current_time = str(get_time())
        self.current_day = str(get_day())
        self.current_date = str(get_date())

        self.current_time_label = Label(
            text=f"[b][color={self.text_color}]{self.current_time}[/color][/b]",
            markup=True
        )
        self.current_day_label = Label(
            text=f"[b][color={self.text_color}]{self.current_day}[/color][/b]",
            markup=True
        )
        self.current_date_label = Label(
            text=f"[b][color={self.text_color}]{self.current_date}[/color][/b]",
            markup=True
        )

        self.date_time_bar_grid.add_widget(self.current_time_label)
        self.date_time_bar_grid.add_widget(self.current_day_label)
        self.date_time_bar_grid.add_widget(self.current_date_label)
        self.add_widget(self.date_time_bar_grid)

        # --- Navigation Buttons ---
        self.button_grid = GridLayout(cols=2, size_hint_y=0.05)
        self.prev_button = Button(text='<< Previous Month')
        self.next_button = Button(text='Next Month >>')
        self.prev_button.bind(on_press=self.on_prev)
        self.next_button.bind(on_press=self.on_next)
        self.button_grid.add_widget(self.prev_button)
        self.button_grid.add_widget(self.next_button)
        self.add_widget(self.button_grid)

        # --- Weekday Headers ---
        self.days_of_week = GridLayout(cols=7, size_hint_y=0.05)
        self.add_weekdays_header()
        self.add_widget(self.days_of_week)

        # --- Calendar Grid Display ---
        self.calendar_display = GridLayout(cols=7, size_hint_y=0.85)
        today = datetime.date.today()
        self.build_calendar(today.year, today.month)
        self.add_widget(self.calendar_display)

        # Update clock every second
        Clock.schedule_interval(self.update_time, 1)

        # Check time for dark and light mode
        Clock.schedule_interval(self.check_theme_switch, 600)

    def on_prev(self, instance):
        """Handles 'Previous Month' button click."""
        print("Previous month clicked")

    def on_next(self, instance):
        """Handles 'Next Month' button click."""
        print("Next month clicked")

    def add_weekdays_header(self):
        """
        Creates colored weekday header cells with text labels
        and adds them to the header row.
        """
        days_with_colors = [
            ('Sun', 'FFD700'),  # Gold
            ('Mon', 'B0C4DE'),  # Light Steel Blue
            ('Tue', '98FB98'),  # Pale Green
            ('Wed', 'FFFF99'),  # Bright Yellow Tint
            ('Thu', 'FFA07A'),  # Light Salmon
            ('Fri', 'D3D3D3'),  # Light Gray
            ('Sat', '87CEFA')   # Light Sky Blue
        ]

        for day, bg_color_light in days_with_colors:
            box = BoxLayout()

            # Use dark or light background color
            bg_color = '2E2E2E' if self.dark_mode else bg_color_light

            # Draw background
            with box.canvas.before:
                Color(*get_color_from_hex(bg_color))
                bg_rect = Rectangle(pos=box.pos, size=box.size)

            # Keep background in sync with layout
            def make_updater(widget, rect):
                def update(*_):
                    rect.pos = widget.pos
                    rect.size = widget.size
                return update

            box.bind(pos=make_updater(box, bg_rect), size=make_updater(box, bg_rect))

            # Add day label
            if self.dark_mode:
                label = Label(
                    text=f"[b][color={bg_color_light}]{day}[/color][/b]",
                    markup=True
                )
            else:
                label = Label(
                    text=f"[b][color={self.text_color}]{day}[/color][/b]",
                    markup=True
                )

            box.add_widget(label)
            self.days_of_week.add_widget(box)

    def build_calendar(self, year, month):
        """
        Builds the calendar grid for a given month and year.
        Highlights today's date and aligns day numbers correctly.
        """
        self.calendar_display.clear_widgets()
        first_weekday, total_days = calendar.monthrange(year, month)

        # Add empty cells for alignment
        for _ in range(first_weekday):
            self.calendar_display.add_widget(Label(text=''))

        # Add actual calendar day cells
        today = datetime.date.today()
        for day in range(1, total_days + 1):
            if year == today.year and month == today.month and day == today.day:
                day_text = f"[b][color=ff3333]{day}[/color][/b]"
            else:
                day_text = f"[b][color={self.text_color}]{day}[/color][/b]"

            self.calendar_display.add_widget(self.create_day_cell(day_text))

    def create_day_cell(self, text):
        """
        Wraps a calendar day label in a BoxLayout with a black border.
        """
        box = BoxLayout()
        label = Label(text=text, markup=True)

        # Draw cell border
        with box.canvas.before:
            Color(*get_color_from_hex("444444") if self.dark_mode else (0, 0, 0, 1))
            border = Line(rectangle=(0, 0, 0, 0), width=1.2)

        def update_border(*_):
            border.rectangle = (box.x, box.y, box.width, box.height)

        box.bind(pos=update_border, size=update_border)
        box.add_widget(label)
        return box

    def update_time(self, dt):
        """
        Updates the time display every second.
        """
        new_time = str(get_time())
        self.current_time_label.text = f"[b][color={self.text_color}]{new_time}[/color][/b]"

    def check_theme_switch(self, dt):
        """
        Periodically checks if the theme should be updated based on time of day.
        If a theme switch is needed, the UI is rebuilt.
        """

        current_mode = is_dark_mode()
        if current_mode != self.dark_mode:
            print("Switching theme based on time of day...")
            self.dark_mode = current_mode

            # Update app-wide colors
            self.text_color = "FFFFFF" if self.dark_mode else "000000"
            self.bg_color = (0.1, 0.1, 0.1, 1) if self.dark_mode else (1, 1, 1, 1)
            Window.clearcolor = self.bg_color

            # Rebuild UI with new theme
            self.clear_widgets()
            self.__init__()  # Re-run initialization with new theme


class CalendarApp(App):
    """Initializes and runs the calendar application."""
    def build(self):
        return Calendar()


if __name__ == '__main__':
    CalendarApp().run()
