"""
nav_buttons.py

Defines a navigation bar component with "Previous" and "Next" buttons for
navigating between months or weeks in the Family Calendar app.

Button labels dynamically change based on whether the calendar is in
weekly or monthly view.

Author: Attila Bordan
"""
from kivy.uix.gridlayout import GridLayout
from app.ui_utils import create_themed_button


class NavButtons(GridLayout):
    """
    Navigation button group for moving between calendar views.

    Displays:
    - "<< Previous Week" or "<< Previous Month"
    - "Next Week >>" or "Next Month >>"

    Args:
        theme (dict): The currently active theme.
        on_prev (callable): Callback when "Previous" is pressed.
        on_next (callable): Callback when "Next" is pressed.
        is_weekly_view (bool): Determines initial view mode.
    """
    def __init__(self, theme, on_prev, on_next, is_weekly_view=False, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.size_hint_y = 0.06
        self.spacing = 50
        self.padding = [50, 0, 50, 10]
        self.theme = theme

        self.is_weekly_view = is_weekly_view

        # Button text depends on whether we're in weekly or monthly view
        prev_text = '<< Previous Week' if self.is_weekly_view else '<< Previous Month'
        next_text = 'Next Week >>' if self.is_weekly_view else 'Next Month >>'

        # Create buttons using the shared theming utility
        prev_layout, prev_btn = create_themed_button(prev_text, self.theme, on_release=on_prev, return_button=True)
        next_layout, next_btn = create_themed_button(next_text, self.theme, on_release=on_next, return_button=True)

        self.prev_button = prev_btn
        self.next_button = next_btn

        self.add_widget(prev_layout)
        self.add_widget(next_layout)

    def update_button_text(self, is_weekly_view):
        """
        Updates the navigation button labels based on view mode.

        Args:
            is_weekly_view (bool): Whether the calendar is in weekly view.
        """
        self.is_weekly_view = is_weekly_view

        prev_text = '<< Previous Week' if self.is_weekly_view else '<< Previous Month'
        next_text = 'Next Week >>' if self.is_weekly_view else 'Next Month >>'

        self.prev_button.text = prev_text
        self.next_button.text = next_text

