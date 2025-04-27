from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.image import AsyncImage

from app.utils import get_time, get_date, get_day, get_location, get_weather


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

        self.weather_label = Label(text="", size_hint=(None, 1), width=60, halign='left', markup=True,
                                   font_size='20sp',)
        self.weather_icon = AsyncImage(size_hint=(None, 1), width=50)

        self.add_widget(self.weather_icon)
        self.add_widget(self.weather_label)

        label_style = {
            'markup': True,
            'font_size': '20sp',
            'halign': 'center',
            'valign': 'middle',
        }

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
        Clock.schedule_once(lambda dt: self.update_weather(), 1)
        Clock.schedule_interval(lambda dt: self.update_weather(), 3600)

    def update_time(self, dt):
        self.current_time = str(get_time())
        self.time_label.text = f"[b][color={self.text_color}]{self.current_time}[/color][/b]"

    def update_weather(self):
        lat, lon, city = get_location()
        if lat and lon:
            temp, icon = get_weather(lat, lon)
            if temp and icon:
                self.weather_label.text = f"[b][color={self.text_color}]{temp}°C[/color][/b]"
                self.weather_icon.source = f"http://openweathermap.org/img/wn/{icon}.png"
