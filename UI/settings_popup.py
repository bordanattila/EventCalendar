from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from app.utils import create_themed_button


def create_settings_popup(theme_manager, apply_callback, theme):
    """
    Constructs and returns a Settings Popup UI
    :param theme_manager: ThemeManager instance
    :param apply_callback: Function to call after settings are saved
    :param theme: Dict containing current theme colors
    :return: Kivy Popup instance.
    """
    settings_popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)

    # Background color
    bg_color = get_color_from_hex(theme['bg_color'])
    text_color = get_color_from_hex(theme['text_color'])

    # Apply background rectangle
    with settings_popup_layout.canvas.before:
        Color(*bg_color)
        bg_rect = RoundedRectangle(pos=settings_popup_layout.pos, size=settings_popup_layout.size, radius=[15])

    def update_bg(*_):
        bg_rect.pos = settings_popup_layout.pos
        bg_rect.size = settings_popup_layout.size

    settings_popup_layout.bind(pos=update_bg, size=update_bg)

    # Theme selection
    settings_popup_layout.add_widget(Label(text='Select Theme:', size_hint_y=None, height=30, color=text_color))
    theme_spinner = Spinner(
        text=theme_manager.settings['preferred_theme'],
        values=list(theme_manager.themes.keys()),
        size_hint_y=None,
        height=44,
        background_normal='',
        background_color=get_color_from_hex(theme['button_color']),
        color=text_color,
    )
    settings_popup_layout.add_widget(theme_spinner)

    # Auto Mode Toggle
    auto_settings_popup_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=10)
    auto_settings_popup_layout.add_widget(Label(text="Auto Mode (Light/Dark):", color=text_color, size_hint_x=0.7))
    auto_mode_switch = Switch(active=theme_manager.settings["auto_mode"], size_hint_x=0.3)
    auto_settings_popup_layout.add_widget(auto_mode_switch)
    settings_popup_layout.add_widget(auto_settings_popup_layout)

    # Light Mode Start
    settings_popup_layout.add_widget(Label(text='Light Mode Start (HH:MM):', size_hint_y=None, height=30, color=text_color))
    light_input = TextInput(
        text=theme_manager.settings['light_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    settings_popup_layout.add_widget(light_input)

    # Dark Mode Start
    settings_popup_layout.add_widget(Label(text='Dark Mode Start (HH:MM):', size_hint_y=None, height=30, color=text_color))
    dark_input = TextInput(
        text=theme_manager.settings['dark_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    settings_popup_layout.add_widget(dark_input)

    popup = Popup(
        title='Settings',
        title_color=get_color_from_hex(theme['text_color']),
        title_align='center',
        content=settings_popup_layout,
        size_hint=(0.5, 0.5),
        background='',
        background_color=get_color_from_hex(theme['bg_color']),
        )

    def toggle_spinner_state(*_):
        theme_spinner.disabled = auto_mode_switch.active

    def on_save_settings(instance):
        theme_manager.toggle_auto_mode(auto_mode_switch.active)
        theme_manager.set_custom_theme(theme_spinner.text)
        theme_manager.set_dark_light_times(light_input.text, dark_input.text)
        theme_manager.update_theme()
        popup.dismiss()
        apply_callback()  # Refresh UI

    # Save Button
    save_button = create_themed_button('Save and Apply', theme, on_release=on_save_settings)
    settings_popup_layout.add_widget(save_button)

    auto_mode_switch.bind(active=toggle_spinner_state)
    save_button.bind()
    toggle_spinner_state()

    return popup
