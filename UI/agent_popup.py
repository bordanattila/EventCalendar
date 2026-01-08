"""
agent_popup.py

AI Agent popup for natural language calendar commands.

Allows users to:
- Type natural language commands
- See proposed changes from the AI agent
- Approve and apply changes to the calendar

Author: Attila Bordan
"""

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import get_color_from_hex

import threading


class AgentPopup(Popup):
    """
    Popup for interacting with the AI calendar agent.
    
    Args:
        theme (dict): The active theme dictionary.
        on_refresh (callable): Callback to refresh the calendar after changes.
    """
    
    def __init__(self, theme, on_refresh=None, **kwargs):
        self.theme = theme
        self.on_refresh = on_refresh
        self.current_plan = None
        
        super().__init__(
            title='AI Calendar Agent',
            size_hint=(0.9, 0.85),
            auto_dismiss=True,
            **kwargs
        )
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the popup UI."""
        bg_color = get_color_from_hex(self.theme.get('bg_color', '#FFFFFF'))
        text_color = self.theme.get('text_color', '#000000')
        accent_color = get_color_from_hex(self.theme.get('accent_color', '#4A90D9'))
        
        # Main container
        main_layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        with main_layout.canvas.before:
            Color(*bg_color)
            self._bg_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)
        main_layout.bind(pos=self._update_bg, size=self._update_bg)
        
        # Instructions label
        instructions = Label(
            text='[b]Ask the AI to manage your calendar:[/b]\n'
                 '"Add soccer every Tuesday at 6pm for 8 weeks"\n'
                 '"What are my crunch days next week?"\n'
                 '"Move dentist if it conflicts with work"',
            markup=True,
            color=get_color_from_hex(text_color),
            size_hint_y=None,
            height=100,
            halign='left',
            valign='top',
            text_size=(None, None)
        )
        instructions.bind(size=lambda *x: setattr(instructions, 'text_size', (instructions.width - 20, None)))
        main_layout.add_widget(instructions)
        
        # Input field
        self.input_field = TextInput(
            hint_text='Type your command here...',
            multiline=False,
            size_hint_y=None,
            height=50,
            font_size='18sp',
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
        )
        self.input_field.bind(on_text_validate=self._on_send)
        main_layout.add_widget(self.input_field)
        
        # Send button
        send_btn = Button(
            text='Ask Agent',
            size_hint_y=None,
            height=50,
            background_color=accent_color,
            color=(1, 1, 1, 1),
            bold=True,
        )
        send_btn.bind(on_release=self._on_send)
        main_layout.add_widget(send_btn)
        
        # Response area (scrollable)
        scroll = ScrollView(size_hint=(1, 1))
        self.response_label = Label(
            text='[i]Response will appear here...[/i]',
            markup=True,
            color=get_color_from_hex(text_color),
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(None, None),
        )
        self.response_label.bind(
            texture_size=lambda *x: setattr(self.response_label, 'height', self.response_label.texture_size[1])
        )
        self.response_label.bind(
            size=lambda *x: setattr(self.response_label, 'text_size', (self.response_label.width - 20, None))
        )
        scroll.add_widget(self.response_label)
        main_layout.add_widget(scroll)
        
        # Action buttons (hidden until we have a plan)
        self.action_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=10,
        )
        
        self.approve_btn = Button(
            text='Apply Changes',
            background_color=(0.2, 0.7, 0.3, 1),
            color=(1, 1, 1, 1),
            bold=True,
            disabled=True,
        )
        self.approve_btn.bind(on_release=self._on_approve)
        
        self.reject_btn = Button(
            text='Cancel',
            background_color=(0.8, 0.3, 0.3, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        self.reject_btn.bind(on_release=self.dismiss)
        
        self.action_layout.add_widget(self.approve_btn)
        self.action_layout.add_widget(self.reject_btn)
        main_layout.add_widget(self.action_layout)
        
        self.content = main_layout
    
    def _update_bg(self, *args):
        """Update background rectangle."""
        if hasattr(self, '_bg_rect'):
            self._bg_rect.pos = self.content.pos
            self._bg_rect.size = self.content.size
    
    def _on_send(self, instance=None):
        """Send command to the AI agent."""
        command = self.input_field.text.strip()
        if not command:
            return
        
        self.response_label.text = '[i]Thinking...[/i]'
        self.approve_btn.disabled = True
        self.current_plan = None
        
        # Run in background thread to not block UI
        thread = threading.Thread(target=self._call_agent, args=(command,))
        thread.daemon = True
        thread.start()
    
    def _call_agent(self, command: str):
        """Call the agent API in background thread."""
        try:
            import httpx
            
            response = httpx.post(
                'http://localhost:8000/chat',
                json={'message': command},
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                self._handle_response(result)
            else:
                self._show_error(f'Server error: {response.status_code}')
                
        except httpx.ConnectError:
            self._show_error(
                'Could not connect to agent server.\n\n'
                'Start it with:\n'
                'cd agent_service && uvicorn calendar_agent.main:app'
            )
        except Exception as e:
            self._show_error(f'Error: {str(e)}')
    
    def _handle_response(self, result: dict):
        """Handle response from agent (called from background thread)."""
        from kivy.clock import Clock
        
        def update_ui(dt):
            if not result.get('success'):
                self.response_label.text = f'[color=#FF0000]Error: {result.get("error", "Unknown error")}[/color]'
                return
            
            plan = result.get('plan', {})
            self.current_plan = plan
            
            # Build response text
            text = f'[b]Summary:[/b]\n{plan.get("summary", "No summary")}\n\n'
            
            actions = plan.get('actions', [])
            if actions:
                text += f'[b]Proposed Actions ({len(actions)}):[/b]\n'
                for i, action in enumerate(actions, 1):
                    action_type = action.get('type', 'unknown').replace('_', ' ').title()
                    text += f'  {i}. {action_type}'
                    
                    if action.get('title'):
                        text += f': {action["title"]}'
                    if action.get('start'):
                        text += f' @ {action["start"][:16]}'
                    text += '\n'
                
                self.approve_btn.disabled = False
            else:
                text += '[i]No changes needed - informational response only.[/i]'
                self.approve_btn.disabled = True
            
            warnings = plan.get('warnings', [])
            if warnings:
                text += f'\n[color=#FFA500][b]Warnings:[/b]\n'
                for w in warnings:
                    text += f'  * {w}\n'
                text += '[/color]'
            
            self.response_label.text = text
        
        Clock.schedule_once(update_ui, 0)
    
    def _show_error(self, message: str):
        """Show error message (called from background thread)."""
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self.response_label, 'text', f'[color=#FF0000]{message}[/color]'), 0)
    
    def _on_approve(self, instance=None):
        """Approve and commit the plan."""
        if not self.current_plan:
            return
        
        plan_id = self.current_plan.get('plan_id')
        if not plan_id:
            self._show_error('No plan ID found')
            return
        
        self.response_label.text = '[i]Applying changes...[/i]'
        self.approve_btn.disabled = True
        
        thread = threading.Thread(target=self._commit_plan, args=(plan_id,))
        thread.daemon = True
        thread.start()
    
    def _commit_plan(self, plan_id: str):
        """Commit the plan via API."""
        try:
            import httpx
            
            response = httpx.post(
                'http://localhost:8000/commit',
                json={'plan_id': plan_id, 'confirm_deletes': True},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                self._handle_commit_result(result)
            else:
                self._show_error(f'Commit failed: {response.status_code}')
                
        except Exception as e:
            self._show_error(f'Commit error: {str(e)}')
    
    def _handle_commit_result(self, result: dict):
        """Handle commit result."""
        from kivy.clock import Clock
        
        def update_ui(dt):
            if result.get('success'):
                count = result.get('committed_actions', 0)
                self.response_label.text = f'[color=#00AA00][b]Success![/b]\n\nApplied {count} change(s) to your calendar.[/color]'
                self.approve_btn.disabled = True
                self.current_plan = None
                
                # Refresh the calendar
                if self.on_refresh:
                    self.on_refresh()
            else:
                self.response_label.text = f'[color=#FF0000]Commit failed: {result.get("error", "Unknown error")}[/color]'
        
        Clock.schedule_once(update_ui, 0)

