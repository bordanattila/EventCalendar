"""
agent_popup.py

AI Agent popup for natural language calendar commands.

Uses cloud agent (GPT-3.5-turbo) for fast responses.

Author: Attila Bordan
"""

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex

import threading

# Try to import speech recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    print("Speech recognition not available. Install: pip install SpeechRecognition PyAudio")


# Agent server configuration
AGENT_URL = "http://localhost:8000"  # Cloud agent with GPT-3.5


class AgentPopup(Popup):
    """
    Popup for interacting with the AI calendar agent.
    """
    
    def __init__(self, theme, on_refresh=None, **kwargs):
        self.theme = theme
        self.on_refresh = on_refresh
        self.current_plan = None
        self.is_listening = False
        
        # Initialize speech recognizer if available
        if SPEECH_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
        else:
            self.recognizer = None
        
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
            text='[b]Speak or type to manage your calendar:[/b]\n'
                 '"Add soccer every Tuesday at 6pm for 8 weeks"\n'
                 '"What events do I have tomorrow?"\n'
                 '"Schedule dinner for Friday at 7pm"',
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
        
        # Voice button
        self.voice_btn = Button(
            text='Tap to Speak',
            size_hint_y=None,
            height=80,
            background_color=(0.2, 0.6, 0.9, 1) if SPEECH_AVAILABLE else (0.5, 0.5, 0.5, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size='22sp',
            disabled=not SPEECH_AVAILABLE,
        )
        self.voice_btn.bind(on_release=self._on_voice_tap)
        main_layout.add_widget(self.voice_btn)
        
        # Status label
        self.status_label = Label(
            text='',
            color=get_color_from_hex(text_color),
            size_hint_y=None,
            height=30,
            font_size='14sp',
        )
        main_layout.add_widget(self.status_label)
        
        # OR separator
        or_label = Label(
            text='- OR type below -',
            color=get_color_from_hex(text_color),
            size_hint_y=None,
            height=30,
            font_size='12sp',
        )
        main_layout.add_widget(or_label)
        
        # Input field row
        input_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=10,
        )
        
        self.input_field = TextInput(
            hint_text='Type your command here...',
            multiline=False,
            size_hint=(0.75, 1),
            font_size='16sp',
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
        )
        self.input_field.bind(on_text_validate=self._on_send)
        input_row.add_widget(self.input_field)
        
        send_btn = Button(
            text='Send',
            size_hint=(0.25, 1),
            background_color=accent_color,
            color=(1, 1, 1, 1),
            bold=True,
        )
        send_btn.bind(on_release=self._on_send)
        input_row.add_widget(send_btn)
        
        main_layout.add_widget(input_row)
        
        # Response area
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
        
        # Action buttons
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
    
    def _on_voice_tap(self, instance=None):
        """Handle voice button tap."""
        if not SPEECH_AVAILABLE or self.is_listening:
            return
        
        self.is_listening = True
        self.voice_btn.text = 'Listening...'
        self.voice_btn.background_color = (0.9, 0.3, 0.3, 1)
        self.status_label.text = 'Speak now...'
        
        thread = threading.Thread(target=self._listen_for_speech)
        thread.daemon = True
        thread.start()
    
    def _find_usb_microphone(self):
        """Find the USB microphone device index."""
        import os
        
        # Suppress ALSA errors
        stderr_fd = None
        devnull = None
        try:
            stderr_fd = os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
        except:
            stderr_fd = None
            devnull = None
        
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            device_count = p.get_device_count()
            
            # Restore stderr
            if stderr_fd is not None:
                os.dup2(stderr_fd, 2)
                os.close(stderr_fd)
                os.close(devnull)
                stderr_fd = None
                devnull = None
            
            # Try device 1 first (USB mic on Pi)
            try:
                info = p.get_device_info_by_index(1)
                if info.get('maxInputChannels', 0) > 0:
                    p.terminate()
                    return 1
            except:
                pass
            
            # Look for USB device
            for i in range(device_count):
                try:
                    info = p.get_device_info_by_index(i)
                    name = info.get('name', '').lower()
                    if info.get('maxInputChannels', 0) > 0:
                        if 'usb' in name or 'pnp' in name:
                            p.terminate()
                            return i
                except:
                    continue
            
            # Default input
            try:
                default_info = p.get_default_input_device_info()
                p.terminate()
                return default_info.get('index')
            except:
                pass
            
            p.terminate()
        except Exception as e:
            print(f"Error finding microphone: {e}")
        finally:
            if stderr_fd is not None:
                try:
                    os.dup2(stderr_fd, 2)
                    os.close(stderr_fd)
                    os.close(devnull)
                except:
                    pass
        
        return None
    
    def _listen_for_speech(self):
        """Listen for speech in background thread."""
        from kivy.clock import Clock
        
        try:
            device_index = self._find_usb_microphone()
            
            if device_index is None:
                Clock.schedule_once(lambda dt: self._voice_error('No microphone found.'), 0)
                return
            
            mic = sr.Microphone(device_index=device_index)
            
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Listening...'), 0)
                
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Processing...'), 0)
                
                text = self.recognizer.recognize_google(audio)
                
                def on_success(dt):
                    self.status_label.text = f'Heard: "{text}"'
                    self.input_field.text = text
                    self._reset_voice_button()
                    self._send_command(text)
                
                Clock.schedule_once(on_success, 0)
                
        except sr.WaitTimeoutError:
            Clock.schedule_once(lambda dt: self._voice_error('No speech detected.'), 0)
        except sr.UnknownValueError:
            Clock.schedule_once(lambda dt: self._voice_error('Could not understand.'), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._voice_error(f'Error: {str(e)[:40]}'), 0)
        finally:
            Clock.schedule_once(lambda dt: self._reset_voice_button(), 0)
    
    def _voice_error(self, message: str):
        """Display voice error."""
        self.status_label.text = message
        self._reset_voice_button()
    
    def _reset_voice_button(self):
        """Reset voice button."""
        self.is_listening = False
        self.voice_btn.text = 'Tap to Speak'
        self.voice_btn.background_color = (0.2, 0.6, 0.9, 1)
    
    def _on_send(self, instance=None):
        """Send typed command."""
        command = self.input_field.text.strip()
        if command:
            self._send_command(command)
    
    def _send_command(self, command: str):
        """Send command to agent."""
        self.response_label.text = '[i]Thinking...[/i]'
        self.approve_btn.disabled = True
        self.current_plan = None
        
        thread = threading.Thread(target=self._call_agent, args=(command,))
        thread.daemon = True
        thread.start()
    
    def _call_agent(self, command: str):
        """Call the agent API."""
        try:
            import httpx
            
            response = httpx.post(
                f'{AGENT_URL}/chat',
                json={'message': command},
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                self._handle_response(result)
            else:
                self._show_error(f'Server error: {response.status_code}')
                
        except Exception as e:
            error_msg = str(e) if str(e) else type(e).__name__
            if 'Connect' in error_msg:
                self._show_error(
                    'Cannot connect to agent.\n\n'
                    'Start with: cd agent_service &&\n'
                    'uvicorn calendar_agent.main:app'
                )
            else:
                self._show_error(f'Error: {error_msg[:60]}')
    
    def _handle_response(self, result: dict):
        """Handle agent response."""
        from kivy.clock import Clock
        
        def update_ui(dt):
            try:
                if not result.get('success'):
                    error_msg = result.get("error") or "Unknown error"
                    self.response_label.text = f'[color=#FF0000]Error: {error_msg}[/color]'
                    return
                
                plan = result.get('plan', {})
                self.current_plan = plan
                
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
                    text += '[i]No changes needed.[/i]'
                    self.approve_btn.disabled = True
                
                self.response_label.text = text
                
            except Exception as e:
                self.response_label.text = f'[color=#FF0000]UI Error: {str(e)}[/color]'
        
        Clock.schedule_once(update_ui, 0)
    
    def _show_error(self, message: str):
        """Show error message."""
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
        """Commit the plan."""
        try:
            import httpx
            
            response = httpx.post(
                f'{AGENT_URL}/commit',
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
                self.response_label.text = f'[color=#00AA00][b]Success![/b]\n\nApplied {count} change(s).[/color]'
                self.approve_btn.disabled = True
                self.current_plan = None
                
                if self.on_refresh:
                    self.on_refresh()
            else:
                self.response_label.text = f'[color=#FF0000]Commit failed: {result.get("error", "Unknown error")}[/color]'
        
        Clock.schedule_once(update_ui, 0)

