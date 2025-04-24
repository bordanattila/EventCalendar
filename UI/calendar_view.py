"""
calendar_view.py

Main Calendar view component with dynamic theme support and settings popup.
"""

from app.utils import is_dark_mode
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.animation import Animation

import calendar
import datetime

from app.theme_manager import ThemeManager
from UI.event_popup import AddEventPopup
from UI.settings_popup import create_settings_popup
from UI.weekly_view import WeeklyView
from UI.components.top_bar import TopBar
from UI.components.nav_buttons import NavButtons
from UI.components.weekday_header import WeekdayHeader
from UI.components.bottom_bar import BottomBar
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
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 5
        self.dark_mode = is_dark_mode()

        today = datetime.date.today()
        self.current_week_date = today
        self.current_year = today.year
        self.current_month = today.month
        self.is_weekly_view = False


        # Load theme and settings
        self.theme_manager = ThemeManager()
        self.theme_manager.update_theme()
        self.theme = self.theme_manager.get_theme()

        self.weekly_view = WeeklyView(theme=self.theme)
        self.weekly_view.update_week(datetime.date(self.current_year, self.current_month, 1))

        # Set theme-dependent colors
        self.bg_color = (0.1, 0.1, 0.1, 1) if self.dark_mode else (1, 1, 1, 1)
        self.dark_mode = self.theme['text_color'] == 'FFFFFF'
        self.text_color = self.theme['text_color']

        Window.clearcolor = self.theme['bg_color']

        # Top Bar
        self.top_bar = TopBar(self.theme)
        self.add_widget(self.top_bar)

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

        # # Navigation Buttons
        self.nav_grid = NavButtons(
            theme=self.theme,
            on_prev=self.on_prev,
            on_next=self.on_next,
            is_weekly_view=self.is_weekly_view,
        )
        self.add_widget(self.nav_grid)

        # Weekday Headers
        self.weekday_header = WeekdayHeader(theme=self.theme, theme_manager=self.theme_manager,
                                            dark_mode=self.dark_mode)
        self.add_widget(self.weekday_header)

        # Calendar Grid Display
        self.selected_day = datetime.date.today()  # default to today
        self.calendar_display = GridLayout(cols=7, size_hint_y=0.85)
        self.build_calendar(today.year, today.month)
        self.add_widget(self.calendar_display)

        # Bottom bar
        self.bottom_bar = BottomBar(
            theme=self.theme,
            on_toggle_view=self.toggle_weekly_view,
            on_add_event=self.on_add_event,
            on_show_settings=self.show_settings,
            is_weekly_view=self.is_weekly_view,
        )
        self.add_widget(self.bottom_bar)

        # Check time for dark and light mode
        Clock.schedule_interval(self.check_theme_switch, 600)

        self.float_root = None

    def create_themed_button(self, text, callback=None, button_type='standard', bg_override=None, font_override=None):
        """
        Creates a styled button with shadow and background, using theme settings.
        button_type: 'standard' (bottom bar), 'nav' (navigation bar), or custom
        """
        box = BoxLayout(size_hint=(1, 1), height=50, spacing=5, padding=[10, 0])

        # Pick the correct background color based on button type
        if bg_override:
            bg_color = bg_override
        elif button_type == 'nav':
            bg_color = self.theme.get('nav_button_color', self.theme['button_color'])
        else:
            bg_color = self.theme['button_color']

        # Background + Shadow drawing
        with box.canvas.before:
            # Fix for shadow being white: ensure the alpha is correct and the canvas draws at the right time
            Color(0, 0, 0, 0.25)
            shadow = RoundedRectangle(pos=(box.x + 2, box.y - 2), size=box.size, radius=[10])

            Color(*get_color_from_hex(bg_color))
            button_bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[10])

        def update_graphics(*_):
            shadow.pos = (box.x + 2, box.y - 2)
            shadow.size = box.size
            button_bg.pos = box.pos
            button_bg.size = box.size

        box.bind(pos=update_graphics, size=update_graphics)

        # Create the actual button
        button = Button(
            text=text,
            background_normal='',
            background_color=get_color_from_hex(bg_color),
            color=get_color_from_hex(self.theme['text_color']),
            size_hint=(1, 1),
            halign='center',
            valign='middle',
            font_name=font_override if font_override else 'Roboto',
        )
        button.text_size = (None, None)

        if callback:
            button.bind(on_press=callback)

        box.add_widget(button)
        return box

    def on_prev(self, instance):
        """Handles 'Previous Month' button click."""
        if self.is_weekly_view:
            # Move to previous week
            # current_date = datetime.date(self.current_year, self.current_month, 1)
            # prev_week = current_date - datetime.timedelta(days=7)
            self.current_week_date -= datetime.timedelta(days=7)
            self.current_year = self.current_week_date.year
            self.current_month = self.current_week_date.month
            # self.current_year = prev_week.year
            # self.current_month = prev_week.month

            # Update display and rebuild weekly view
            self.update_current_date_display()
            # self.weekly_view.update_week(prev_week)
            self.weekly_view.update_week(self.current_week_date)
            week_dates = WeeklyView.get_current_week_dates(self.current_week_date)  # or next_week
            self.weekday_header.update_weekly_dates(week_dates)
        else:
            # Move to previous month
            if self.current_month == 1:
                self.current_month = 12
                self.current_year -= 1
            else:
                self.current_month -= 1
            self.update_current_date_display()
            self.build_calendar(self.current_year, self.current_month)

    def on_next(self, instance):
        """Handles 'Next Month' button click."""
        if self.is_weekly_view:
            # Move to next week
            # current_date = datetime.date(self.current_year, self.current_month, 1)
            # next_week = current_date + datetime.timedelta(days=7)
            self.current_week_date += datetime.timedelta(days=7)
            self.current_year = self.current_week_date.year
            self.current_month = self.current_week_date.month

            # Update display and rebuild weekly view
            self.update_current_date_display()
            self.weekly_view.update_week(self.current_week_date)
            week_dates = WeeklyView.get_current_week_dates(self.current_week_date)  # or next_week
            self.weekday_header.update_weekly_dates(week_dates)

        else:
            # Move to next month
            if self.current_month == 12:
                self.current_month = 1
                self.current_year += 1
            else:
                self.current_month += 1
            self.update_current_date_display()
            self.build_calendar(self.current_year, self.current_month)

    def update_current_date_display(self):
        new_date = datetime.date(self.current_year, self.current_month, 1)
        self.current_date = new_date.strftime("%B %Y")
        self.top_bar.date_label.text = f"[b][color={self.text_color}]{self.current_date}[/color][/b]"

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
        for i, event in enumerate(sorted(events, key=lambda e: e.time)):
            short_title = (event.title[:22] + '...') if len(event.title) > 25 else event.title
            preview = Label(
                text=f"[size=12][color={self.text_color}]* {short_title} @ {event.time}[/color][/size]",
                markup=True,
                font_size='12sp',
                halign='left',
                valign='top',
                size_hint=(1, None),
                height=15,
                pos_hint={'x': 0, 'top': 0.85 - i * 0.15},
                padding=(5, 2),
            )
            preview.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)),
                         texture_size=lambda instance, value: setattr(instance, 'height', value[1]),
                         )
            # preview.bind(size=preview.setter('text_size'))
            box.add_widget(preview)

        box.bind(pos=update_border, size=update_border)
        return box

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
            pos_hint={'center_x': 0.5},
            halign='center',
            valign='bottom',
            # color=get_color_from_hex('#FF4C4C'),
            # background_color=get_color_from_hex('#ff3333'),
            color=get_color_from_hex('#FFFFFF'),
            bold=True
        )
        toast.canvas.before.clear()
        with toast.canvas.before:
            # Color(*self.theme['button_color'])  # background color
            Color(*get_color_from_hex('#FF4C4C'))
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

    def toggle_weekly_view(self, instance):
        self.clear_widgets()
        self.is_weekly_view = not self.is_weekly_view

        # Update button texts
        self.bottom_bar.update_view_button_text(self.is_weekly_view)
        self.nav_grid.update_button_text(self.is_weekly_view)

        # Re-add the top bar
        self.add_widget(self.top_bar)

        # Re-add the nav buttons
        self.add_widget(self.nav_grid)

        week_dates = None
        if self.is_weekly_view:
            today = datetime.date.today()
            week_dates = WeeklyView.get_current_week_dates()  # Use the static method from WeeklyView

        # Re-create the weekday header with appropriate settings
        self.weekday_header = WeekdayHeader(
            theme=self.theme,
            theme_manager=self.theme_manager,
            dark_mode=self.dark_mode,
            is_weekly_view=self.is_weekly_view,
            week_dates=week_dates
        )
        self.add_widget(self.weekday_header)

        # Display appropriate view
        if self.is_weekly_view:
            self.weekly_view = WeeklyView(theme=self.theme)
            self.add_widget(self.weekly_view)
        else:
            # Rebuild the monthly calendar
            self.calendar_display = GridLayout(cols=7, size_hint_y=0.85)
            self.build_calendar(self.current_year, self.current_month)
            self.add_widget(self.calendar_display)

        # Re-add the bottom bar
        self.add_widget(self.bottom_bar)
