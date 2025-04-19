from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
import datetime

from app.utils import get_time, get_date, get_day


class TopBar(BoxLayout):
    def __init__(self, theme, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = 0.08
        self.padding = [20, 10]
        self.spacing = 20
        self.theme = theme

        self.text_color = self.theme['text_color']

        self.current_time = str(get_time())
        self.current_day = str(get_day())
        self.current_date = str(get_date())

        label_style = {
            'markup': True,
            'font_size': '20sp',
            'halign': 'center',
            'valign': 'middle',
        }

        logo = Image(
            source='assets/logo.png',
            size_hint=(None, None),
            size=(60, 60),
            allow_stretch=True,
            keep_ratio=True,
            pos_hint={'x': 0, 'top': 1.05},
        )
        self.add_widget(logo)

        self.time_label = Label(
            text=f"[b][color={self.text_color}]{self.current_time}[/color][/b]",
            **label_style
        )
        self.day_label = Label(
            text=f"[b][color={self.text_color}]{self.current_day}[/color][/b]",
            **label_style
        )
        self.date_label = Label(
            text=f"[b][color={self.text_color}]{self.current_date}[/color][/b]",
            **label_style
        )

        self.add_widget(self.time_label)
        self.add_widget(self.day_label)
        self.add_widget(self.date_label)

        Clock.schedule_interval(self.update_time, 1)

    def update_time(self, dt):
        self.current_time = str(get_time())
        self.time_label.text = f"[b][color={self.text_color}]{self.current_time}[/color][/b]"
