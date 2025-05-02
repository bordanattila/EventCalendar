"""
weekly_view.py

Week view component
The main layout is a horizontal BoxLayout (7 days = 7 children).

Each child is a vertical GridLayout with 24 rows for each hour.

Inside each hour slot, optionally place the event label(s).

This gives 7 tall columns, one per day, each with 24 vertical rows.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.graphics import Color, Line, Rectangle
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.animation import Animation

import datetime

from storage.db_manager import get_events_for_week
from app.api_utils import is_event_on_date
from UI.event_popup import AddEventPopup


class WeeklyView(BoxLayout):
    """
    Displays a scrollable weekly calendar view with seven day-columns.
    Each column lists events in vertical order with theme-aware styling.

    Allows editing events via popups and supports recurring event rendering.
    """
    def __init__(self, theme, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.theme = theme
        self.border_color = get_color_from_hex(theme['border_color'])
        self.text_color = self.theme['text_color']
        self.size_hint = (1, 1)
        self.spacing = 0  # No spacing between columns

        self.build_view()

        # Divider below view pane
        with self.canvas:
            Color(*get_color_from_hex(self.theme['border_color']))
            self.divider_line = Rectangle(
                pos=(self.x, self.y + self.height * 0.945),
                size=(self.width, 1),
            )

        # Keep divider in sync
        def update_divider(*_):
            self.divider_line.pos = (self.x, self.y-2)
            self.divider_line.size = (self.width, 2.5)
        self.bind(pos=update_divider, size=update_divider)

    @staticmethod
    def get_current_week_dates(reference_date=None):
        if reference_date is None:
            reference_date = datetime.date.today()
        days_since_sunday = (reference_date.weekday() + 1) % 7
        sunday = reference_date - datetime.timedelta(days=days_since_sunday)
        return [sunday + datetime.timedelta(days=i) for i in range(7)]

    def create_event_box(self, event, date):
        # Event container
        event_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=150,
            padding=(5, 5),
        )

        # Conditionally include location and notes only if they're not empty
        event_text = f"[b][color={self.theme['time_color']}]{event.time}[/color][/b]\n" + \
                     f"[color={self.text_color}]{event.title}[/color]"

        if event.location and event.location.strip():
            event_text += f"\n[size=14][color={self.theme['location_color']}][u]Location:[/u] " \
                          f"{event.location}[/color][/size]"

        # Event content
        event_label = Label(
            text=event_text,
            markup=True,
            size_hint_y=None,
            text_size=(None, None),
            halign='left',
            valign='top',
            padding=(10, 10),
        )

        def update_label_size(label, width):
            # Set text_size to constrain width and allow flowing text
            label.text_size = (width - 20, None)

            # After next render, texture_size will have the real required size
            Clock.schedule_once(lambda dt: adjust_height(label), 0)

        def adjust_height(label):
            # Set height based on texture_size with padding
            new_height = label.texture_size[1] + 20
            label.height = new_height
            label.parent.height = new_height + 10  # parent is event_box

        # Bind width changes to update_label_size
        event_label.bind(width=update_label_size)
        event_box.add_widget(event_label)

        def draw_bottom_border(widget, *_):
            widget.canvas.after.clear()
            with widget.canvas.after:
                Color(*self.border_color)
                Line(points=[widget.x, widget.y, widget.right, widget.y], width=1.2)

        def create_event_tap(event_ref, event_box_ref):
            def on_event_tap(instance, touch):
                if event_box_ref.collide_point(*touch.pos):
                    popup = AddEventPopup(
                        app_ref=self,
                        theme=self.theme,
                        event=event_ref,
                        on_save_callback=self.update_week_with_today
                    )
                    popup.opacity = 0
                    popup.open()
                    anim = Animation(opacity=1, d=0.3, t='out_quad')
                    anim.start(popup)
                    return True
                return False

            return on_event_tap

        event_box.bind(on_touch_down=create_event_tap(event, event_box))
        return event_box

    def build_view(self):
        self.clear_widgets()

        # Get week dates and events
        week_dates = self.get_current_week_dates()
        first_day = week_dates[0]
        event_dict = get_events_for_week(first_day.year, first_day.isocalendar().week)

        # Create 7 columns, one for each day
        for i, date in enumerate(week_dates):
            # Column container
            day_column = BoxLayout(orientation='vertical', size_hint_x=1 / 7)

            # Draw vertical borderline
            with day_column.canvas.after:
                Color(*self.border_color)
                v_line = Line(points=[0, 0, 0, 0], width=1.2)

                def update_v_line(inst, val):
                    v_line.points = [inst.right, inst.y, inst.right, inst.top]
                day_column.bind(pos=update_v_line, size=update_v_line)

            # Scrollable events container
            scroll = ScrollView(size_hint=(1, 1))
            events_layout = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                spacing=5,
                padding=(0, 20),
            )
            events_layout.bind(minimum_height=events_layout.setter('height'))

            # Sort events chronologically
            events = (event_dict.get(str(date), []))

            if not events:
                events = []

            # Filter events for this specific day (including recurring)
            all_weekly_events = [e for e in events if is_event_on_date(e, date)]

            # Add each event to the column
            for event in all_weekly_events:
                event_box = self.create_event_box(event, date)
                events_layout.add_widget(event_box)

            scroll.add_widget(events_layout)
            day_column.add_widget(scroll)
            self.add_widget(day_column)

        # Add vertical lines between columns at the container level for better visibility
        def update_all_borders(instance, value):
            instance.canvas.after.clear()
            with instance.canvas.after:
                for i in range(6):  # 6 dividers between 7 columns
                    col_width = instance.width / 7
                    x_pos = (i + 1) * col_width

                    Color(*self.border_color)
                    Line(
                        points=[x_pos, instance.y, x_pos, instance.y + instance.height],
                        width=1.2
                    )

        self.bind(pos=update_all_borders, size=update_all_borders)

    def update_week_with_today(self, *_):
        """Force weekly view to rebuild around today's date"""
        today = datetime.date.today()
        self.update_week(today)

    def update_week(self, reference_date):
        """Rebuilds the weekly view starting from the given reference date."""
        self.clear_widgets()
        week_dates = self.get_current_week_dates(reference_date)
        first_day = week_dates[0]
        event_dict = get_events_for_week(first_day.year, first_day.isocalendar().week)

        for i, date in enumerate(week_dates):
            # Column container
            day_column = BoxLayout(orientation='vertical', size_hint_x=1 / 7)

            # Draw vertical borderline
            with day_column.canvas.after:
                Color(*self.border_color)
                v_line = Line(points=[0, 0, 0, 0], width=1.2)

                def update_v_line(inst, val):
                    v_line.points = [inst.right, inst.y, inst.right, inst.top]

                day_column.bind(pos=update_v_line, size=update_v_line)

            # Scrollable events container
            scroll = ScrollView(
                size_hint=(1, 1),
                bar_width=8,
                scroll_type=['bars', 'content'],
                bar_color=get_color_from_hex(self.theme.get('scrollbar_color', '#888888')),
                bar_inactive_color=get_color_from_hex(self.theme.get('scrollbar_inactive_color', '#555555')),
                effect_cls='ScrollEffect',
            )
            events_layout = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                spacing=0,
                padding=(0, 20),
            )
            events_layout.bind(minimum_height=events_layout.setter('height'))

            # Sort events chronologically
            events = sorted(event_dict.get(str(date), []), key=lambda e: e.time)
            all_weekly_events = [e for e in events if is_event_on_date(e, date)]

            # Add each event to the column
            for event in all_weekly_events:
                event_box = self.create_event_box(event, date)
                events_layout.add_widget(event_box)

            scroll.add_widget(events_layout)
            day_column.add_widget(scroll)
            self.add_widget(day_column)
