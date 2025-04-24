from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex


class WeekdayHeader(GridLayout):
    def __init__(self, **kwargs):
        theme = kwargs.pop('theme')
        theme_manager = kwargs.pop('theme_manager')
        dark_mode = kwargs.pop('dark_mode')

        is_weekly_view = kwargs.pop('is_weekly_view', False)
        week_dates = kwargs.pop('week_dates', None)

        super().__init__(**kwargs)

        self.theme = theme
        self.theme_manager = theme_manager
        self.dark_mode = dark_mode
        self.cols = 7
        self.size_hint_y = 0.05

        self.is_weekly_view = is_weekly_view
        self.week_dates = week_dates

        self.build_header()

    def build_header(self):
        days_with_colors = [
            ('Sun', '#FFB347'),  # Soft Amber – warm, energetic, and bright
            ('Mon', '#6ECEDA'),  # Aqua Mist – calm, clean, and refreshing
            ('Tue', '#FF6B6B'),  # Coral – bold, emotional, and attention-grabbing
            ('Wed', '#A2D95E'),  # Spring Green – natural, balanced, and fresh
            ('Thu', '#F9E55D'),  # Lemon – optimistic, light, and cheerful
            ('Fri', '#F8A5C2'),  # Blush Pink – fun, soft, and celebratory
            ('Sat', '#B39DDB')  # Lavender – relaxed, dreamy, and mellow
        ]

        # If we're in weekly view and have the week dates
        if self.is_weekly_view and self.week_dates and len(self.week_dates) == 7:
            # Use the week dates to create headers with date numbers
            for i, (day_name, bg_color_light) in enumerate(days_with_colors):
                date = self.week_dates[i]
                day_text = f"{day_name} {date.day}"  # e.g., "Sun 20"
                self._create_header_box(day_text, bg_color_light)
        else:
            # Regular monthly view - just day names
            for day_name, bg_color_light in days_with_colors:
                self._create_header_box(day_name, bg_color_light)

    def _create_header_box(self, day_text, bg_color_light):
        """Helper method to create a single header box"""
        box = BoxLayout()
        bg_color = get_color_from_hex(bg_color_light)
        if self.theme_manager.settings.get('auto_mode') and self.dark_mode:
            bg_color = self.theme['bg_color']
        with box.canvas.before:
            Color(*bg_color)
            rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[0])

        def make_updater(widget, rect):
            def update(*_):
                rect.pos = widget.pos
                rect.size = widget.size

            return update

        box.bind(pos=make_updater(box, rect), size=make_updater(box, rect))
        label = Label(
            text=f"[b][color={bg_color_light if self.dark_mode else self.theme['text_color']}]{day_text}[/color][/b]",
            markup=True
        )
        box.add_widget(label)
        self.add_widget(box)

    def update_weekly_dates(self, new_week_dates):
        """Update the header with a new list of dates for weekly view."""
        self.week_dates = new_week_dates
        self.clear_widgets()
        self.build_header()

