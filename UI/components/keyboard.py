from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.clock import Clock


class VirtualKeyboard(BoxLayout):
    active_input = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.key_rows = [
            ['1','2','3','4','5','6','7','8','9','0'],
            ['q','w','e','r','t','y','u','i','o','p'],
            ['a','s','d','f','g','h','j','k','l'],
            ['z','x','c','v','b','n','m'],
            ['Space', 'Backspace', 'Clear', 'Done']
        ]
        self.build_keys()

    def build_keys(self):
        for row in self.key_rows:
            row_layout = GridLayout(cols=len(row), size_hint_y=None, height=40)
            for key in row:
                btn = Button(text=key, on_press=self.handle_key, font_size=18)
                row_layout.add_widget(btn)
            self.add_widget(row_layout)

    def handle_key(self, instance):
        if not self.active_input:
            return

        key = instance.text
        if key == 'Space':
            self.active_input.insert_text(' ')
        elif key == 'Backspace':
            text = self.active_input.text
            self.active_input.text = text[:-1]
        elif key == 'Clear':
            self.active_input.text = ''
        elif key == 'Done':
            self.active_input.focus = False
        else:
            self.active_input.insert_text(key)

    def register_inputs(self, *inputs):
        for input_field in inputs:
            input_field.bind(focus=self.on_focus)

    def on_focus(self, instance, value):
        if value:
            Clock.schedule_once(lambda dt: setattr(self, 'active_input', instance), 0)
