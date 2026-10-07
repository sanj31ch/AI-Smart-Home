# main.py - Complete Kivy Mobile App for Android (FIXED - Language Display with Door Buttons)
import os
os.environ['KIVY_AUDIO'] = 'sdl2'
import kivy
kivy.require('2.1.0')
import sys
import traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.utils import platform
from kivy.core.audio import SoundLoader
from kivy.logger import Logger

import requests
import json
import threading
import time
from datetime import datetime
os.environ['KIVY_AUDIO'] = 'sdl2'
os.environ['KIVY_VIDEO'] = 'sdl2'

def start_recording_desktop(self):
    self.show_message("Desktop recording disabled in build", False)
    return False

def stop_recording_desktop(self):
    return None


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

sys.excepthook = handle_exception


# Platform-specific imports
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    from jnius import autoclass
    import android
    MediaRecorder = autoclass('android.media.MediaRecorder')
    AudioSource = autoclass('android.media.MediaRecorder$AudioSource')
    OutputFormat = autoclass('android.media.MediaRecorder$OutputFormat')
    AudioEncoder = autoclass('android.media.MediaRecorder$AudioEncoder')
else:
    try:
        import pyaudio
        import wave
    except ImportError:
        print("⚠️ pyaudio not installed. Voice recording disabled.")
        pyaudio = None
        wave = None

# Set window size for development
if platform != 'android':
    Window.size = (400, 700)

