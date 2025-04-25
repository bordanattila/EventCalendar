from kivy.uix.gridlayout import GridLayout
from app.utils import create_themed_button


class NavButtons(GridLayout):
    def __init__(self, theme, on_prev, on_next, is_weekly_view=False, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.size_hint_y = 0.06
        self.spacing = 50
        self.padding = [50, 0, 50, 10]
        self.theme = theme

        self.is_weekly_view = is_weekly_view

        # Button text depends on current view
        prev_text = '<< Previous Week' if self.is_weekly_view else '<< Previous Month'
        next_text = 'Next Week >>' if self.is_weekly_view else 'Next Month >>'

        self.prev_button = create_themed_button(prev_text, self.theme, on_prev)
        self.next_button = create_themed_button(next_text, self.theme, on_next)

        self.add_widget(self.prev_button)
        self.add_widget(self.next_button)

    # Update navigation button text
    def update_button_text(self, is_weekly_view):
        self.is_weekly_view = is_weekly_view

        prev_text = '<< Previous Week' if self.is_weekly_view else '<< Previous Month'
        next_text = 'Next Week >>' if self.is_weekly_view else 'Next Month >>'

        self.prev_button.children[0].text = prev_text
        self.next_button.children[0].text = next_text
