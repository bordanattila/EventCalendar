from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex


class NavButtons(GridLayout):
    def __init__(self, theme, on_prev, on_next, is_weekly_view=False, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.size_hint_y = 0.06
        self.spacing = 50
        self.padding = [50, 0, 50, 10]
        self.theme = theme

        self.is_weekly_view = is_weekly_view

        # Button text depends on current view
        prev_text = '<< Previous Week' if self.is_weekly_view else '<< Previous Month'
        next_text = 'Next Week >>' if self.is_weekly_view else 'Next Month >>'

        self.prev_button = self.create_button(prev_text, on_prev)
        self.next_button = self.create_button(next_text, on_next)

        self.add_widget(self.prev_button)
        self.add_widget(self.next_button)

    # Update navigation button text
    def update_button_text(self, is_weekly_view):
        self.is_weekly_view = is_weekly_view

        prev_text = '<< Previous Week' if self.is_weekly_view else '<< Previous Month'
        next_text = 'Next Week >>' if self.is_weekly_view else 'Next Month >>'

        self.prev_button.children[0].text = prev_text
        self.next_button.children[0].text = next_text

    def create_button(self, text, callback, bg_override=None, font_override=None):
        """
        Creates a themed button with a border and proper background.
        Returns a BoxLayout containing the styled button.
        """

        box = BoxLayout(size_hint=(1, 1), height=50, spacing=5, padding=[10, 0])

        with box.canvas.before:
            # Shadow
            Color(0, 0, 0, 0, 0.25)
            shadow = RoundedRectangle(pos=(box.x + 2, box.y - 2), size=box.size, radius=[10])

            # Background fill
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
        button.bind(on_press=callback)

        box.add_widget(button)
        return box
