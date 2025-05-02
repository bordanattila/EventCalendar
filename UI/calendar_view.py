"""
calendar_view.py

The main UI component for the Family Calendar app.

Includes:
- Monthly and Weekly calendar views
- Themed day cells and event previews
- Navigation, settings, toast messages, and event popups
- Automatic theme switching (light/dark) based on time
- Support for recurring events and limited overflow handling

Author: Attila Bordan
"""
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.animation import Animation

import calendar
import datetime
import time

from app.utils import is_dark_mode
from app.api_utils import is_event_on_date
from app.theme_manager import ThemeManager
from UI.event_popup import AddEventPopup
from UI.settings_popup import create_settings_popup
from UI.weekly_view import WeeklyView
from UI.components.top_bar import TopBar
from UI.components.nav_buttons import NavButtons
from UI.components.weekday_header import WeekdayHeader
from UI.components.bottom_bar import BottomBar
from UI.components.show_day_popup import show_day_popup
from storage.db_manager import get_events_for_month


class Calendar(GridLayout):
    """
    The Calendar component is the central layout for the Family Calendar UI.

    It supports:
    - Toggling between monthly and weekly views
    - Themed rendering based on user settings or time of day
    - Adding, updating, and displaying recurring events
    - Dynamic toast messages and popups

    Extends:
        GridLayout (with 1 column and 5 rows)

    Usage:
        Used as the root layout widget in the main app window.
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

    def on_prev(self, instance):
        """Handles 'Previous Month' button click."""
        print(f"[DEBUG] Previous pressed at {time.time()}")
        if self.is_weekly_view:
            # Move to previous week
            self.current_week_date -= datetime.timedelta(days=7)
            self.current_year = self.current_week_date.year
            self.current_month = self.current_week_date.month

            # Update display and rebuild weekly view
            self.update_current_date_display()
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
        print(f"[DEBUG] Next pressed at {time.time()}")
        if self.is_weekly_view:
            # Move to next week
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
        btn = Button(
            background_normal='',
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        btn.bind(on_release=lambda instance: self.set_selected_day(day_date.day))
        box.add_widget(btn)

        # Draw cell border
        with box.canvas.before:
            Color(*get_color_from_hex(self.theme['border_color']))
            border = Line(rectangle=(0, 0, 0, 0), width=1.2)

        def update_border(*_):
            border.rectangle = (box.x, box.y, box.width, box.height)

        box.bind(pos=update_border, size=update_border)

        # Filter events for this specific day (including recurring)
        all_monthly_events = [e for e in events if is_event_on_date(e, day_date)]

        # Limit displayed events to 3
        MAX_EVENTS = 3
        extra_events = max(0, len(all_monthly_events) - MAX_EVENTS)

        # Add event previews (just time + title)
        for i, event in enumerate(sorted(all_monthly_events, key=lambda e: e.time)[:MAX_EVENTS]):
            short_title = (event.title[:25] + '...') if len(event.title) > 28 else event.title
            event_box = BoxLayout(
                orientation='horizontal',
                padding=[4, 2],
                spacing=8,
                size_hint=(1, None),
                height=30,
                pos_hint={'x': 0, 'top': 0.85 - i * 0.20},
            )

            # Create tap area for each event
            def create_event_tap(event_box_ref, event_ref):
                def on_event_tap(instance, touch):
                    # Inflate the clickable area by +10px in all directions
                    inflate = 10
                    x1 = event_box_ref.x - inflate
                    y1 = event_box_ref.y - inflate
                    x2 = event_box_ref.right + inflate
                    y2 = event_box_ref.top + inflate

                    if x1 <= touch.x <= x2 and y1 <= touch.y <= y2:
                        popup = AddEventPopup(
                            app_ref=self,
                            theme=self.theme,
                            event=event_ref,
                            on_save_callback=lambda date: self.build_calendar(self.current_year, self.current_month)
                        )
                        popup.opacity = 0
                        popup.open()
                        anim = Animation(opacity=1, d=0.3, t='out_quad')
                        anim.start(popup)
                        return True
                    return False

                return on_event_tap

            event_box.bind(on_touch_down=create_event_tap(event_box, event))

            # Draw background for each event
            with event_box.canvas.before:
                Color(0.2, 0.2, 0.2, 0.2)  # Light background for contrast
                event_bg_rect = RoundedRectangle(pos=event_box.pos, size=event_box.size, radius=[6])

            # Create a closure that captures this specific rectangle
            def make_updater(rect):
                def update_event_bg(instance, value):
                    rect.pos = (instance.x + 4, instance.y)
                    rect.size = (instance.width - 8, instance.height)

                return update_event_bg
            # Bind with the specific updater for this event box
            event_box.bind(pos=make_updater(event_bg_rect), size=make_updater(event_bg_rect))

            # Create an icon image
            icon = Image(
                source='assets/pin.png',
                size_hint=(None, 1),
                # width=16,
                allow_stretch=True,
                size=(24, 24),
            )

            # Add the event label
            preview_label = Label(
                text=f"[size=14][color={self.text_color}][b]{event.time}[/b] {short_title}[/color][/size]",
                markup=True,
                size_hint=(1, 1),
                halign='left',
                valign='middle',
                padding=(5, 2),
            )
            preview_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))

            event_box.add_widget(icon)
            event_box.add_widget(preview_label)

            box.add_widget(event_box)

        # If there are more than MAX_EVENTS, show a "+n more" pill
        if extra_events > 0:
            more_events_button = Button(
                text=f"[color={self.text_color}][b]+{extra_events} more...[/b][/color]",
                markup=True,
                font_size='16sp',
                size_hint=(1, None),
                height=20,
                pos_hint={'x': 0, 'top': 0.20},
                halign='center',
                valign='middle',
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=get_color_from_hex(self.text_color),
            )

            more_events_button.bind(on_release=lambda inst: show_day_popup(day_date, all_monthly_events, self.theme))
            box.add_widget(more_events_button)

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

        event_date = datetime.datetime.strptime(event_data['date'], '%Y-%m-%d').date()
        self.selected_day = event_date
        self.build_calendar(self.current_year, self.current_month)

    def show_toast(self, message, duration=2.5):
        """
        Displays a temporary toast-style message at the bottom of the screen.
        """
        toast = Label(
            text=message,
            markup=True,
            size_hint=(None, None),
            size=(self.width * 0.2, 30),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle',
            color=get_color_from_hex('#FFFFFF'),
            padding=(20, 10),
            bold=True,
        )
        # toast.text_size = toast.size
        toast.canvas.before.clear()
        with toast.canvas.before:
            # Color(*self.theme['button_color'])  # background color
            Color(*get_color_from_hex('#FF4C4C'))
            toast_bg = RoundedRectangle(pos=toast.pos, size=toast.size, radius=[10])

        # Keep background rectangle in sync
        def update_rect(*_):
            toast_bg.pos = toast.pos
            toast_bg.size = toast.size

        toast.bind(pos=update_rect, size=update_rect)

        if self.float_root:
            self.float_root.add_widget(toast)

            # Animate in
            toast.opacity = 0
            anim_in = Animation(opacity=1, duration=0.2)

            # Animate out after a delay

            def dismiss_toast(*_):
                anim_out = Animation(opacity=0, duration=0.2)
                anim_out.bind(on_complete=lambda *x: self.float_root
                              .remove_widget(toast))
                anim_out.start(toast)

            anim_in.start(toast)

            Clock.schedule_once(dismiss_toast, duration)
        else:
            print("⚠️ Warning: float_root not set — cannot display toast.")

    def set_float_root(self, float_root):
        """Allows the Calendar to add overlays like toast to its parent FloatLayout."""
        self.float_root = float_root

    def show_settings(self, instance=None):
        popup = create_settings_popup(self.theme_manager, lambda: self.rebuild_ui(self.float_root), self.theme)
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
