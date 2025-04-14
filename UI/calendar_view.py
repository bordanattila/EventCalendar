"""
calendar_view.py

Main Calendar view component with dynamic theme support and settings popup.
"""

from app.utils import is_dark_mode
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
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
from storage.db_manager import get_events_for_month


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

        today = datetime.date.today()
        self.current_year = today.year
        self.current_month = today.month

        # Load theme and settings
        self.theme_manager = ThemeManager()
        self.theme_manager.update_theme()
        self.theme = self.theme_manager.get_theme()

        # Set theme-dependent colors
        self.bg_color = (0.1, 0.1, 0.1, 1) if self.dark_mode else (1, 1, 1, 1)
        self.dark_mode = self.theme['text_color'] == 'FFFFFF'
        self.text_color = self.theme['text_color']

        Window.clearcolor = self.theme['bg_color']

        self.current_time = str(get_time())
        self.current_day = str(get_day())
        self.current_date = str(get_date())

        # Top Bar: Time / Day / Date
        self.date_time_bar_grid = BoxLayout(
            orientation='horizontal',
            size_hint_y=0.08,
            padding=[20, 10],
            spacing=20
        )

        label_style = {
            'markup': True,
            'font_size': '20sp',
            'halign': 'center',
            'valign': 'middle',
        }

        self.current_time_label = Label(
            text=f"[b][color={self.text_color}]{self.current_time}[/color][/b]",
            **label_style
        )
        self.current_day_label = Label(
            text=f"[b][color={self.text_color}]{self.current_day}[/color][/b]",
            **label_style
        )
        self.current_date_label = Label(
            text=f"[b][color={self.text_color}]{self.current_date}[/color][/b]",
            **label_style
        )

        self.date_time_bar_grid.add_widget(self.current_time_label)
        self.date_time_bar_grid.add_widget(self.current_day_label)
        self.date_time_bar_grid.add_widget(self.current_date_label)
        self.add_widget(self.date_time_bar_grid)

        # Divider below top bar
        with self.canvas:
            Color(*get_color_from_hex(self.theme['border_color']))
            self.divider_line = Rectangle(
                pos=(self.x, self.y + self.height * 0.945),
                size=(self.width, 1),
            )

        # Keep divider in sync
        def update_divider(*_):
            self.divider_line.pos = (self.x, self.y + self.height * 0.945)
            self.divider_line.size = (self.width, 1)
        self.bind(pos=update_divider, size=update_divider)

        # Navigation Buttons
        self.button_grid = GridLayout(cols=2, size_hint_y=0.06, spacing=50, padding=[50, 0, 50, 10])
        self.button_grid.add_widget(
            self.themed_button('<< Previous Month', self.on_prev, bg_override=self.theme['nav_button_color'])
        )
        self.button_grid.add_widget(
            self.themed_button('Next Month >>', self.on_next, bg_override=self.theme['nav_button_color'])
        )
        self.add_widget(self.button_grid)

        # Weekday Headers
        self.days_of_week = GridLayout(cols=7, size_hint_y=0.05)
        self.add_weekdays_header()
        self.add_widget(self.days_of_week)

        # Calendar Grid Display
        self.selected_day = datetime.date.today()  # default to today
        self.calendar_display = GridLayout(cols=7, size_hint_y=0.85)
        self.build_calendar(today.year, today.month)
        self.add_widget(self.calendar_display)

        # Add Event and Settings Button (touch-friendly)
        self.bottom_bar = GridLayout(cols=2, size_hint_y=0.06, spacing=50, padding=[50, 15, 50, 10])

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
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.build_calendar(self.current_year, self.current_month)

    def on_next(self, instance):
        """Handles 'Next Month' button click."""
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.build_calendar(self.current_year, self.current_month)

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
            bg_color = get_color_from_hex(bg_color_light)
            if self.theme_manager.settings['auto_mode'] and self.dark_mode:
                bg_color = self.theme['bg_color']

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

    def themed_button(self, text, on_press=None, bg_override=None):
        """
        Creates a themed button with a border and proper background.
        Returns a BoxLayout containing the styled button.
        """

        box = BoxLayout(size_hint=(1, 1), height=50)

        with box.canvas.before:
            # # Shadow
            # Color(0, 0, 0, 0,25)
            # shadow = RoundedRectangle(pos=(box.x + 2, box.y - 2), size=box.size, radius=[10])

            # Background fill
            Color(*get_color_from_hex(bg_override or self.theme['button_color']))
            button_bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[10])

            # Border
            # Color(*get_color_from_hex(self.theme['button_border_color']))
            # button_border = RoundedRectangle(pos=box.pos, size=box.size, radius=[10])

        def update_graphics(*_):
            # shadow.pos = (box.x + 2, box.y - 2)
            # shadow.size = box.size
            button_bg.pos = box.pos
            button_bg.size = box.size
            # button_border.pos = box.pos
            # button_border.size = box.size

        box.bind(pos=update_graphics, size=update_graphics)

        button = Button(
            text=text,
            background_normal='',
            background_color=get_color_from_hex(bg_override or self.theme['button_color']),
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

        # Get all events for current month
        events_this_month = get_events_for_month(year, month)

        # Add empty cells for alignment
        for _ in range(first_weekday):
            self.calendar_display.add_widget(Label(text=''))

        # Add actual calendar day cells
        for day in range(1, total_days + 1):
            day_date = datetime.date(year, month, day)
            date_str = str(day_date)
            day_event = events_this_month.get(date_str, [])

            self.calendar_display.add_widget(self.create_day_cell(day_date, day_event))

    def create_day_cell(self, day_date, events):
        """
        Wraps a calendar day label in a BoxLayout with a black border.
        """
        # box = BoxLayout(orientation='vertical', padding=[4, 25, 4, 0], spacing=2)
        box = FloatLayout()

        # Format date text
        if day_date == datetime.date.today():
            day_text = f"[b][color=ff3333]{day_date.day}[/color][/b]"
        elif self.selected_day == day_date:
            day_text = f"[b][color=00CED1]{day_date.day}[/color][/b]"
        else:
            day_text = f"[b][color={self.text_color}]{day_date.day}[/color][/b]"

        # Day number Label
        day_label = Label(
            text=day_text,
            markup=True,
            size_hint=(None, None),
            size=(30, 20),
            pos_hint={'x': 0, 'top': 1},
            halign='left',
            valign='top',
        )
        day_label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
        box.add_widget(day_label)

        # Cell input area
        # anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        btn = Button(
            background_normal='',
            # background_color=self.theme['cell_color'],
            background_color=(0, 0, 0, 0),
            # color=get_color_from_hex(self.theme['text_color']),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        btn.bind(on_release=lambda instance: self.set_selected_day(day_date.day))
        # anchor.add_widget(btn)
        box.add_widget(btn)

        # Draw cell border
        with box.canvas.before:
            Color(*get_color_from_hex(self.theme['border_color']))
            border = Line(rectangle=(0, 0, 0, 0), width=1.2)

        def update_border(*_):
            border.rectangle = (box.x, box.y, box.width, box.height)

        # Add event previews (just time + title)
        for i, event in enumerate(events[:2]):  # Limit to 2 for clarity
            preview = Label(
                text=f"[size=12][color={self.text_color}]{event.title} @ {event.time}[/color][/size]",
                markup=True,
                font_size='12sp',
                halign='left',
                valign='top',
                size_hint=(1, None),
                height=15,
                pos_hint={'x': 0, 'top': 0.85 - i * 0.15},
                padding=(5, 0),
            )
            preview.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
            # preview.bind(size=preview.setter('text_size'))
            box.add_widget(preview)


        box.bind(pos=update_border, size=update_border)
        return box

    def update_time(self, dt):
        """
        Updates the time display every second.
        """
        new_time = str(get_time())
        self.current_time_label.text = f"[b][color={self.text_color}]{new_time}[/color][/b]"

    def rebuild_ui(self, root_ref):
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
        self.selected_day = datetime.date(self.current_year, self.current_month, day)
        self.build_calendar(self.current_year, self.current_month)
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
