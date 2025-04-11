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
from kivy.utils import get_color_from_hex
from kivy.graphics import Color as Colour, RoundedRectangle as RR, Rectangle

import datetime


class AddEventPopup(Popup):
    def __init__(self, on_save_callback=None, theme=None, **kwargs):
        self.app_ref = kwargs.pop('app_ref', None)
        self.selected_date = kwargs.pop('initial_date', datetime.date.today())
        super().__init__(**kwargs)
        self.title = 'Add Event'
        self.size_hint = (0.85, 0.85)
        self.on_save_callback = on_save_callback
        self.theme = theme or {}
        self.background = ''
        self.bg_color = self.theme.get('bg_color', (1, 1, 1, 1))
        self.date_label = Label(
            text=str(self.selected_date),
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=40
        )
        # Styled Border + Rounded Background
        with self.canvas.before:
            Colour(*self.theme.get('bg_color', (1, 1, 1, 1)))
            self._popup_bg = RR(
                pos=self.pos,
                size=self.size,
                radius=[15],
            )

            Colour(*self.theme.get('popup_border_color', (0, 0, 0, 1)))  # Border overlay
            self._popup_border = RR(
                pos=self.pos,
                size=self.size,
                radius=[15]
            )

            Colour(0, 0, 0, 0.35)  # translucent black
            self._overlay_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_popup_border, size=self._update_popup_border)

        layout = GridLayout(cols=2, spacing=10, padding=20, row_force_default=True, row_default_height=40)

        # Required fields
        layout.add_widget(Label(
            text='Title:*',
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=30
            ))
        self.title_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', (1, 1, 1, 1)),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.title_input)

        layout.add_widget(Label(
            text='Date:*',
            color=get_color_from_hex(self.theme.get('text_colr', '#000000')),
            size_hint_y=None,
            height=30
        ))

        # Show selected date from main calendar
        layout.add_widget(self.date_label)

        layout.add_widget(Label(
            text='Time (HH:MM):*',
            color=get_color_from_hex(self.theme.get('text_colr', '#000000')),
            size_hint_y=None,
            height=30
        ))
        self.time_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', (1, 1, 1, 1)),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.time_input)

        # Optional fields
        layout.add_widget(Label(
            text='Location:',
            color=get_color_from_hex(self.theme.get('text_colr', '#000000')),
            size_hint_y=None,
            height=30
        ))
        self.location_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', (1, 1, 1, 1)),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.location_input)

        layout.add_widget(Label(
            text='Notes:',
            color=get_color_from_hex(self.theme.get('text_colr', '#000000')),
            size_hint_y=None,
            height=30
        ))
        self.notes_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', (1, 1, 1, 1)),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.notes_input)

        # Spacer
        layout.add_widget(Label())
        layout.add_widget(Label())

        # Buttons
        button_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)

        save_btn = Button(
            text='Save',
            background_normal='',
            background_color=self.theme.get('button_color', (0.9, 0.9, 0.9, 1)),
            color=self.theme.get('text_color', '#000000')
        )
        cancel_btn = Button(
            text='Cancel',
            background_normal='',
            background_color=self.theme.get('button_color', (0.9, 0.9, 0.9, 1)),
            color=self.theme.get('text_color', '#000000')
        )

        save_btn.bind(on_release=self.save_event)
        cancel_btn.bind(on_release=self.dismiss)

        button_box.add_widget(cancel_btn)
        button_box.add_widget(save_btn)

        container = BoxLayout(orientation='vertical')
        container.add_widget(layout)
        container.add_widget(button_box)

        self.content = container

    def set_selected_date(self, date_obj):
        self.date_label.text = str(date_obj)

    def save_event(self, instance):
        title = self.title_input.text.strip()
        date = self.date_label.text.strip()
        time = self.time_input.text.strip()
        location = self.location_input.text.strip()
        notes = self.notes_input.text.strip()

        if not title or not date or not time:
            if self.app_ref:
                self.app_ref.show_toast('Please fill in required fields.')
            return

        event_data = {
            'title': title,
            'date': date,
            'time': time,
            'location': location,
            'notes': notes
        }

        if self.on_save_callback:
            self.on_save_callback(event_data)

        self.dismiss()

    def _update_popup_border(self, *args):
        self._popup_border.pos = self.pos
        self._popup_border.size = self.size
        self._popup_bg.pos = self.pos
        self._popup_bg.size = self.size
        self._overlay_rect.pos = self.pos
        self._overlay_rect.size = self.size