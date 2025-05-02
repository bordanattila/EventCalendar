"""
ui_utils.py

Reusable UI components and helpers for the Family Calendar app.
Includes methods for creating stylized Kivy widgets using the active theme.

Author: Attila Bordan
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex

import time
import platform

is_raspberry_pi = platform.machine().startswith('arm')


def create_themed_button(text, theme, on_press=None, bg_override=None, font_override=None, on_release=None,
                         return_button=False):
    """
    Creates a styled button embedded in a BoxLayout using the provided theme.

    Args:
        text (str): The text displayed on the button.
        theme (dict): A dictionary of theme colors.
        on_press (callable, optional): Function to call on press.
        on_release (callable, optional): Function to call on release.
        bg_override (str, optional): Optional background hex color.
        font_override (str, optional): Optional font name.

    Returns:
        BoxLayout: The layout containing the styled button.
    """
    box = BoxLayout(
        size_hint=(1, None),
        height=35,
        spacing=5,
        padding=[10, 0],
    )

    # Draw custom canvas background with shadow and rounded corners
    with box.canvas.before:
        Color(0, 0, 0, 0.25)
        shadow = RoundedRectangle(pos=(box.x + 2, box.y - 2), size=box.size, radius=[10])

        Color(*get_color_from_hex(bg_override or theme['button_color']))
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
        background_color=get_color_from_hex(bg_override or theme['button_color']),
        color=get_color_from_hex(theme['text_color']),
        size_hint=(1, 1),
        halign='center',
        valign='middle',
        font_name=font_override if font_override else 'Roboto',
    )
    button.text_size = (None, None)

    def debug_touch(instance, touch):
        print(f"DEBUG: on_touch_down @ {time.time()} on {instance.text}")
        return False  # let event continue

    button.bind(on_touch_down=debug_touch)

    if on_press:
        button.bind(on_press=on_press)
    if on_release:
        button.bind(on_release=on_release)

    box.add_widget(button)

    return (box, button) if return_button else box
