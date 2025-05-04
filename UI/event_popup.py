"""
event_popup.py

Popup class for adding a new calendar event.
Includes required fields: title, date, time.
Optional fields: location, notes.
"""

from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import get_color_from_hex
from kivy.graphics import Color as Colour, RoundedRectangle as RR, Rectangle
from kivy.animation import Animation
from kivy.clock import Clock

import datetime

from storage.db_manager import save_event_to_db, stop_recurring_event, update_event_in_db, delete_event
from app.ui_utils import create_themed_button
from UI.components.keyboard import VirtualKeyboard


class AddEventPopup(Popup):
    """
    Popup form for adding or editing a calendar event.

    Supports:
    - Required fields: title, date, time
    - Optional fields: location, notes
    - Recurrence via dropdown: daily, weekly, monthly, yearly
    - Editing an existing event with pre-filled values
    - Toast-style inline validation feedback
    - Theme-aware background, input, and button styling
    """
    def __init__(self, app_ref, on_save_callback=None, theme=None, event=None, **kwargs):
        self.app_ref = kwargs.pop('app_ref', None)
        self.selected_date = kwargs.pop('initial_date', datetime.date.today())
        super().__init__(auto_dismiss=False, **kwargs)
        self.app_ref = app_ref
        self.theme = theme or {}
        self.event = event
        self.title = 'Edit Event' if self.event else 'Add Event'
        self.title_color = get_color_from_hex(theme['text_color'])
        self.title_align = 'center'
        self.size_hint = (0.5, 0.7)
        self.on_save_callback = on_save_callback
        self.background = ''
        self.background_color = get_color_from_hex(self.theme.get('bg_color', '#FFFFFF'))
        self.bg_color = self.theme.get('bg_color', '#FFFFFF')

        self.date_label = Label(
            text=str(self.selected_date),
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=40
        )

        # Styled Border + Rounded Background
        with self.canvas.before:
            Colour(*self.theme.get('bg_color', '#FFFFFF'))
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
            background_color=self.theme.get('input_bg_color', '#FFFFFF'),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.title_input)

        layout.add_widget(Label(
            text='Date:*',
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=30
        ))

        # Show selected date from main calendar
        layout.add_widget(self.date_label)

        layout.add_widget(Label(
            text='Time (HH:MM):*',
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=30
        ))
        self.time_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', '#FFFFFF'),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.time_input)

        # Optional fields
        layout.add_widget(Label(
            text='Location:',
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=30
        ))
        self.location_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', '#FFFFFF'),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        layout.add_widget(self.location_input)

        layout.add_widget(Label(
            text='Notes:',
            color=get_color_from_hex(self.theme.get('text_color', '#000000')),
            size_hint_y=None,
            height=30
        ))
        self.notes_input = TextInput(
            multiline=False,
            background_color=self.theme.get('input_bg_color', '#FFFFFF'),
            foreground_color=get_color_from_hex(self.theme.get('text_color', '#000000')),
        )
        # self.notes_input.bind(focus=lambda instance, value: show_virtual_keyboard() if value else None)
        layout.add_widget(self.notes_input)

        # Spacer
        layout.add_widget(Label())
        layout.add_widget(Label())

        # Recurrence selection
        self.recurrence_label = Label(
            text='Repeat:',
            size_hint=(1, None),
            height=30,
            color=get_color_from_hex(self.theme['text_color']),
            halign='left'
        )
        self.recurrence_spinner = Spinner(
            text='None',
            values=('None', 'Daily', 'Weekly', 'Monthly', 'Yearly'),
            size_hint=(1, None),
            height=44,
            background_color=get_color_from_hex(self.theme['button_color']),
            color=get_color_from_hex(self.theme['text_color']),
        )

        layout.add_widget(self.recurrence_label)
        layout.add_widget(self.recurrence_spinner)

        # Buttons
        button_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        # Only show 'Stop Recurrence' if editing a recurring event
        if self.event and self.event.recurrence.lower() != "none":
            self.stop_button = create_themed_button(
                "Stop Recurrence",
                self.theme,
                on_release=self.handle_stop_recurrence
            )
            button_box.add_widget(self.stop_button)

        # Only show 'Delete' if editing an existing event
        if self.event and self.event.title != "none":
            self.delete_button = create_themed_button(
                "Delete",
                self.theme,
                on_release=self.handle_delete_event
            )
            button_box.add_widget(self.delete_button)

        self.save_btn = create_themed_button('Save', self.theme, on_release=self.save_event)
        self.cancel_btn = create_themed_button('Cancel', self.theme, on_release=self.dismiss)

        button_box.add_widget(self.cancel_btn)
        button_box.add_widget(self.save_btn)

        self.keyboard = VirtualKeyboard(size_hint_y=None, height=200)
        self.keyboard.register_inputs(
            self.title_input,
            self.time_input,
            self.location_input,
            self.notes_input
        )

        # # Set natural focus order
        # self.title_input.next = self.time_input
        # self.time_input.next = self.location_input
        # self.location_input.next = self.notes_input

        container = BoxLayout(orientation='vertical')
        container.add_widget(layout)
        container.add_widget(self.keyboard)
        container.add_widget(button_box)

        self.content = container

        if self.event:
            self.title_input.text = self.event.title
            self.date_label.text = self.event.date
            self.time_input.text = self.event.time
            self.location_input.text = self.event.location
            self.notes_input.text = self.event.notes
            self.recurrence_spinner.text = self.event.recurrence

    def __del__(self):
        print("🧹 AddEventPopup destroyed")

    def set_selected_date(self, date_obj):
        """Sets the popup's displayed date label to the given date."""
        self.date_label.text = str(date_obj)

    def save_event(self, *_):
        """
        Validates and saves the event to the database.

        - If required fields are missing, shows a toast message inside the popup.
        - If editing, updates the event; otherwise, creates a new one.
        - Calls the parent view’s callback and refresh methods if available.
        """
        title = self.title_input.text.strip()
        date = self.date_label.text.strip()
        time = self.time_input.text.strip()
        location = self.location_input.text.strip()
        notes = self.notes_input.text.strip()
        recurrence = self.recurrence_spinner.text.strip()

        if not title or not date or not time:
            # Show inline toast if any required field is missing
            self.show_popup_toast('Please fill in required fields.')
            return

        event_data = {
            'title': title,
            'date': date,
            'time': time,
            'location': location,
            'notes': notes,
            'recurrence': recurrence,
        }

        if self.event:
            update_event_in_db(self.event.id, event_data)
        else:
            save_event_to_db(event_data)

        if self.on_save_callback:
            self.on_save_callback(event_data)

        self.dismiss()

        # Show the app toast only after popup is dismissed
        if hasattr(self.app_ref, "show_toast"):
            self.app_ref.show_toast(f"Event '{event_data['title']}' added!")

        # Refresh calendar to show new event
        if hasattr(self.app_ref, "build_view"):
            self.app_ref.selected_day = None
            self.app_ref.build_view(self.app_ref.current_year, self.app_ref.current_month)

    def _update_popup_border(self, *_):
        """Keeps the styled popup border in sync with the popup's size and position."""
        self._popup_border.pos = self.pos
        self._popup_border.size = self.size
        self._popup_bg.pos = self.pos
        self._popup_bg.size = self.size
        self._overlay_rect.pos = self.pos
        self._overlay_rect.size = self.size

    def show_popup_toast(self, message, duration=2.5):
        """Shows a toast message within the popup."""
        # Create toast label
        toast = Label(
            text=message,
            markup=True,
            size_hint=(None, None),
            size=(self.width * 0.2, 30),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle',
            color=get_color_from_hex('#FFFFFF'),
            padding=(20, 10),
            font_size='16sp',
        )

        # Set the background color (red for errors)
        toast.canvas.before.clear()
        with toast.canvas.before:
            Colour(*get_color_from_hex('#FF4C4C'))
            toast_bg = RR(pos=toast.pos, size=toast.size, radius=[10])

        # Update the background when the label size changes
        def update_bg(*_):
            toast_bg.pos = toast.pos
            toast_bg.size = toast.size

        toast.bind(size=update_bg, pos=update_bg)

        # Add to popup content
        self.content.add_widget(toast)

        # Animate in
        toast.opacity = 0
        anim_in = Animation(opacity=1, duration=0.2)

        # Animate out after a delay
        def remove_toast(*_):
            anim_out = Animation(opacity=0, duration=0.2)
            anim_out.bind(on_complete=lambda *x: self.content.remove_widget(toast))
            anim_out.start(toast)

        anim_in.start(toast)
        Clock.schedule_once(remove_toast, duration)

    def handle_stop_recurrence(self, *_):
        """
        Stops recurrence for an existing event by updating the database,
        then dismisses the popup and refreshes the calendar UI.
        """
        if self.event and stop_recurring_event(self.event.id):
            self.show_popup_toast("Recurrence stopped.")
            self.dismiss()

            # Delay the calendar refresh to occur AFTER the popup closes
            def refresh_ui(dt):
                if hasattr(self.app_ref, "rebuild_ui"):
                    float_root = getattr(self.app_ref, "float_root", None)
                    if float_root:
                        self.app_ref.rebuild_ui(float_root)
                    else:
                        print("⚠️ Warning: float_root not found for rebuild.")

            Clock.schedule_once(refresh_ui, 0.3)
        else:
            self.show_popup_toast("Unable to stop recurrence.")

    def handle_delete_event(self, *_):
        """
        Delete existing events
        :param _:
        :return:
        """
        if self.event and delete_event(self.event.id):
            self.show_popup_toast("Evnet deleted.")
            self.dismiss()

            # Delay the calendar refresh to occur AFTER the popup closes
            def refresh_ui(dt):
                if hasattr(self.app_ref, "rebuild_ui"):
                    float_root = getattr(self.app_ref, "float_root", None)
                    if float_root:
                        self.app_ref.rebuild_ui(float_root)
                    else:
                        print("⚠️ Warning: float_root not found for rebuild.")

            Clock.schedule_once(refresh_ui, 0.3)
        else:
            self.show_popup_toast("Unable to delete event.")

    def on_dismiss(self):
        if hasattr(self, "keyboard") and self.keyboard:
            if self.keyboard.parent:
                self.keyboard.parent.remove_widget(self.keyboard)
            self.keyboard = None
        self.content = None
