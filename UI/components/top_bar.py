"""
top_bar.py

Defines the top status bar for the Family Calendar application.

Displays:
- Live time and date
- Current day of the week
- Real-time weather icon and temperature

Author: Attila Bordan
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.image import AsyncImage

from app.utils import get_time, get_date, get_day
from app.api_utils import get_location, get_weather


class TopBar(BoxLayout):
    """
    A horizontal bar that displays the current time, date, weekday,
    and real-time weather info (icon + temperature).

    Automatically refreshes:
    - Time every second
    - Weather once every hour
    """
    def __init__(self, theme, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = 0.08
        self.padding = [20, 10]
        self.spacing = 20
        self.theme = theme
        self.text_color = self.theme['text_color']

        # Get initial time and date
        self.current_time = str(get_time())
        self.current_day = str(get_day())
        self.current_date = str(get_date())

        # Weather icon and temperature
        self.weather_label = Label(text="", size_hint=(None, 1), width=60, halign='left', markup=True,
                                   font_size='20sp',)
        self.weather_icon = AsyncImage(size_hint=(None, 1), width=50)

        self.add_widget(self.weather_icon)
        self.add_widget(self.weather_label)

        # Base style for time/date/day labels
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

        # Update time every second
        Clock.schedule_interval(self.update_time, 1)
        # Update weather once after 1s, then every 30 minutes
        Clock.schedule_once(lambda dt: self.update_weather(), 1)
        Clock.schedule_interval(lambda dt: self.update_weather(), 1800)

    def update_time(self, dt):
        """Refreshes the time label once per second."""
        self.current_time = str(get_time())
        self.time_label.text = f"[b][color={self.text_color}]{self.current_time}[/color][/b]"

    def update_weather(self):
        """Fetches weather info using location and updates label/icon."""
        lat, lon, city = get_location()
        if lat and lon:
            celsius, fahrenheit, icon = get_weather(lat, lon)
            if celsius is not None and icon:
                self.weather_label.text = f"[b][color={self.text_color}]{celsius}°C / {fahrenheit}°F[/color][/b]"
                self.weather_icon.source = f"http://openweathermap.org/img/wn/{icon}.png"
            else:
                self.weather_label.text = ""
                self.weather_icon.source = "assets/default_weather.png"  # Optional fallback
        else:
            self.weather_label.text = ""
            self.weather_icon.source = "assets/default_weather.png"
