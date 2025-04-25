from kivy.uix.gridlayout import GridLayout
from app.utils import create_themed_button


class BottomBar(GridLayout):
    def __init__(self, theme, on_add_event, on_toggle_view, on_show_settings, is_weekly_view=False, **kwargs):
        super().__init__(**kwargs)
        self.cols = 3
        self.size_hint_y = 0.06
        self.spacing = 50
        self.padding = [50, 15, 50, 10]
        self.theme = theme
        self.is_weekly_view = is_weekly_view

        # Toggle view button text based on current view
        view_button_text = 'Monthly View' if self.is_weekly_view else 'Weekly View'
        self.toggle_view_button = create_themed_button(view_button_text, self.theme, on_press=on_toggle_view)
        self.add_event_button = create_themed_button('+ Add Event', self.theme, on_press=on_add_event)
        self.settings_button = create_themed_button('Settings', self.theme, on_press=on_show_settings)

        self.add_widget(self.toggle_view_button)
        self.add_widget(self.add_event_button)
        self.add_widget(self.settings_button)

    # Update toggle button text
    def update_view_button_text(self, is_weekly_view):
        self.is_weekly_view = is_weekly_view
        view_button_text = 'Monthly View' if self.is_weekly_view else 'Weekly View'
        self.toggle_view_button.children[0].text = view_button_text
