"""
calendar_view.py

Main Calendar view component with dynamic theme support and settings popup.
"""

from app.utils import is_dark_mode
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.graphics import Color, Line, Rectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import get_color_from_hex

import calendar
import datetime

from app.utils import get_time, get_date, get_day
from app.theme_manager import ThemeManager
from UI.event_popup import AddEventPopup


class Calendar(GridLayout):
    """
    Main calendar component that includes:
    - Current time, date, and day bar
    - Month navigation buttons
    - Weekday headers with background colors
    - Dynamic calendar grid display for the selected month
    - Settings popup
    """
    def __init__(self, **kwargs):
        super(Calendar, self).__init__(**kwargs)
        self.cols = 1
        self.rows = 5
        self.dark_mode = is_dark_mode()

        # Load theme and settings
        self.theme_manager = ThemeManager()
        self.theme_manager.update_theme()
        self.theme = self.theme_manager.get_theme()

        # Set theme-dependent colors
        self.bg_color = (0.1, 0.1, 0.1, 1) if self.dark_mode else (1, 1, 1, 1)
        self.dark_mode = self.theme['text_color'] == 'FFFFFF'
        self.text_color = self.theme['text_color']

        Window.clearcolor = self.theme['bg_color']

        # Top Bar: Time / Day / Date
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

        # Navigation Buttons
        self.button_grid = GridLayout(cols=2, size_hint_y=0.06, spacing=50, padding=[50, 0, 50, 10])
        self.button_grid.add_widget(self.themed_button('<< Previous Month', self.on_prev))
        self.button_grid.add_widget(self.themed_button('Next Month >>', self.on_next))
        self.add_widget(self.button_grid)


        # Weekday Headers
        self.days_of_week = GridLayout(cols=7, size_hint_y=0.05)
        self.add_weekdays_header()
        self.add_widget(self.days_of_week)

        # Calendar Grid Display
        self.calendar_display = GridLayout(cols=7, size_hint_y=0.85)
        today = datetime.date.today()
        self.build_calendar(today.year, today.month)
        self.add_widget(self.calendar_display)

        # Add Event and Settings Button (touch-friendly)
        self.bottom_bar = GridLayout(cols=2, size_hint_y=0.06, spacing=150, padding=[5, 5, 5, 5])

        # Left: Add Event button
        self.bottom_bar.add_widget(self.themed_button('+ Add Event', self.on_add_event))

        # Right: Settings button (aligned to right)
        self.bottom_bar.add_widget(self.themed_button('⚙ Settings', self.show_settings))

        self.add_widget(self.bottom_bar)

        # Update clock every second
        Clock.schedule_interval(self.update_time, 1)

        # Check time for dark and light mode
        Clock.schedule_interval(self.check_theme_switch, 600)

    def on_prev(self, instance):
        """Handles 'Previous Month' button click."""
        print('Previous month clicked')

    def on_next(self, instance):
        """Handles 'Next Month' button click."""
        print('Next month clicked')

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

            # Use background color per day or theme-wide fallback
            bg_color = bg_color_light if not self.theme_manager.settings['auto_mode'] else self.theme['bg_color']

            # Draw background
            with box.canvas.before:
                if isinstance(bg_color, str):
                    Color(*get_color_from_hex(bg_color))
                else:
                    Color(*bg_color)

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

    def themed_button(self, text, on_press=None):
        """
        Creates a themed button with a border and proper background.
        Returns a BoxLayout containing the styled button.
        """

        box = BoxLayout(size_hint=(1, 1), height=50)

        # Border
        with box.canvas.before:
            Color(*self.theme['button_border_color'])
            border = Line(rectangle=(0, 0, 0, 0), width=1.2)

        def update_border(*_):
            border.rectangle = (box.x, box.y, box.width, box.height)

        box.bind(pos=update_border, size=update_border)

        button = Button(
            text=text,
            background_normal='',
            background_color=self.theme['button_color'],
            color=get_color_from_hex(self.theme['text_color']),
            size_hint=(1, 1),
            halign='center',
            valign='middle',
        )

        button.text_size = (None, None)

        if on_press:
            button.bind(on_press=on_press)

        box.add_widget(button)
        return box

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
            Color(*self.theme['border_color'])
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
            print('Switching theme based on time of day...')
            self.dark_mode = current_mode

            # Update app-wide colors
            self.text_color = 'FFFFFF' if self.dark_mode else '000000'
            self.bg_color = (0.1, 0.1, 0.1, 1) if self.dark_mode else (1, 1, 1, 1)
            Window.clearcolor = self.bg_color

            # Rebuild UI with new theme
            self.clear_widgets()
            self.__init__()  # Re-run initialization with new theme

    def show_settings(self, instance=None):
        """
        Displays a popup where the user can customize the theme, toggle auto mode,
        and set custom dark/light times.
        """

        layout = BoxLayout(orientation='vertical', spacing=10, padding=20)

        # Theme selection
        layout.add_widget(Label(text='Select Theme:', size_hint_y=None, height=30))
        theme_spinner = Spinner(
            text=self.theme_manager.settings['preferred_theme'],
            values=list(self.theme_manager.themes.keys()),
            size_hint_y=None,
            height=44
        )
        layout.add_widget(theme_spinner)

        # Auto Mode Label + Switch
        auto_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=10)
        auto_layout.add_widget(Label(text="Auto Light/Dark Mode:", size_hint_x=0.7))
        auto_mode_switch = Switch(active=self.theme_manager.settings["auto_mode"], size_hint_x=0.3)
        auto_layout.add_widget(auto_mode_switch)
        layout.add_widget(auto_layout)

        # Light start time input
        light_input = TextInput(
            text=self.theme_manager.settings['light_start'],
            hint_text='HH:MM',
            multiline=False,
            size_hint_y=None,
            height=44
        )
        layout.add_widget(Label(text='Light Mode Start (HH:MM):', size_hint_y=None, height=30))
        layout.add_widget(light_input)

        # Dark start time input
        dark_input = TextInput(
            text=self.theme_manager.settings['dark_start'],
            hint_text='HH:MM',
            multiline=False,
            size_hint_y=None,
            height=44
        )
        layout.add_widget(Label(text='Dark Mode Start (HH:MM):', size_hint_y=None, height=30))
        layout.add_widget(dark_input)

        # Save button
        save_button = Button(text='Save and Apply', size_hint_y=None, height=50)
        layout.add_widget(save_button)

        popup = Popup(title='Settings', content=layout, size_hint=(0.8, 0.8))

        def toggle_theme_spinner(*args):
            theme_spinner.disabled = auto_mode_switch.active

        auto_mode_switch.bind(active=toggle_theme_spinner)
        toggle_theme_spinner()  # initialize

        def save_settings(instance):
            # Apply user settings
            auto_mode = auto_mode_switch.active
            selected_theme = theme_spinner.text
            light_start = light_input.text
            dark_start = dark_input.text

            # Save values from UI to theme manager
            self.theme_manager.toggle_auto_mode(auto_mode_switch.active)
            self.theme_manager.set_custom_theme(theme_spinner.text)
            self.theme_manager.set_dark_light_times(light_input.text, dark_input.text)

            # Update app theme
            self.theme_manager.update_theme()
            self.theme = self.theme_manager.get_theme()
            self.text_color = self.theme["text_color"]
            self.dark_mode = self.text_color == "FFFFFF"

            # Rebuild UI
            self.clear_widgets()
            self.__init__()
            popup.dismiss()

        save_button.bind(on_release=save_settings)

        popup.open()

    def on_add_event(self, instance):
        popup = AddEventPopup(
            theme=self.theme,
            on_save_callback=self.save_event
        )
        popup.open()

    def save_event(self, event_data):
        print("Saved Event:", event_data)
        # TODO: Save to file/db and refresh calendar display


