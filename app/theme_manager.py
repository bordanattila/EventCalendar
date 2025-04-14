import datetime
import json
import os


class ThemeManager:
    """
    Manages application themes, including auto-switching logic,
    user overrides, and persistent performances.
    """
    SETTINGS_FILE = 'theme_settings.json'

    def __init__(self):

        # Define available themes
        self.themes = {
            'light': {
                'bg_color': '#FFEFD5',
                'text_color': '#000000',
                'border_color': '#000000',
                'button_color': '#DADADA',
                'cell_color': '#E5E5E5',
                'button_border_color': '#B3B3B3',
                'popup_border_color': '#333333',
                'nav_button_color': '#DADADA',
                'input_bg_color': '#FFEFD5',
            },
            'dark': {
                'bg_color': '#1A1A1A',
                'text_color': '#FFFFFF',
                'border_color': '#FFFFFF',
                'button_color': '#444444',
                'cell_color': '#333333',
                'button_border_color': '#666666',
                'popup_border_color': '#333333',
                'nav_button_color': '#444444',
                'input_bg_color': '#444444',
            },
            'blueberry': {
                'bg_color': '#334080',
                'text_color': '#EEEEEE',
                'border_color': '#CCDDFF',
                'button_color': '#4B5FA3',
                'cell_color': '#4B5FA3',
                'button_border_color': '#8FA3E0',
                'popup_border_color': '#222222',
                'nav_button_color': '#3C4F94',
                'input_bg_color': '#4B5FA3',
            },
            'sunset': {
                'bg_color': '#FFDAB3',
                'text_color': '#222222',
                'border_color': '#CC5522',
                'button_color': '#FFB7A2',
                'cell_color': '#FFB380',
                'button_border_color': '#CC704D',
                'popup_border_color': '#333333',
                'nav_button_color': '#FFA07A',
                'input_bg_color': '#FFDAB3',
            }
        }

        # Default user settings
        self.settings = {
            'auto_mode': True,
            'dark_start': '20:00',
            'light_start': '07:00',
            'preferred_theme': 'light',  # used if auto_mode is false
            'active_theme': 'light'  # updated dynamically
        }

        # Load saved settings if present
        self.load_settings()

        # Apply current theme based on settings
        self.update_theme()

    def load_settings(self):
        """Loads user settings from disk if file exists."""
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                print(f'Error loading theme settings: {e}')

    def save_settings(self):
        """"Saves user settings to disk."""
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f'Error saving theme settings: {e}')

    def get_theme(self):
        """Returns the currently active theme dictionary."""
        return self.themes[self.settings['active_theme']]

    def update_theme(self):
        """Determines and sets the appropriate theme."""
        if self.settings['auto_mode']:
            now = datetime.datetime.now().time()
            dark_start = datetime.datetime.strptime(self.settings['dark_start'], '%H:%M').time()
            light_start = datetime.datetime.strptime(self.settings['light_start'], '%H:%M').time()

            if light_start <= now < dark_start:
                self.settings['active_theme'] = 'light'
            else:
                self.settings['active_theme'] = 'dark'
        else:
            self.settings['active_theme'] = self.settings['preferred_theme']

    def toggle_auto_mode(self, enabled: bool):
        """Enable or disable auto dark/light mode."""
        self.settings['auto_mode'] = enabled
        self.update_theme()
        self.save_settings()

    def set_custom_theme(self, theme_name: str):
        """Sets a custom theme by name."""
        if theme_name in self.themes:
            self.settings['preferred_theme'] = theme_name
            self.update_theme()
            self.save_settings()

    def set_dark_light_times(self, light_time: str, dark_time: str):
        """Sets custom times for light and dark mode switching."""
        self.settings['light_start'] = light_time
        self.settings['dark_start'] = dark_time
        self.update_theme()
        self.save_settings()
