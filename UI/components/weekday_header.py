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
        super().__init__(**kwargs)

        self.theme = theme
        self.theme_manager = theme_manager
        self.dark_mode = dark_mode
        self.cols = 7
        self.size_hint_y = 0.05

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

        for day, bg_color_light in days_with_colors:
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
                text=f"[b][color={bg_color_light if self.dark_mode else self.theme['text_color']}]{day}[/color][/b]",
                markup=True
            )
            box.add_widget(label)
            self.add_widget(box)