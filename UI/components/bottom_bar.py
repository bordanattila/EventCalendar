"""
bottom_bar.py

Defines a reusable bottom navigation bar for the Family Calendar app.

Includes buttons to:
- Toggle between weekly and monthly views
- Add a new event
- Open the settings popup

Author: Attila Bordan
"""
from kivy.uix.gridlayout import GridLayout
from app.ui_utils import create_themed_button


class BottomBar(GridLayout):
    """
    A themed bottom navigation bar with three buttons:
    - Toggle View: Switches between weekly and monthly calendar views.
    - Add Event: Opens the Add Event popup.
    - Settings: Opens the settings panel.

    Args:
        theme (dict): The active theme dictionary.
        on_add_event (callable): Callback for the Add Event button.
        on_toggle_view (callable): Callback for the Toggle View button.
        on_show_settings (callable): Callback for the Settings button.
        is_weekly_view (bool): Indicates whether the current view is weekly or monthly.
    """
    def __init__(self, theme, on_add_event, on_toggle_view, on_show_settings, is_weekly_view=False, **kwargs):
        super().__init__(**kwargs)
        self.cols = 3
        self.size_hint_y = 0.06
        self.spacing = 50
        self.padding = [50, 15, 50, 10]
        self.theme = theme
        self.is_weekly_view = is_weekly_view

        # Determine button label based on current view
        view_button_text = 'Monthly View' if self.is_weekly_view else 'Weekly View'

        # Create buttons using the shared themed button factory
        toggle_layout, toggle_btn = create_themed_button(view_button_text, self.theme, on_press=on_toggle_view,
                                                         return_button=True)
        self.toggle_view_button = toggle_btn
        self.add_widget(toggle_layout)
        add_layout, _ = create_themed_button('+ Add Event', self.theme, on_press=on_add_event, return_button=True)
        settings_layout, _ = create_themed_button('Settings', self.theme, on_press=on_show_settings, return_button=True)

        # Add buttons to the grid layout
        self.add_widget(add_layout)
        self.add_widget(settings_layout)

    def update_view_button_text(self, is_weekly_view):
        """
        Updates the toggle view button label when switching between views.

        Args:
            is_weekly_view (bool): Whether the current view is weekly.
        """
        self.is_weekly_view = is_weekly_view
        view_button_text = 'Monthly View' if self.is_weekly_view else 'Weekly View'
        if self.toggle_view_button.children:
            self.toggle_view_button.text = view_button_text

