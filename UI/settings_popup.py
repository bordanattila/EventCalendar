"""
settings_popup.py

Defines the themed settings popup for toggling auto light/dark mode, setting custom
theme preferences, adjusting light/dark start times, and triggering iCloud sync.
"""
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex

from app.ui_utils import create_themed_button
from UI.components.keyboard import VirtualKeyboard


def create_settings_popup(
    theme_manager,
    apply_callback,
    theme,
    get_last_sync_text=None,
    on_sync_now=None,
):
    """
    Constructs and returns a Settings Popup UI
    :param theme_manager: ThemeManager instance
    :param apply_callback: Function to call after settings are saved
    :param theme: Dict containing current theme colors
    :param get_last_sync_text: Optional callable returning last sync status text
    :param on_sync_now: Optional callable(on_done) to trigger iCloud sync
    :return: Kivy Popup instance.
    """
    scroll = ScrollView(size_hint=(1, 1))
    settings_area = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=20)
    settings_area.bind(minimum_height=settings_area.setter('height'))
    scroll.add_widget(settings_area)

    # Background color
    bg_color = get_color_from_hex(theme['bg_color'])
    text_color = get_color_from_hex(theme['text_color'])

    # Apply background rectangle
    with settings_area.canvas.before:
        Color(*bg_color)
        bg_rect = RoundedRectangle(pos=settings_area.pos, size=settings_area.size)

    def update_bg(*_):
        bg_rect.pos = settings_area.pos
        bg_rect.size = settings_area.size

    settings_area.bind(pos=update_bg, size=update_bg)

    # Theme selection
    settings_area.add_widget(Label(text='Select Theme:', size_hint_y=None, height=30, color=text_color))
    theme_spinner = Spinner(
        text=theme_manager.settings['preferred_theme'],
        values=list(theme_manager.themes.keys()),
        size_hint_y=None,
        height=44,
        background_normal='',
        background_color=get_color_from_hex(theme['button_color']),
        color=text_color,
    )
    settings_area.add_widget(theme_spinner)

    # Auto Mode Toggle
    auto_settings_area = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=10)
    auto_settings_area.add_widget(Label(text="Auto Mode (Light/Dark):", color=text_color, size_hint_x=0.7))
    auto_mode_switch = Switch(active=theme_manager.settings["auto_mode"], size_hint_x=0.3)
    auto_settings_area.add_widget(auto_mode_switch)
    settings_area.add_widget(auto_settings_area)

    # Light Mode Start
    settings_area.add_widget(Label(text='Light Mode Start (HH:MM):', size_hint_y=None, height=30, color=text_color))
    light_input = TextInput(
        text=theme_manager.settings['light_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    settings_area.add_widget(light_input)

    # Dark Mode Start
    settings_area.add_widget(Label(text='Dark Mode Start (HH:MM):', size_hint_y=None, height=30,
                                           color=text_color))
    dark_input = TextInput(
        text=theme_manager.settings['dark_start'],
        hint_text='HH:MM',
        multiline=False,
        size_hint_y=None,
        height=44
    )
    settings_area.add_widget(dark_input)

    sync_status_label = None
    sync_button = None
    if on_sync_now is not None:
        settings_area.add_widget(
            Label(
                text="[b]iCloud Sync[/b]",
                markup=True,
                size_hint_y=None,
                height=30,
                color=text_color,
            )
        )
        initial_status = get_last_sync_text() if get_last_sync_text else "Never synced"
        sync_status_label = Label(
            text=initial_status,
            size_hint_y=None,
            height=40,
            color=text_color,
            halign="left",
            valign="middle",
        )
        sync_status_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        settings_area.add_widget(sync_status_label)

        sync_layout, sync_button = create_themed_button(
            "Sync Now",
            theme,
            return_button=True,
        )
        settings_area.add_widget(sync_layout)

    settings_popup_layout = BoxLayout(orientation='vertical')
    settings_popup_layout.add_widget(scroll)

    vk = VirtualKeyboard(size_hint_y=None, height=200)
    vk.register_inputs(light_input, dark_input)
    settings_popup_layout.add_widget(vk)

    popup = Popup(
        title='Settings',
        title_color=get_color_from_hex(theme['text_color']),
        title_align='center',
        content=settings_popup_layout,
        size_hint=(0.5, 0.7),
        background='',
        background_color=get_color_from_hex(theme['bg_color']),
        auto_dismiss=False,
        )

    def block_extra_touches(instance, touch):
        if instance.collide_point(*touch.pos):
            print(f"[DEBUG] Touch inside popup at {touch.pos}")
            return False  # Let Kivy continue handling the event
        return False

    popup.bind(on_touch_down=block_extra_touches)

    def refresh_sync_status(success: bool, message: str) -> None:
        if sync_button is not None:
            sync_button.disabled = False
        if sync_status_label is None:
            return
        if get_last_sync_text and success:
            sync_status_label.text = get_last_sync_text()
        else:
            sync_status_label.text = message

    def on_sync_pressed(_instance):
        if sync_button is not None:
            sync_button.disabled = True
        if sync_status_label is not None:
            sync_status_label.text = "Syncing with iCloud..."

        def done(success, message):
            Clock.schedule_once(lambda _dt: refresh_sync_status(success, message), 0)

        on_sync_now(done)

    if sync_button is not None:
        sync_button.bind(on_release=on_sync_pressed)

    def toggle_spinner_state(*_):
        theme_spinner.disabled = auto_mode_switch.active

    def on_save_settings(instance):
        # Update theme settings and apply immediately
        theme_manager.toggle_auto_mode(auto_mode_switch.active)
        theme_manager.set_custom_theme(theme_spinner.text)
        theme_manager.set_dark_light_times(light_input.text, dark_input.text)
        theme_manager.update_theme()
        popup.dismiss()
        apply_callback()  # Refresh UI

    # Cancel Button
    cancel_button = create_themed_button('Cancel', theme, on_release=popup.dismiss)

    # Save Button
    save_button = create_themed_button('Save and Apply', theme, on_release=on_save_settings)

    button_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
    button_box.add_widget(cancel_button)
    button_box.add_widget(save_button)
    settings_popup_layout.add_widget(button_box)

    auto_mode_switch.bind(active=toggle_spinner_state)
    toggle_spinner_state()

    return popup
