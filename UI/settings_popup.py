from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.button import Button


def create_settings_popup(theme_manager, apply_callback):
    """
    Constructs and returns a Settings Popup UI.

    :param theme_manager: ThemeManager instance.
    :param apply_callback: Function to call after settings are saved.
    :return: Kivy Popup instance.
    """
    layout = BoxLayout(orientation='vertical', spacing=10, padding=20)

    # Theme selection
    layout.add_widget(Label(text='Select Theme:', size_hint_y=None, height=30))
    theme_spinner = Spinner(
        text=theme_manager.settings['preferred_theme'],
        values=list(theme_manager.themes.keys()),
        size_hint_y=None,
        height=44
    )
    layout.add_widget(theme_spinner)

    # Auto Mode Toggle
    auto_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=10)
    auto_layout.add_widget(Label(text="Auto Light/Dark Mode:", size_hint_x=0.7))
    auto_mode_switch = Switch(active=theme_manager.settings["auto_mode"], size_hint_x=0.3)
    auto_layout.add_widget(auto_mode_switch)
    layout.add_widget(auto_layout)

    # Light Mode Start
    layout.add_widget(Label(text='Light Mode Start (HH:MM):', size_hint_y=None, height=30))
    light_input = TextInput(
        text=theme_manager.settings['light_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    layout.add_widget(light_input)

    # Dark Mode Start
    layout.add_widget(Label(text='Dark Mode Start (HH:MM):', size_hint_y=None, height=30))
    dark_input = TextInput(
        text=theme_manager.settings['dark_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    layout.add_widget(dark_input)

    # Save Button
    save_button = Button(text='Save and Apply', size_hint_y=None, height=50)
    layout.add_widget(save_button)

    popup = Popup(title='Settings', content=layout, size_hint=(0.8, 0.8))

    def toggle_spinner_state(*args):
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
