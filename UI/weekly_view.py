"""
weekly_view.py

Week view component
"""

from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Line, Rectangle
from kivy.utils import get_color_from_hex

import datetime

from storage.db_manager import get_events_for_week
from app.theme_manager import ThemeManager


class WeeklyView(GridLayout):
    """
    Weekly view component that includes:
    - Days of the week
    """
    def __init__(self, theme, **kwargs):
        super().__init__(**kwargs)
        self.cols = 7
        self.rows = 24
        self.theme = theme
        self.border_color = get_color_from_hex(theme['border_color'])
        self.text_color = self.theme['text_color']
        self.size_hint = (1, 1)

    @staticmethod
    def get_current_week_dates():
        today = datetime.date.today()
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - datetime.timedelta(days=days_since_sunday)
        result = [sunday + datetime.timedelta(days=i) for i in range(7)]
        return result

    def build_view(self):
        self.clear_widgets()

        week_dates = WeeklyView.get_current_week_dates()
        first_day = week_dates[0] # First day of the week
        event_dict = get_events_for_week(first_day.year, first_day.isocalendar().week)

        for hour in range(24):  # inner loop is hour (== rows per column)
            for date in week_dates:  # now outer loop is date (== column)
                events = event_dict.get(str(date), [])
                try:
                    matching = [e for e in events if int(e.time.split(":")[0]) == hour]
                except Exception as ex:
                    print(f"⚠️ Failed to parse time for event(s): {ex}")
                    matching = []

                # cell = self.create_hour_cell(date, hour, matching)
                # if cell:
                #     self.add_widget(cell)
                # else:
                #     self.add_widget(Widget(size_hint=(1, 1)))  # invisible spacer
                self.add_widget(self.create_hour_cell(date, hour, matching))

    def create_hour_cell(self, date, hour, events):
        layout = FloatLayout()
        # if not events:
        #     return None

        # if hour == 0:
        #     # Optional: show day name at top row
        #     label = Label(
        #         text=date.strftime('%a\n%m/%d'),
        #         size_hint=(1, None),
        #         # pos_hint={'center_x': 0.5, 'center_y': 0.5},
        #         halign='center',
        #         valign='middle',
        #         markup=True,
        #         color=get_color_from_hex(self.text_color),
        #         height=30,
        #         pos_hint={'top': 1},
        #     )
        #     label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        #     layout.add_widget(label)

        for i, event in enumerate(events):
            label = Label(
                text=f"[color={self.text_color}]{event.title} @ {event.time} \nLocation: {event.location} "
                     f"\nNotes: {event.notes}[/color]",
                markup=True,
                size_hint=(1, None),
                halign='center',
                valign='middle',
                text_size=(None, None),
                height=70,
                pos_hint={'top': 0.9 - i * 0.3},
            )
            label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
            layout.add_widget(label)

        with layout.canvas.before:
            Color(1, 1, 1, 0.04) if events else Color(0, 0, 0, 0)  # only tint if there's something
            # Color(0.2, 0.2, 0.2, 0.1)  # light transparent fill to debug layout
            Rectangle(pos=layout.pos, size=layout.size)

            Color(*self.border_color)
            border = Line(rectangle=(0, 0, 0, 0), width=0.8)

        def update_border(*_):
            border.rectangle = (layout.x, layout.y, layout.width, layout.height)

        layout.bind(pos=update_border, size=update_border)
        layout.bind(size=lambda instance, value: setattr(instance, 'text_size', value))

        return layout
