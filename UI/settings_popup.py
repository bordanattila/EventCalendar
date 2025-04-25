from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex


def create_settings_popup(theme_manager, apply_callback, theme):
    """
    Constructs and returns a Settings Popup UI
    :param theme_manager: ThemeManager instance
    :param apply_callback: Function to call after settings are saved
    :param theme: Dict containing current theme colors
    :return: Kivy Popup instance.
    """
    popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)

    # Background color
    bg_color = get_color_from_hex(theme['bg_color'])
    text_color = get_color_from_hex(theme['text_color'])

    # Apply background rectangle
    with popup_layout.canvas.before:
        Color(*bg_color)
        bg_rect = RoundedRectangle(pos=popup_layout.pos, size=popup_layout.size, radius=[15])

    def update_bg(*_):
        bg_rect.pos = popup_layout.pos
        bg_rect.size = popup_layout.size

    popup_layout.bind(pos=update_bg, size=update_bg)

    # Title
    title_label = Label(
        text='[b]Settings[/b]',
        markup=True,
        font_size=20,
        size_hint_y=None,
        halign='center',
        valign='top',
        height=40,
        color=text_color,
    )
    popup_layout.add_widget(title_label)

    # Theme selection
    popup_layout.add_widget(Label(text='Select Theme:', size_hint_y=None, height=30, color=text_color))
    theme_spinner = Spinner(
        text=theme_manager.settings['preferred_theme'],
        values=list(theme_manager.themes.keys()),
        size_hint_y=None,
        height=44,
        background_color=get_color_from_hex(theme['button_color']),
        color=text_color,
    )
    popup_layout.add_widget(theme_spinner)

    # Auto Mode Toggle
    auto_popup_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=10)
    auto_popup_layout.add_widget(Label(text="Auto Mode (Light/Dark):", color=text_color, size_hint_x=0.7))
    auto_mode_switch = Switch(active=theme_manager.settings["auto_mode"], size_hint_x=0.3)
    auto_popup_layout.add_widget(auto_mode_switch)
    popup_layout.add_widget(auto_popup_layout)

    # Light Mode Start
    popup_layout.add_widget(Label(text='Light Mode Start (HH:MM):', size_hint_y=None, height=30, color=text_color))
    light_input = TextInput(
        text=theme_manager.settings['light_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    popup_layout.add_widget(light_input)

    # Dark Mode Start
    popup_layout.add_widget(Label(text='Dark Mode Start (HH:MM):', size_hint_y=None, height=30, color=text_color))
    dark_input = TextInput(
        text=theme_manager.settings['dark_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    popup_layout.add_widget(dark_input)

    # Save Button
    save_button = Button(
        text='Save and Apply',
        size_hint_y=None,
        height=50,
        color=text_color,
        background_normal='',
        background_color=get_color_from_hex(theme['button_color']),
    )
    popup_layout.add_widget(save_button)

    popup = Popup(title='', content=popup_layout, size_hint=(0.8, 0.8), background='')

    def toggle_spinner_state(*_):
        theme_spinner.disabled = auto_mode_switch.active

    def on_save_settings(instance):
        theme_manager.toggle_auto_mode(auto_mode_switch.active)
        theme_manager.set_custom_theme(theme_spinner.text)
        theme_manager.set_dark_light_times(light_input.text, dark_input.text)
        theme_manager.update_theme()
        popup.dismiss()
        apply_callback()  # Refresh UI

    auto_mode_switch.bind(active=toggle_spinner_state)
    save_button.bind(on_release=on_save_settings)
    toggle_spinner_state()

    return popup
