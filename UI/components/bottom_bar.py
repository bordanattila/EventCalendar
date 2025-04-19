from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex


class BottomBar(GridLayout):
    def __init__(self, theme, on_add_event, on_toggle_view, on_show_settings, **kwargs):
        super().__init__(**kwargs)
        self.cols = 3
        self.size_hint_y = 0.06
        self.spacing = 50
        self.padding = [50, 15, 50, 10]
        self.theme = theme

        self.add_widget(self.themed_button('Weekly View', on_toggle_view))
        self.add_widget(self.themed_button('+ Add Event', on_add_event))
        self.add_widget(self.themed_button('Settings', on_show_settings))

    def themed_button(self, text, on_press=None, bg_override=None, font_override=None):
        box = BoxLayout(size_hint=(1, 1), height=50, spacing=5, padding=[10, 0])

        with box.canvas.before:
            Color(0, 0, 0, 0.25)
            shadow = RoundedRectangle(pos=(box.x + 2, box.y - 2), size=box.size, radius=[10])
            Color(*get_color_from_hex(bg_override or self.theme['button_color']))
            button_bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[10])

        def update_graphics(*_):
            shadow.pos = (box.x + 2, box.y - 2)
            shadow.size = box.size
            button_bg.pos = box.pos
            button_bg.size = box.size

        box.bind(pos=update_graphics, size=update_graphics)

        button = Button(
            text=text,
            background_normal='',
            background_color=get_color_from_hex(bg_override or self.theme['button_color']),
            color=get_color_from_hex(self.theme['text_color']),
            size_hint=(1, 1),
            halign='center',
            valign='middle',
            font_name=font_override if font_override else 'Roboto',
        )
        button.text_size = (None, None)

        if on_press:
            button.bind(on_press=on_press)

        box.add_widget(button)
        return box
