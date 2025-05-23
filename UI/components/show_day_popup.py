"""
show_day_popup.py

Defines a popup window that displays all events for a given day.

Used in the monthly calendar view when a user taps "+N more..." or a day cell.

Author: Attila Bordan
"""
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.clock import Clock


def show_day_popup(day_date, events, theme):
    """
    Creates and opens a popup displaying all events for the specified day.

    Args:
        day_date (datetime.date): The date of the events.
        events (list): List of Event objects.
        theme (dict): Current theme dictionary for colors and styling.
    """
    # Root layout for the popup content
    day_popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

    # Scrollable container to hold event labels
    scroll = ScrollView(size_hint=(1, 1))
    event_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8, padding=5)
    event_list.bind(minimum_height=event_list.setter('height'))

    # Theme colors
    bg_color = get_color_from_hex(theme['bg_color'])
    text_color = get_color_from_hex(theme['text_color'])

    # Draw background for the popup layout
    with day_popup_layout.canvas.before:
        Color(*bg_color)
        bg_rect = RoundedRectangle(pos=day_popup_layout.pos, size=day_popup_layout.size, radius=[15])

    def update_bg(*_):
        bg_rect.pos = day_popup_layout.pos
        bg_rect.size = day_popup_layout.size

    day_popup_layout.bind(pos=update_bg, size=update_bg)

    # Sort events by time and create labels
    for event in sorted(events, key=lambda e: e.time):
        # TODO: Improve appearance
        # TODO: Add Close button
        # Conditionally include location and notes only if they're not empty
        event_text = f"[b]{event.time}[/b]  -  {event.title}"

        if event.location and event.location.strip():
            event_text += f"\n[size=12]Location: {event.location}[/size]"

        if event.notes and event.notes.strip():
            event_text += f"\n[size=12]Notes: {event.notes}[/size]\n"

        label = Label(
            text=event_text,
            markup=True,
            size_hint_y=None,
            height=75,
            color=text_color,
            text_size=(None, None),
        )
        # Bind the width to make text wrap properly
        label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        event_list.add_widget(label)

    scroll.add_widget(event_list)
    day_popup_layout.add_widget(scroll)

    # Construct the popup
    popup = Popup(
        title=f"Events for {day_date.strftime('%b %d')}",
        title_color=get_color_from_hex(theme['text_color']),
        title_align='center',
        content=day_popup_layout,
        size_hint=(0.3, 0.9),
        auto_dismiss=True,
        background='',
        background_color=get_color_from_hex(theme['bg_color']),
    )
    popup.open()

    # Auto-close after 15 minutes
    Clock.schedule_once(lambda dt: popup.dismiss(), 900)
