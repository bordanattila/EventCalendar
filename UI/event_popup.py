"""
event_popup.py

Popup class for adding a new calendar event.
Includes required fields: title, date, time.
Optional fields: location, notes.
"""

from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout


class AddEventPopup(Popup):
    def __init__(self, on_save_callback=None, theme=None, **kwargs):
        super().__init__(**kwargs)
        self.title = "Add Event"
        self.size_hint = (0.85, 0.85)
        self.on_save_callback = on_save_callback
        self.theme = theme or {}

        layout = GridLayout(cols=2, spacing=10, padding=20, row_force_default=True, row_default_height=40)

        # Required fields
        layout.add_widget(Label(text="Title:*"))
        self.title_input = TextInput(multiline=False)
        layout.add_widget(self.title_input)

        layout.add_widget(Label(text="Date:* (YYYY-MM-DD)"))
        self.date_input = TextInput(multiline=False)
        layout.add_widget(self.date_input)

        layout.add_widget(Label(text="Time:* (HH:MM)"))
        self.time_input = TextInput(multiline=False)
        layout.add_widget(self.time_input)

        # Optional fields
        layout.add_widget(Label(text="Location:"))
        self.location_input = TextInput(multiline=False)
        layout.add_widget(self.location_input)

        layout.add_widget(Label(text="Notes:"))
        self.notes_input = TextInput(multiline=True)
        layout.add_widget(self.notes_input)

        # Spacer
        layout.add_widget(Label())
        layout.add_widget(Label())

        # Buttons
        button_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)

        save_btn = Button(
            text="Save",
            background_normal='',
            background_color=self.theme.get("button_color", (0.9, 0.9, 0.9, 1)),
            color=self.theme.get("text_color", "#000000")
        )
        cancel_btn = Button(
            text="Cancel",
            background_normal='',
            background_color=self.theme.get("button_color", (0.9, 0.9, 0.9, 1)),
            color=self.theme.get("text_color", "#000000")
        )

        save_btn.bind(on_release=self.save_event)
        cancel_btn.bind(on_release=self.dismiss)

        button_box.add_widget(cancel_btn)
        button_box.add_widget(save_btn)

        container = BoxLayout(orientation='vertical')
        container.add_widget(layout)
        container.add_widget(button_box)

        self.content = container

    def save_event(self, instance):
        title = self.title_input.text.strip()
        date = self.date_input.text.strip()
        time = self.time_input.text.strip()
        location = self.location_input.text.strip()
        notes = self.notes_input.text.strip()

        if not title or not date or not time:
            print("Missing required fields")
            return

        event_data = {
            "title": title,
            "date": date,
            "time": time,
            "location": location,
            "notes": notes
        }

        if self.on_save_callback:
            self.on_save_callback(event_data)

        self.dismiss()
