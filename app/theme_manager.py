"""
Theme Manager Module
--------------------
Handles theme selection and management for the Family Calendar application.

Features:
- Predefined color themes with light/dark modes and seasonal variants.
- Automatic switching between themes based on time.
- Persistent user settings stored in JSON.
- Manual override and custom time ranges for light/dark themes.

Author: Attila Bordan
"""
import datetime
import json
import os


class ThemeManager:
    """
    Manages application themes, including auto-switching logic,
    user overrides, and persistent preferences.
    """
    SETTINGS_FILE = 'theme_settings.json'

    def __init__(self):

        # Predefined theme styles with color settings for UI elements
        self.themes = {
            'Light': {
                'bg_color': '#FFEFD5',
                'text_color': '#000000',
                'border_color': '#000000',
                'button_color': '#DADADA',
                'cell_color': '#E5E5E5',
                'button_border_color': '#B3B3B3',
                'popup_border_color': '#333333',
                'nav_button_color': '#DADADA',
                'input_bg_color': '#FFEFD5',
                'time_color': '#D2691E',
                'title_color': '#222222',
                'location_color': '#555555',
                'notes_color': '#777777',
                "scrollbar_color": "#66d9ed",
                "scrollbar_inactive_color": "#cccccc",
            },
            'Dark': {
                'bg_color': '#1A1A1A',
                'text_color': '#FFFFFF',
                'border_color': '#FFFFFF',
                'button_color': '#444444',
                'cell_color': '#333333',
                'button_border_color': '#666666',
                'popup_border_color': '#333333',
                'nav_button_color': '#444444',
                'input_bg_color': '#444444',
                'time_color': '#FFC107',
                'title_color': '#FFFFFF',
                'location_color': '#AAAAAA',
                'notes_color': '#888888',
                "scrollbar_color": "#A6F6FF",
                "scrollbar_inactive_color": "#444444",
            },
            'Blueberry': {
                'bg_color': '#334080',
                'text_color': '#EEEEEE',
                'border_color': '#CCDDFF',
                'button_color': '#4B5FA3',
                'cell_color': '#4B5FA3',
                'button_border_color': '#8FA3E0',
                'popup_border_color': '#222222',
                'nav_button_color': '#3C4F94',
                'input_bg_color': '#4B5FA3',
                'time_color': '#FFC107',
                'title_color': '#EEEEEE',
                'location_color': '#AAAAAA',
                'notes_color': '#888888',
                "scrollbar_color": "#9EDDFF",
                "scrollbar_inactive_color": "#333344",
            },
            'Sunset': {
                'bg_color': '#FFDAB3',
                'text_color': '#222222',
                'border_color': '#CC5522',
                'button_color': '#FFB7A2',
                'cell_color': '#FFB380',
                'button_border_color': '#CC704D',
                'popup_border_color': '#333333',
                'nav_button_color': '#FFA07A',
                'input_bg_color': '#FFDAB3',
                'time_color': '#C1440E',
                'title_color': '#222222',
                'location_color': '#5C3B1E',
                'notes_color': '#7A5C4F',
                "scrollbar_color": "#FFB347",
                "scrollbar_inactive_color": "#704214",
            }
        }

        # Default settings used if no config file exists
        self.settings = {
            'auto_mode': True,
            'dark_start': '20:00',
            'light_start': '07:00',
            'preferred_theme': 'Light',  # used if auto_mode is false
            'active_theme': 'Light'  # gets dynamically updated
        }

        # Load saved settings if present
        self.load_settings()

        # Apply current theme based on settings
        self.update_theme()

    def load_settings(self):
        """Loads user theme preferences from a JSON file if available."""
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                print(f'Error loading theme settings: {e}')

    def save_settings(self):
        """Saves user theme preferences to a JSON file."""
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f'Error saving theme settings: {e}')

    def get_theme(self):
        """
        Returns the currently active theme's color dictionary.

        :return: dict of color values for UI elements.
        """
        return self.themes[self.settings['active_theme']]

    def update_theme(self):
        """
        Sets the active theme based on auto mode or preferred user selection.

        In auto mode, the app switches between light and dark themes
        based on the current system time and user-defined thresholds.
        """
        if self.settings['auto_mode']:
            now = datetime.datetime.now().time()
            dark_start = datetime.datetime.strptime(self.settings['dark_start'], '%H:%M').time()
            light_start = datetime.datetime.strptime(self.settings['light_start'], '%H:%M').time()

            if light_start <= now < dark_start:
                self.settings['active_theme'] = self.settings['preferred_theme']
            else:
                self.settings['active_theme'] = 'Dark'
        else:
            self.settings['active_theme'] = self.settings['preferred_theme']

    def toggle_auto_mode(self, enabled: bool):
        """
        Enables or disables automatic light/dark mode switching.

        :param enabled: True to enable auto mode, False to disable.
        """
        self.settings['auto_mode'] = enabled
        self.update_theme()
        self.save_settings()

    def set_custom_theme(self, theme_name: str):
        """
         Sets a user-selected theme manually.

        :param theme_name: Name of the theme from the available themes.
        """
        if theme_name in self.themes:
            self.settings['preferred_theme'] = theme_name
            self.update_theme()
            self.save_settings()

    def set_dark_light_times(self, light_time: str, dark_time: str):
        """
        Configures custom switching times for light and dark modes.

        :param light_time: Start time for light mode (HH:MM format).
        :param dark_time: Start time for dark mode (HH:MM format).
        """
        self.settings['light_start'] = light_time
        self.settings['dark_start'] = dark_time
        self.update_theme()
        self.save_settings()