class SmartHomeApp(App):
    # Properties
    server_ip = StringProperty("10.161.87.87")  # CHANGE THIS TO YOUR PC IP
    connection_status = StringProperty("Disconnected")
    is_connected = BooleanProperty(False)
    is_recording = BooleanProperty(False)
    recording_time = NumericProperty(0)
    
    # Device status
    light_status = StringProperty("OFF")
    fan_status = StringProperty("OFF")
    fan_speed = NumericProperty(0)
    door_status = StringProperty("LOCKED")
    
    # Language
    current_language = StringProperty("english")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_url = f"http://{self.server_ip}:5000"
        self.recording = False
        self.recorder = None
        self.audio_file = None
        self.recording_thread = None
        self.audio_frames = []
        
        # Status colors
        self.status_colors = {
            'ON': (0.2, 0.8, 0.2, 1),
            'OFF': (0.8, 0.2, 0.2, 1),
            'LOCKED': (0.8, 0.2, 0.2, 1),
            'UNLOCKED': (0.2, 0.8, 0.2, 1)
        }
        
        # Language display names
        self.languages = {
            'english': 'English',
            'hindi': 'हिंदी',
            'marathi': 'मराठी'
        }
        
        # Language names for spinner (more readable)
        self.language_options = {
            'English': 'english',
            'Hindi (हिंदी)': 'hindi', 
            'Marathi (मराठी)': 'marathi'
        }
        
        # Example commands
        self.examples = {
            'english': [
                "Light on", "Light off",
                "Fan on", "Fan off", "Fan speed 50",
                "Lock door", "Unlock door"
            ],
            'hindi': [
                "लाइट चालू", "लाइट बंद",
                "पंखा चालू", "पंखा बंद", "पंखा स्पीड 50",
                "दरवाजा बंद", "दरवाजा खोल"
            ],
            'marathi': [
                "दिवा चालू", "दिवा बंद",
                "पंखा चालू", "पंखा बंद", "पंखा स्पीड 50",
                "दरवाजा बंद", "दरवाजा उघड"
            ]
        }
    
    def build(self):
        # Main layout
        main = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # Header
        header = self.create_header()
        main.add_widget(header)
        
        # Connection bar
        conn_bar = self.create_connection_bar()
        main.add_widget(conn_bar)
        
        # Language selector
        lang_selector = self.create_language_selector()
        main.add_widget(lang_selector)
        
        # Voice control section
        voice_section = self.create_voice_section()
        main.add_widget(voice_section)
        
        # Example commands
        example_section = self.create_example_section()
        main.add_widget(example_section)
        
        # Device controls
        device_section = self.create_device_section()
        main.add_widget(device_section)
        
        # ML Insights
        ml_section = self.create_ml_section()
        main.add_widget(ml_section)
        
        # Status message
        self.status_label = Label(
            text="Ready",
            size_hint=(1, 0.05),
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        main.add_widget(self.status_label)
        
        # Request Android permissions
        if platform == 'android':
            self.request_permissions()
        
        # Start periodic updates
        Clock.schedule_interval(self.update_status, 2)
        Clock.schedule_once(lambda dt: self.connect_to_server(), 1)
        
        return main
    
    def create_header(self):
        """Create app header"""
        header = BoxLayout(size_hint=(1, 0.08))
        
        title = Label(
            text="🏠 AI Smart Home",
            font_size='24sp',
            bold=True,
            color=(0.2, 0.4, 0.9, 1),
            halign='left'
        )
        
        self.conn_indicator = Label(
            text="●",
            font_size='30sp',
            color=(0.8, 0.2, 0.2, 1),
            size_hint=(0.2, 1)
        )
        
        header.add_widget(title)
        header.add_widget(self.conn_indicator)
        
        return header
    
    def create_connection_bar(self):
        """Create connection bar"""
        bar = BoxLayout(size_hint=(1, 0.06), spacing=5)
        
        self.ip_input = Button(
            text=f"IP: {self.server_ip}",
            size_hint=(0.7, 1),
            background_color=(0.3, 0.3, 0.3, 1),
            color=(1, 1, 1, 1),
            font_size='14sp'
        )
        self.ip_input.bind(on_press=self.show_ip_dialog)
        
        self.connect_btn = Button(
            text="Connect",
            size_hint=(0.3, 1),
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size='14sp'
        )
        self.connect_btn.bind(on_press=lambda x: self.connect_to_server())
        
        bar.add_widget(self.ip_input)
        bar.add_widget(self.connect_btn)
        
        return bar
    
    def create_language_selector(self):
        """Create language selector with better display"""
        lang_box = BoxLayout(orientation='vertical', size_hint=(1, 0.1), spacing=2)
        
        # Language label
        lang_label = Label(
            text="Select Language:",
            size_hint=(1, 0.3),
            font_size='14sp',
            bold=True,
            halign='left',
            color=(0.2, 0.2, 0.2, 1)
        )
        lang_label.bind(size=lang_label.setter('text_size'))
        lang_box.add_widget(lang_label)
        
        # Spinner row
        spinner_row = BoxLayout(size_hint=(1, 0.7), spacing=5)
        
        self.lang_spinner = Spinner(
            text='English',
            values=('English', 'Hindi (हिंदी)', 'Marathi (मराठी)'),
            size_hint=(0.7, 1),
            background_color=(0.9, 0.9, 0.9, 1),
            font_size='14sp'
        )
        self.lang_spinner.bind(text=self.on_language_change)
        
        # Current language display
        self.current_lang_display = Label(
            text="Current: English",
            size_hint=(0.3, 1),
            font_size='12sp',
            color=(0.2, 0.6, 0.2, 1),
            halign='right'
        )
        self.current_lang_display.bind(size=self.current_lang_display.setter('text_size'))
        
        spinner_row.add_widget(self.lang_spinner)
        spinner_row.add_widget(self.current_lang_display)
        
        lang_box.add_widget(spinner_row)
        
        return lang_box
    
    def create_voice_section(self):
        """Create voice control section"""
        voice_box = BoxLayout(orientation='vertical', size_hint=(1, 0.15))
        
        # Voice button
        self.voice_btn = Button(
            text="🎤 PRESS & HOLD TO SPEAK",
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.7),
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        self.voice_btn.bind(on_press=self.start_recording)
        self.voice_btn.bind(on_release=self.stop_recording)
        
        # Recording status
        self.rec_status = Label(
            text="Press and hold to speak",
            size_hint=(1, 0.3),
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        
        voice_box.add_widget(self.voice_btn)
        voice_box.add_widget(self.rec_status)
        
        return voice_box
    
    def create_example_section(self):
        """Create example commands section"""
        example_box = BoxLayout(orientation='vertical', size_hint=(1, 0.2))
        
        # Title with language indicator
        title_row = BoxLayout(size_hint=(1, 0.2))
        title_row.add_widget(Label(
            text="Try saying:",
            font_size='14sp',
            bold=True,
            halign='left',
            color=(0.4, 0.4, 0.4, 1)
        ))
        
        self.lang_example_label = Label(
            text="(English)",
            font_size='12sp',
            color=(0.4, 0.4, 0.8, 1),
            halign='right'
        )
        title_row.add_widget(self.lang_example_label)
        
        example_box.add_widget(title_row)
        
        # Example buttons grid
        grid = GridLayout(cols=2, spacing=5, size_hint=(1, 0.8))
        
        self.example_btns = []
        for cmd in self.examples['english'][:4]:  # First 4 examples
            btn = Button(
                text=cmd,
                font_size='12sp',
                background_color=(0.3, 0.5, 0.8, 0.8),
                color=(1, 1, 1, 1)
            )
            btn.bind(on_press=lambda x, t=cmd: self.send_text_command(t))
            grid.add_widget(btn)
            self.example_btns.append(btn)
        
        example_box.add_widget(grid)
        return example_box
    
    def create_device_section(self):
        """Create device controls section - FIXED with separate door buttons"""
        device_box = BoxLayout(orientation='vertical', size_hint=(1, 0.35), spacing=5)
        
        # Light control
        light_box = BoxLayout(size_hint=(1, 0.22))
        light_box.add_widget(Label(text="💡 Light", font_size='16sp'))
        
        self.light_btn = ToggleButton(
            text=self.light_status,
            group='light',
            background_normal='',
            background_color=self.status_colors.get(self.light_status, (0.5,0.5,0.5,1))
        )
        self.light_btn.bind(on_press=lambda x: self.toggle_device('light'))
        light_box.add_widget(self.light_btn)
        device_box.add_widget(light_box)
        
        # Fan control
        fan_box = BoxLayout(orientation='vertical', size_hint=(1, 0.33))
        
        # Fan ON/OFF
        fan_row1 = BoxLayout(size_hint=(1, 0.5))
        fan_row1.add_widget(Label(text="🌀 Fan", font_size='16sp'))
        
        self.fan_btn = ToggleButton(
            text=self.fan_status,
            group='fan',
            background_normal='',
            background_color=self.status_colors.get(self.fan_status, (0.5,0.5,0.5,1))
        )
        self.fan_btn.bind(on_press=lambda x: self.toggle_device('fan'))
        fan_row1.add_widget(self.fan_btn)
        fan_box.add_widget(fan_row1)
        
        # Fan speed slider
        fan_row2 = BoxLayout(size_hint=(1, 0.5))
        fan_row2.add_widget(Label(text="Speed:", size_hint=(0.3, 1)))
        
        self.speed_slider = Slider(
            min=0, max=100, value=self.fan_speed,
            size_hint=(0.5, 1)
        )
        self.speed_slider.bind(value=self.on_speed_change)
        
        self.speed_label = Label(
            text=f"{self.fan_speed}%",
            size_hint=(0.2, 1)
        )
        
        fan_row2.add_widget(self.speed_slider)
        fan_row2.add_widget(self.speed_label)
        fan_box.add_widget(fan_row2)
        
        device_box.add_widget(fan_box)
        
        # Door control - Separate buttons for Lock and Unlock
        door_container = BoxLayout(orientation='vertical', size_hint=(1, 0.25), spacing=3)
        
        # Door label
        door_label = Label(
            text="🚪 Door",
            font_size='16sp',
            size_hint=(1, 0.3),
            halign='left'
        )
        door_label.bind(size=door_label.setter('text_size'))
        door_container.add_widget(door_label)
        
        # Door buttons row - Two separate buttons
        door_buttons_row = BoxLayout(size_hint=(1, 0.5), spacing=10)
        
        # Lock button
        self.lock_btn = Button(
            text="🔒 LOCK",
            font_size='14sp',
            bold=True,
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        self.lock_btn.bind(on_press=lambda x: self.send_control_command('door', 'lock'))
        
        # Unlock button
        self.unlock_btn = Button(
            text="🔓 UNLOCK",
            font_size='14sp',
            bold=True,
            background_color=(0.2, 0.8, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        self.unlock_btn.bind(on_press=lambda x: self.send_control_command('door', 'unlock'))
        
        door_buttons_row.add_widget(self.lock_btn)
        door_buttons_row.add_widget(self.unlock_btn)
        door_container.add_widget(door_buttons_row)
        
        # Status indicator
        self.door_status_label = Label(
            text=f"Status: {self.door_status}",
            font_size='12sp',
            size_hint=(1, 0.2),
            color=(0.5, 0.5, 0.5, 1)
        )
        door_container.add_widget(self.door_status_label)
        
        device_box.add_widget(door_container)
        
        return device_box
    
    def create_ml_section(self):
        """Create ML insights section"""
        ml_box = BoxLayout(orientation='vertical', size_hint=(1, 0.1))
        
        # ML toggle
        toggle_box = BoxLayout(size_hint=(1, 0.5))
        toggle_box.add_widget(Label(text="🤖 Auto Learning:", font_size='12sp'))
        
        self.ml_toggle = ToggleButton(
            text="ON",
            state='down',
            background_normal='',
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.ml_toggle.bind(on_press=self.toggle_ml)
        toggle_box.add_widget(self.ml_toggle)
        ml_box.add_widget(toggle_box)
        
        # Insights button
        self.insights_btn = Button(
            text="Show Insights",
            size_hint=(1, 0.5),
            font_size='12sp',
            background_color=(0.5, 0.5, 0.5, 1)
        )
        self.insights_btn.bind(on_press=self.show_insights)
        ml_box.add_widget(self.insights_btn)
        
        return ml_box
    
    # ========== ANDROID PERMISSIONS ==========
    def request_permissions(self):
        """Request Android permissions"""
        if platform == 'android':
            permissions = [
                Permission.RECORD_AUDIO,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET
            ]
            request_permissions(permissions, self.permission_callback)
    
    def permission_callback(self, permissions, grants):
        """Handle permission results"""
        if all(grants.values()):
            self.show_message("✅ All permissions granted")
        else:
            self.show_message("❌ Some permissions denied", False)
    
    # ========== ANDROID AUDIO RECORDING ==========
    def start_recording_android(self):
        """Start recording on Android"""
        try:
            from android.storage import primary_external_storage_path
            import os
            
            # Create temp file
            storage_path = primary_external_storage_path()
            self.audio_file = os.path.join(storage_path, 'voice_command.3gp')
            
            # Initialize MediaRecorder
            self.recorder = MediaRecorder()
            self.recorder.setAudioSource(AudioSource.MIC)
            self.recorder.setOutputFormat(OutputFormat.THREE_GPP)
            self.recorder.setAudioEncoder(AudioEncoder.AMR_NB)
            self.recorder.setOutputFile(self.audio_file)
            
            # Prepare and start
            self.recorder.prepare()
            self.recorder.start()
            
            self.is_recording = True
            return True
            
        except Exception as e:
            Logger.error(f"Recording error: {e}")
            return False
    
    def stop_recording_android(self):
        """Stop recording on Android"""
        try:
            if self.recorder:
                self.recorder.stop()
                self.recorder.release()
                self.recorder = None
                
                # Read the recorded file
                with open(self.audio_file, 'rb') as f:
                    audio_data = f.read()
                
                # Clean up
                import os
                os.remove(self.audio_file)
                
                return audio_data
        except Exception as e:
            Logger.error(f"Stop error: {e}")
        
        return None
    
    # ========== DESKTOP AUDIO RECORDING ==========
    def start_recording_desktop(self):
        """Start recording on desktop"""
        if pyaudio is None:
            self.show_message("pyaudio not installed", False)
            return False
            
        try:
            self.audio_frames = []
            self.recording = True
            
            def record():
                CHUNK = 1024
                FORMAT = pyaudio.paInt16
                CHANNELS = 1
                RATE = 16000
                
                p = pyaudio.PyAudio()
                stream = p.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              frames_per_buffer=CHUNK)
                
                while self.recording:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    self.audio_frames.append(data)
                
                stream.stop_stream()
                stream.close()
                p.terminate()
            
            self.recording_thread = threading.Thread(target=record)
            self.recording_thread.start()
            
            return True
            
        except Exception as e:
            Logger.error(f"Desktop recording error: {e}")
            return False
    
    def stop_recording_desktop(self):
        """Stop recording on desktop"""
        if pyaudio is None:
            return None
            
        try:
            self.recording = False
            if self.recording_thread:
                self.recording_thread.join()
            
            # Convert frames to WAV
            import io
            buffer = io.BytesIO()
            wf = wave.open(buffer, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()
            
            return buffer.getvalue()
            
        except Exception as e:
            Logger.error(f"Desktop stop error: {e}")
            return None
    
    # ========== VOICE RECORDING HANDLERS ==========
    def start_recording(self, instance):
        """Start voice recording"""
        if not self.is_connected:
            self.show_message("Connect to server first", False)
            return
        
        self.is_recording = True
        self.recording_time = 0
        
        # Update UI
        self.voice_btn.text = "🎤 RECORDING... RELEASE TO STOP"
        self.voice_btn.background_color = (0.2, 0.8, 0.2, 1)
        self.rec_status.text = "Listening... Speak now"
        self.rec_status.color = (0.2, 0.8, 0.2, 1)
        
        # Start recording based on platform
        if platform == 'android':
            success = self.start_recording_android()
        else:
            success = self.start_recording_desktop()
        
        if not success:
            self.show_message("Failed to start recording", False)
            self.is_recording = False
            self.voice_btn.text = "🎤 PRESS & HOLD TO SPEAK"
            self.voice_btn.background_color = (0.8, 0.2, 0.2, 1)
            return
        
        # Start timer
        Clock.schedule_interval(self.update_recording_timer, 0.1)
    
    def stop_recording(self, instance):
        """Stop voice recording"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        Clock.unschedule(self.update_recording_timer)
        
        # Update UI
        self.voice_btn.text = "🎤 PRESS & HOLD TO SPEAK"
        self.voice_btn.background_color = (0.8, 0.2, 0.2, 1)
        self.rec_status.text = "Processing..."
        self.rec_status.color = (0.8, 0.5, 0.2, 1)
        
        # Get audio data
        if platform == 'android':
            audio_data = self.stop_recording_android()
        else:
            audio_data = self.stop_recording_desktop()
        
        if audio_data:
            self.send_audio_command(audio_data)
        else:
            self.rec_status.text = "Recording failed. Try again"
            self.rec_status.color = (0.8, 0.2, 0.2, 1)
    
    def update_recording_timer(self, dt):
        """Update recording timer"""
        self.recording_time += dt
        seconds = int(self.recording_time)
        self.rec_status.text = f"Recording... {seconds}s"
    
    # ========== SERVER COMMUNICATION ==========
    def connect_to_server(self):
        """Connect to backend server"""
        def connect():
            try:
                response = requests.get(
                    f"{self.server_url}/api/health",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.is_connected = True
                    self.connection_status = "Connected"
                    
                    # Update UI on main thread
                    Clock.schedule_once(lambda dt: self.on_connect_success())
                else:
                    raise Exception("Server error")
                    
            except Exception as e:
                self.is_connected = False
                Clock.schedule_once(lambda dt: self.on_connect_fail())
        
        threading.Thread(target=connect, daemon=True).start()
    
    def on_connect_success(self):
        """Handle successful connection"""
        self.conn_indicator.color = (0.2, 0.8, 0.2, 1)
        self.connect_btn.background_color = (0.2, 0.8, 0.2, 1)
        self.connect_btn.text = "Connected"
        self.show_message("✅ Connected to server")
        self.update_status()
    
    def on_connect_fail(self):
        """Handle connection failure"""
        self.conn_indicator.color = (0.8, 0.2, 0.2, 1)
        self.connect_btn.background_color = (0.8, 0.2, 0.2, 1)
        self.connect_btn.text = "Retry"
        self.show_message("❌ Connection failed", False)
    
    def update_status(self, dt=None):
        """Update device status from server"""
        if not self.is_connected:
            return
        
        def fetch():
            try:
                response = requests.get(
                    f"{self.server_url}/api/devices",
                    timeout=3
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        Clock.schedule_once(
                            lambda dt: self.update_device_display(data['devices'])
                        )
            except:
                pass
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def update_device_display(self, devices):
        """Update UI with device status - FIXED for door"""
        for device in devices:
            name = device['device_name']
            status = device['status']
            
            # Clean status
            if '_' in status:
                status = status.split('_')[0]
            
            if name == 'light':
                self.light_status = status
                self.light_btn.text = status
                self.light_btn.background_color = self.status_colors.get(status, (0.5,0.5,0.5,1))
            
            elif name == 'fan':
                self.fan_status = status
                self.fan_btn.text = status
                self.fan_btn.background_color = self.status_colors.get(status, (0.5,0.5,0.5,1))
            
            elif name == 'fan_speed':
                try:
                    self.fan_speed = int(status)
                    self.speed_slider.value = self.fan_speed
                    self.speed_label.text = f"{self.fan_speed}%"
                except:
                    pass
            
            elif name == 'door':  # Changed from door_lock to door
                self.door_status = status
                self.door_status_label.text = f"Status: {status}"
                # Update button appearances based on status
                if status == 'LOCKED':
                    self.lock_btn.background_color = (0.8, 0.2, 0.2, 1)
                    self.unlock_btn.background_color = (0.5, 0.5, 0.5, 0.5)
                else:
                    self.lock_btn.background_color = (0.5, 0.5, 0.5, 0.5)
                    self.unlock_btn.background_color = (0.2, 0.8, 0.2, 1)
    
    def toggle_device(self, device):
        """Toggle device on/off - Only for light and fan, door has separate buttons"""
        if not self.is_connected:
            self.show_message("Connect to server first", False)
            return
        
        # Determine new state
        if device == 'light':
            new_state = 'OFF' if self.light_status == 'ON' else 'ON'
            self.send_control_command(device, new_state.lower())
        elif device == 'fan':
            new_state = 'OFF' if self.fan_status == 'ON' else 'ON'
            self.send_control_command(device, new_state.lower())
        # Door is handled by separate buttons, not toggle
    
    def on_speed_change(self, instance, value):
        """Handle fan speed change"""
        speed = int(value)
        self.speed_label.text = f"{speed}%"
        
        # Debounce speed updates
        if hasattr(self, '_speed_timer'):
            Clock.unschedule(self._speed_timer)
        
        self._speed_timer = Clock.schedule_once(
            lambda dt: self.send_speed_command(speed), 0.5
        )
    
    def send_control_command(self, device, action):
        """Send control command to server"""
        def send():
            try:
                payload = {
                    'device': device,
                    'action': action.lower()
                }
                
                response = requests.post(
                    f"{self.server_url}/api/control",
                    json=payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        Clock.schedule_once(lambda dt: self.update_status())
                        self.show_message(f"✅ {device} {action}")
                    else:
                        self.show_message(f"❌ Command failed", False)
                else:
                    self.show_message(f"❌ Server error", False)
                    
            except Exception as e:
                self.show_message(f"❌ Error: {str(e)[:20]}", False)
        
        threading.Thread(target=send, daemon=True).start()
    
    def send_speed_command(self, speed):
        """Send fan speed command"""
        def send():
            try:
                payload = {'speed': speed}
                
                response = requests.post(
                    f"{self.server_url}/api/fan-speed",
                    json=payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.show_message(f"✅ Fan speed: {speed}%")
                    
            except Exception as e:
                pass
        
        threading.Thread(target=send, daemon=True).start()
    
    def send_text_command(self, text):
        """Send text voice command"""
        if not self.is_connected:
            self.show_message("Connect to server first", False)
            return
        
        def send():
            try:
                payload = {
                    'text': text,
                    'language': self.current_language
                }
                
                self.rec_status.text = f"Sending: {text}"
                
                response = requests.post(
                    f"{self.server_url}/api/voice",
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        self.show_message(f"✅ Command executed")
                        Clock.schedule_once(lambda dt: self.update_status())
                        self.rec_status.text = "Command executed"
                        self.rec_status.color = (0.2, 0.8, 0.2, 1)
                    else:
                        self.rec_status.text = data.get('message', 'Failed')
                        self.rec_status.color = (0.8, 0.2, 0.2, 1)
                else:
                    self.rec_status.text = "Server error"
                    self.rec_status.color = (0.8, 0.2, 0.2, 1)
                    
            except Exception as e:
                self.rec_status.text = "Connection failed"
                self.rec_status.color = (0.8, 0.2, 0.2, 1)
        
        threading.Thread(target=send, daemon=True).start()
    
    def send_audio_command(self, audio_data):
        """Send audio command to server"""
        def send():
            try:
                # Save audio to temp file
                import tempfile
                import os
                
                temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp.write(audio_data)
                temp.close()
                
                # Send to server
                with open(temp.name, 'rb') as f:
                    files = {'audio': f}
                    data = {'language': self.current_language}
                    
                    response = requests.post(
                        f"{self.server_url}/api/voice-audio",
                        files=files,
                        data=data,
                        timeout=15
                    )
                
                # Clean up
                os.unlink(temp.name)
                
                if response.status_code == 200:
                    result = response.json()
                    if result['success']:
                        self.show_message(f"✅ {result['message']}")
                        Clock.schedule_once(lambda dt: self.update_status())
                        self.rec_status.text = "Command executed"
                        self.rec_status.color = (0.2, 0.8, 0.2, 1)
                    else:
                        self.rec_status.text = result.get('message', 'Failed')
                        self.rec_status.color = (0.8, 0.2, 0.2, 1)
                else:
                    self.rec_status.text = "Server error"
                    self.rec_status.color = (0.8, 0.2, 0.2, 1)
                    
            except Exception as e:
                self.rec_status.text = f"Error: {str(e)[:20]}"
                self.rec_status.color = (0.8, 0.2, 0.2, 1)
        
        threading.Thread(target=send, daemon=True).start()
    
    def on_language_change(self, spinner, text):
        """Handle language change with better display"""
        # Map display text to language code
        lang_map = {
            'English': 'english',
            'Hindi (हिंदी)': 'hindi',
            'Marathi (मराठी)': 'marathi'
        }
        
        # Map language code to display name
        display_map = {
            'english': 'English',
            'hindi': 'Hindi (हिंदी)',
            'marathi': 'Marathi (मराठी)'
        }
        
        # Map language code to short display
        short_display = {
            'english': 'English',
            'hindi': 'हिंदी',
            'marathi': 'मराठी'
        }
        
        new_lang = lang_map.get(text, 'english')
        self.current_language = new_lang
        
        # Update displays
        self.current_lang_display.text = f"Current: {short_display[new_lang]}"
        self.lang_example_label.text = f"({short_display[new_lang]})"
        
        # Update example buttons
        examples = self.examples[self.current_language][:4]
        for i, btn in enumerate(self.example_btns):
            if i < len(examples):
                btn.text = examples[i]
        
        self.show_message(f"Language: {display_map[new_lang]}")
    
    def toggle_ml(self, instance):
        """Toggle ML automation"""
        state = instance.state == 'down'
        instance.text = "ON" if state else "OFF"
        instance.background_color = (0.2, 0.8, 0.2, 1) if state else (0.8, 0.2, 0.2, 1)
        
        def send():
            try:
                payload = {'enabled': state}
                requests.post(
                    f"{self.server_url}/api/ml/toggle",
                    json=payload,
                    timeout=3
                )
            except:
                pass
        
        threading.Thread(target=send, daemon=True).start()
        self.show_message(f"ML Auto: {'ON' if state else 'OFF'}")
    
    def show_insights(self, instance):
        """Show ML insights dialog"""
        def fetch():
            try:
                response = requests.get(
                    f"{self.server_url}/api/ml/insights",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        insights = data['insights']
                        message = "\n".join(insights) if insights else "No insights yet"
                        Clock.schedule_once(
                            lambda dt: self.show_message(message, True)
                        )
            except:
                pass
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def show_ip_dialog(self, instance):
        """Show IP input dialog"""
        from kivy.uix.textinput import TextInput
        from kivy.uix.popup import Popup
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="Enter Server IP:"))
        
        ip_input = TextInput(text=self.server_ip, multiline=False)
        content.add_widget(ip_input)
        
        btn_layout = BoxLayout(size_hint=(1, 0.3), spacing=10)
        
        def save_ip(instance):
            self.server_ip = ip_input.text
            self.server_url = f"http://{self.server_ip}:5000"
            self.ip_input.text = f"IP: {self.server_ip}"
            popup.dismiss()
            self.connect_to_server()
        
        save_btn = Button(text="Save", background_color=(0.2,0.8,0.2,1))
        save_btn.bind(on_press=save_ip)
        
        cancel_btn = Button(text="Cancel", background_color=(0.8,0.2,0.2,1))
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(
            title="Server IP",
            content=content,
            size_hint=(0.8, 0.4)
        )
        popup.open()
    
    def show_message(self, message, success=True):
        """Show status message"""
        self.status_label.text = message
        self.status_label.color = (0.2, 0.8, 0.2, 1) if success else (0.8, 0.2, 0.2, 1)
        
        # Reset after 3 seconds
        def reset(dt):
            self.status_label.text = "Ready"
            self.status_label.color = (0.5, 0.5, 0.5, 1)
        
        Clock.unschedule(reset)
        Clock.schedule_once(reset, 3)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏠 AI SMART HOME MOBILE APP")
    print("="*60)
    print("1. Change server IP in the code (line 34)")
    print("2. Make sure Flask server is running")
    print("3. Press Connect button")
    print("4. Press & hold mic button to speak")
    print("5. Select language from dropdown")
    print("="*60 + "\n")
    
    SmartHomeApp().run()