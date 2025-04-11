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
from kivy.animation import Animation

import calendar
import datetime

from app.utils import get_time, get_date, get_day
from app.theme_manager import ThemeManager
from UI.event_popup import AddEventPopup
from UI.settings_popup import create_settings_popup


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

        self.selected_day = datetime.date.today()  # default to today

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

        self.float_root = None

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

        # Adjust: Python's calendar starts with Monday (0), UI starts with Sunday (0)
        first_weekday = (first_weekday + 1) % 7

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

            self.calendar_display.add_widget(self.create_day_cell(day_text, day))

    def create_day_cell(self, text, day):
        """
        Wraps a calendar day label in a BoxLayout with a black border.
        """
        box = BoxLayout()
        btn = Button(
            text=text,
            markup=True,
            background_normal='',
            background_color=self.theme['button_color'],
            color=get_color_from_hex(self.theme['text_color'])
        )
        btn.bind(on_release=lambda instance: self.set_selected_day(day))

        # Draw cell border
        with box.canvas.before:
            Color(*self.theme['border_color'])
            border = Line(rectangle=(0, 0, 0, 0), width=1.2)

        def update_border(*_):
            border.rectangle = (box.x, box.y, box.width, box.height)

        box.bind(pos=update_border, size=update_border)
        box.add_widget(btn)
        return box

    def update_time(self, dt):
        """
        Updates the time display every second.
        """
        new_time = str(get_time())
        self.current_time_label.text = f"[b][color={self.text_color}]{new_time}[/color][/b]"

    def rebuild_ui(self, root_ref,):
        # Re-run initialization with new theme
        root_ref = self.float_root
        self.clear_widgets()
        self.__init__()
        self.set_float_root(root_ref)

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

            self.rebuild_ui(self.float_root)

    def set_selected_day(self, day):
        today = datetime.date.today()
        self.selected_day = datetime.date(today.year, today.month, day)
        self.show_toast(f"Selected {self.selected_day.strftime('%b %d')}")

    def on_add_event(self, instance):
        popup = AddEventPopup(
            theme=self.theme,
            on_save_callback=self.save_event,
            app_ref=self,
            initial_date=self.selected_day,
        )
        popup.open()

    def save_event(self, event_data):
        print('Saved Event:', event_data)
        self.show_toast(f"Event '{event_data['title']}' added!")
        # TODO: Save to file/db and refresh calendar display

    def show_toast(self, message, duration=2.5):
        """
        Displays a temporary toast-style message at the bottom of the screen.
        """
        toast = Label(
            text=message,
            size_hint=(None, None),
            size=(self.width * 0.8, 40),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle',
            color=get_color_from_hex('#FF4C4C'),
            bold=True
        )
        toast.canvas.before.clear()
        with toast.canvas.before:
            Color(*self.theme['button_color'])  # background color
            toast_bg = Rectangle(pos=toast.pos, size=toast.size)

        # Keep background rectangle in sync
        def update_rect(*_):
            toast_bg.pos = toast.pos
            toast_bg.size = toast.size

        toast.bind(pos=update_rect, size=update_rect)

        if self.float_root:
            self.float_root.add_widget(toast)

            def dismiss_toast(*_):
                anim = Animation(opacity=0, duration=0.5)
                anim.bind(on_complete=lambda *args: self.float_root.remove_widget(toast))
                anim.start(toast)

            Clock.schedule_once(dismiss_toast, duration)
        else:
            print("⚠️ Warning: float_root not set — cannot display toast.")

    def set_float_root(self, float_root):
        """Allows the Calendar to add overlays like toast to its parent FloatLayout."""
        self.float_root = float_root

    def show_settings(self, instance=None):
        popup = create_settings_popup(self.theme_manager, lambda: self.rebuild_ui(self.float_root))
        popup.open()