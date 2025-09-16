"""
Configuration module for Renz Assistant
"""
import os
import json
import getpass
from pathlib import Path

class Config:
    """Handles configuration settings for Renz Assistant"""
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # OpenRouter API settings
        "openrouter": {
            "api_key": "",
            "default_model": "openai/gpt-3.5-turbo",
            "available_models": [
                "openai/gpt-3.5-turbo",
                "openai/gpt-4",
                "anthropic/claude-3-opus",
                "anthropic/claude-3-sonnet",
                "google/gemini-pro",
                "meta-llama/llama-3-70b-instruct",
                "mistral/mistral-7b-instruct",
                "mistral/mixtral-8x7b-instruct",
                "cohere/command-r",
                "cohere/command-r-plus"
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "use_streaming": True
        },
        
        # Voice recognition settings
        "voice_recognition": {
            "engine": "termux_api",  # Options: termux_api, vosk, whisper
            "continuous_listening": False,
            "wake_word_enabled": True,
            "wake_words": ["hey renz", "ok renz", "hello renz", "hi renz"],
            "wake_word_sensitivity": 0.7,
            "language": "id",  # Default language for voice recognition
            "timeout": 10,  # Recording timeout in seconds
            "sample_rate": 16000,
            "noise_suppression": True,
            "auto_gain_control": True,
            "vad_sensitivity": 3,  # Voice Activity Detection sensitivity (1-5)
            "silence_duration": 1.5,  # Seconds of silence to stop recording
            "whisper_model": "base",  # Options: tiny, base, small, medium, large
            "vosk_model_path": "~/vosk-model-id"  # Path to Vosk model
        },
        
        # Termux API settings
        "termux_api": {
            "enabled": True,
            "permissions": {
                "location": {
                    "background": False,
                    "foreground_approximate": True,
                    "foreground_precise": True
                },
                "camera": True,
                "microphone": True,
                "storage": True,
                "sms": True,
                "call_phone": True,
                "network": True,
                "wifi": True,
                "body_sensors": False,
                "nfc": False,
                "bluetooth": True,
                "infrared": True,
                "fingerprint": True,
                "clipboard": True,
                "notifications": True,
                "battery": True,
                "phone_state": True,
                "contacts": True,
                "call_log": True,
                "wallpaper": True,
                "torch": True,
                "vibrate": True,
                "wake_lock": True
            },
            "location_update_interval": 60,  # seconds
            "notification_check_interval": 30,  # seconds
            "background_services": {
                "location_tracking": False,
                "notification_monitoring": True,
                "battery_monitoring": True,
                "call_monitoring": False,
                "sms_monitoring": False
            },
            "notification_filters": {
                "exclude_apps": ["com.android.systemui", "android"],
                "exclude_titles": ["USB debugging connected", "Charging"],
                "priority_only": False
            }
        },
        
        # User preferences
        "user_preferences": {
            "personality": "friendly",
            "tts_speed": 1.0,
            "volume": 70,
            "language_preference": "id",
            "auto_suggestions": True,
            "learning_mode": True
        },
        
        # System settings
        "system": {
            "debug_mode": False,
            "log_level": "INFO",
            "data_directory": "~/.renz_assistant",
            "max_history": 100,
            "idle_timeout": 300  # 5 minutes
        }
    }
    
    def __init__(self, config_file=None):
        """Initialize configuration manager"""
        self.home_dir = str(Path.home())
        self.config_dir = os.path.expanduser(os.path.join(self.home_dir, ".renz_assistant"))
        
        # Ensure config directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        # Set config file path
        self.config_file = config_file or os.path.join(self.config_dir, "config.json")
        
        # Load or create configuration
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Update with any missing default values
                return self._update_with_defaults(config)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG
        else:
            # Create default config
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
    
    def _update_with_defaults(self, config):
        """Recursively update config with any missing default values"""
        result = config.copy()
        
        def update_dict(target, source):
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    update_dict(target[key], value)
            return target
        
        return update_dict(result, self.DEFAULT_CONFIG)
    
    def save_config(self, config=None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key_path, default=None):
        """
        Get a configuration value using dot notation
        Example: config.get("openrouter.api_key")
        """
        keys = key_path.split(".")
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path, value):
        """
        Set a configuration value using dot notation
        Example: config.set("openrouter.api_key", "your-api-key")
        """
        keys = key_path.split(".")
        target = self.config
        
        # Navigate to the correct nested dictionary
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the value
        target[keys[-1]] = value
        
        # Save the updated config
        self.save_config()
        return True
    
    def setup_openrouter(self):
        """Interactive setup for OpenRouter API"""
        print("\n📝 OpenRouter API Configuration")
        print("------------------------------")
        
        current_key = self.get("openrouter.api_key", "")
        if current_key:
            print(f"Current API Key: {current_key[:5]}...{current_key[-5:] if len(current_key) > 10 else ''}")
            change = input("Change API Key? (y/n): ").lower() == 'y'
        else:
            change = True
        
        if change:
            api_key = getpass.getpass("Enter OpenRouter API Key: ")
            if api_key:
                self.set("openrouter.api_key", api_key)
                print("✅ API Key saved")
            else:
                print("⚠️ API Key not changed")
        
        # Model selection
        print("\nAvailable Models:")
        models = self.get("openrouter.available_models", [])
        current_model = self.get("openrouter.default_model", "")
        
        for i, model in enumerate(models):
            is_current = " (current)" if model == current_model else ""
            print(f"{i+1}. {model}{is_current}")
        
        try:
            choice = input(f"\nSelect default model (1-{len(models)}, Enter to keep current): ")
            if choice.strip():
                index = int(choice) - 1
                if 0 <= index < len(models):
                    self.set("openrouter.default_model", models[index])
                    print(f"✅ Default model set to: {models[index]}")
                else:
                    print("⚠️ Invalid selection, keeping current model")
        except ValueError:
            print("⚠️ Invalid input, keeping current model")
        
        # Advanced model settings
        print("\n⚙️ Advanced Model Settings:")
        
        # Temperature
        current_temp = self.get("openrouter.temperature", 0.7)
        try:
            temp = input(f"Temperature (0.0-2.0, currently {current_temp}): ")
            if temp.strip():
                temp_val = float(temp)
                if 0.0 <= temp_val <= 2.0:
                    self.set("openrouter.temperature", temp_val)
                    print(f"✅ Temperature set to: {temp_val}")
                else:
                    print("⚠️ Invalid value, must be between 0.0 and 2.0")
        except ValueError:
            print("⚠️ Invalid input, keeping current temperature")
        
        # Max tokens
        current_max_tokens = self.get("openrouter.max_tokens", 1000)
        try:
            max_tokens = input(f"Max tokens (currently {current_max_tokens}): ")
            if max_tokens.strip() and max_tokens.isdigit():
                self.set("openrouter.max_tokens", int(max_tokens))
                print(f"✅ Max tokens set to: {max_tokens}")
        except ValueError:
            print("⚠️ Invalid input, keeping current max tokens")
        
        # Top P
        current_top_p = self.get("openrouter.top_p", 1.0)
        try:
            top_p = input(f"Top P (0.0-1.0, currently {current_top_p}): ")
            if top_p.strip():
                top_p_val = float(top_p)
                if 0.0 <= top_p_val <= 1.0:
                    self.set("openrouter.top_p", top_p_val)
                    print(f"✅ Top P set to: {top_p_val}")
                else:
                    print("⚠️ Invalid value, must be between 0.0 and 1.0")
        except ValueError:
            print("⚠️ Invalid input, keeping current Top P")
        
        # Frequency penalty
        current_freq_penalty = self.get("openrouter.frequency_penalty", 0.0)
        try:
            freq_penalty = input(f"Frequency penalty (-2.0 to 2.0, currently {current_freq_penalty}): ")
            if freq_penalty.strip():
                freq_penalty_val = float(freq_penalty)
                if -2.0 <= freq_penalty_val <= 2.0:
                    self.set("openrouter.frequency_penalty", freq_penalty_val)
                    print(f"✅ Frequency penalty set to: {freq_penalty_val}")
                else:
                    print("⚠️ Invalid value, must be between -2.0 and 2.0")
        except ValueError:
            print("⚠️ Invalid input, keeping current frequency penalty")
        
        # Presence penalty
        current_pres_penalty = self.get("openrouter.presence_penalty", 0.0)
        try:
            pres_penalty = input(f"Presence penalty (-2.0 to 2.0, currently {current_pres_penalty}): ")
            if pres_penalty.strip():
                pres_penalty_val = float(pres_penalty)
                if -2.0 <= pres_penalty_val <= 2.0:
                    self.set("openrouter.presence_penalty", pres_penalty_val)
                    print(f"✅ Presence penalty set to: {pres_penalty_val}")
                else:
                    print("⚠️ Invalid value, must be between -2.0 and 2.0")
        except ValueError:
            print("⚠️ Invalid input, keeping current presence penalty")
        
        # Streaming
        current_streaming = self.get("openrouter.use_streaming", True)
        print(f"\nStreaming responses: {'Enabled' if current_streaming else 'Disabled'}")
        choice = input("Enable streaming responses? (y/n, Enter to keep current): ").lower()
        
        if choice == 'y':
            self.set("openrouter.use_streaming", True)
            print("✅ Streaming responses enabled")
        elif choice == 'n':
            self.set("openrouter.use_streaming", False)
            print("✅ Streaming responses disabled")
    
    def setup_voice_recognition(self):
        """Interactive setup for voice recognition"""
        print("\n🎤 Voice Recognition Configuration")
        print("--------------------------------")
        
        # Engine selection
        engines = ["termux_api", "vosk", "whisper"]
        current_engine = self.get("voice_recognition.engine", "termux_api")
        
        print("Available engines:")
        for i, engine in enumerate(engines):
            is_current = " (current)" if engine == current_engine else ""
            print(f"{i+1}. {engine}{is_current}")
        
        try:
            choice = input(f"\nSelect voice recognition engine (1-{len(engines)}, Enter to keep current): ")
            if choice.strip():
                index = int(choice) - 1
                if 0 <= index < len(engines):
                    self.set("voice_recognition.engine", engines[index])
                    print(f"✅ Voice recognition engine set to: {engines[index]}")
                else:
                    print("⚠️ Invalid selection, keeping current engine")
        except ValueError:
            print("⚠️ Invalid input, keeping current engine")
        
        # Language selection
        current_language = self.get("voice_recognition.language", "id")
        print(f"\nVoice recognition language: {current_language}")
        new_language = input("Enter language code (e.g., id, en, Enter to keep current): ")
        if new_language.strip():
            self.set("voice_recognition.language", new_language.strip())
            print(f"✅ Voice recognition language set to: {new_language}")
        
        # Wake word settings
        print("\n🔊 Wake Word Settings:")
        
        # Enable/disable wake word
        wake_word_enabled = self.get("voice_recognition.wake_word_enabled", True)
        print(f"Wake word detection: {'Enabled' if wake_word_enabled else 'Disabled'}")
        choice = input("Enable wake word detection? (y/n, Enter to keep current): ").lower()
        
        if choice == 'y':
            self.set("voice_recognition.wake_word_enabled", True)
            print("✅ Wake word detection enabled")
        elif choice == 'n':
            self.set("voice_recognition.wake_word_enabled", False)
            print("✅ Wake word detection disabled")
        
        # Wake words
        current_wake_words = self.get("voice_recognition.wake_words", ["hey renz", "ok renz"])
        print(f"Current wake words: {', '.join(current_wake_words)}")
        new_wake_words = input("Enter comma-separated wake words (Enter to keep current): ")
        if new_wake_words.strip():
            wake_words = [word.strip().lower() for word in new_wake_words.split(",")]
            self.set("voice_recognition.wake_words", wake_words)
            print(f"✅ Wake words set to: {', '.join(wake_words)}")
        
        # Wake word sensitivity
        current_sensitivity = self.get("voice_recognition.wake_word_sensitivity", 0.7)
        print(f"Wake word sensitivity: {current_sensitivity} (0.0-1.0, higher is more sensitive)")
        
        try:
            choice = input("Enter new sensitivity (0.0-1.0, Enter to keep current): ")
            if choice.strip():
                sensitivity = float(choice)
                if 0.0 <= sensitivity <= 1.0:
                    self.set("voice_recognition.wake_word_sensitivity", sensitivity)
                    print(f"✅ Wake word sensitivity set to: {sensitivity}")
                else:
                    print("⚠️ Invalid value, must be between 0.0 and 1.0")
        except ValueError:
            print("⚠️ Invalid input, keeping current sensitivity")
        
        # Continuous listening
        current_continuous = self.get("voice_recognition.continuous_listening", False)
        print(f"\nContinuous listening mode: {'Enabled' if current_continuous else 'Disabled'}")
        choice = input("Enable continuous listening? (y/n, Enter to keep current): ").lower()
        
        if choice == 'y':
            self.set("voice_recognition.continuous_listening", True)
            print("✅ Continuous listening enabled")
        elif choice == 'n':
            self.set("voice_recognition.continuous_listening", False)
            print("✅ Continuous listening disabled")
        
        # Recording settings
        print("\n🎙️ Recording Settings:")
        
        # Timeout
        current_timeout = self.get("voice_recognition.timeout", 10)
        try:
            timeout = input(f"Recording timeout in seconds (currently {current_timeout}): ")
            if timeout.strip() and timeout.isdigit():
                self.set("voice_recognition.timeout", int(timeout))
                print(f"✅ Recording timeout set to: {timeout} seconds")
        except ValueError:
            print("⚠️ Invalid input, keeping current timeout")
        
        # Noise suppression
        noise_suppression = self.get("voice_recognition.noise_suppression", True)
        choice = input(f"Enable noise suppression? (y/n, currently {'enabled' if noise_suppression else 'disabled'}): ").lower()
        if choice in ('y', 'n'):
            self.set("voice_recognition.noise_suppression", choice == 'y')
            print(f"✅ Noise suppression {'enabled' if choice == 'y' else 'disabled'}")
        
        # Auto gain control
        auto_gain = self.get("voice_recognition.auto_gain_control", True)
        choice = input(f"Enable auto gain control? (y/n, currently {'enabled' if auto_gain else 'disabled'}): ").lower()
        if choice in ('y', 'n'):
            self.set("voice_recognition.auto_gain_control", choice == 'y')
            print(f"✅ Auto gain control {'enabled' if choice == 'y' else 'disabled'}")
        
        # VAD sensitivity
        vad_sensitivity = self.get("voice_recognition.vad_sensitivity", 3)
        try:
            sensitivity = input(f"Voice Activity Detection sensitivity (1-5, currently {vad_sensitivity}): ")
            if sensitivity.strip() and sensitivity.isdigit():
                sens_val = int(sensitivity)
                if 1 <= sens_val <= 5:
                    self.set("voice_recognition.vad_sensitivity", sens_val)
                    print(f"✅ VAD sensitivity set to: {sens_val}")
                else:
                    print("⚠️ Invalid value, must be between 1 and 5")
        except ValueError:
            print("⚠️ Invalid input, keeping current VAD sensitivity")
        
        # Engine-specific settings
        if current_engine == "whisper" or self.get("voice_recognition.engine") == "whisper":
            print("\n🤖 Whisper Model Settings:")
            whisper_models = ["tiny", "base", "small", "medium", "large"]
            current_model = self.get("voice_recognition.whisper_model", "base")
            
            print("Available Whisper models:")
            for i, model in enumerate(whisper_models):
                is_current = " (current)" if model == current_model else ""
                print(f"{i+1}. {model}{is_current}")
            
            try:
                choice = input(f"Select Whisper model (1-{len(whisper_models)}, Enter to keep current): ")
                if choice.strip():
                    index = int(choice) - 1
                    if 0 <= index < len(whisper_models):
                        self.set("voice_recognition.whisper_model", whisper_models[index])
                        print(f"✅ Whisper model set to: {whisper_models[index]}")
                    else:
                        print("⚠️ Invalid selection, keeping current model")
            except ValueError:
                print("⚠️ Invalid input, keeping current model")
        
        elif current_engine == "vosk" or self.get("voice_recognition.engine") == "vosk":
            print("\n🤖 Vosk Model Settings:")
            current_path = self.get("voice_recognition.vosk_model_path", "~/vosk-model-id")
            new_path = input(f"Enter path to Vosk model (currently {current_path}): ")
            if new_path.strip():
                self.set("voice_recognition.vosk_model_path", new_path)
                print(f"✅ Vosk model path set to: {new_path}")
    
    def setup_termux_api(self):
        """Interactive setup for Termux API permissions"""
        print("\n📱 Termux API Configuration")
        print("-------------------------")
        
        # Enable/disable Termux API
        current_enabled = self.get("termux_api.enabled", True)
        print(f"Termux API integration: {'Enabled' if current_enabled else 'Disabled'}")
        choice = input("Enable Termux API integration? (y/n, Enter to keep current): ").lower()
        
        if choice == 'y':
            self.set("termux_api.enabled", True)
            print("✅ Termux API integration enabled")
        elif choice == 'n':
            self.set("termux_api.enabled", False)
            print("✅ Termux API integration disabled")
            return
        
        # Configure permissions
        print("\nConfigure Termux API permissions:")
        permissions = self.get("termux_api.permissions", {})
        
        # Location permissions
        print("\n📍 Location permissions:")
        location = permissions.get("location", {})
        
        bg_loc = location.get("background", False)
        choice = input(f"Allow background location access? (y/n, currently {'enabled' if bg_loc else 'disabled'}): ").lower()
        if choice in ('y', 'n'):
            self.set("termux_api.permissions.location.background", choice == 'y')
        
        fg_approx = location.get("foreground_approximate", True)
        choice = input(f"Allow approximate location in foreground? (y/n, currently {'enabled' if fg_approx else 'disabled'}): ").lower()
        if choice in ('y', 'n'):
            self.set("termux_api.permissions.location.foreground_approximate", choice == 'y')
        
        fg_precise = location.get("foreground_precise", True)
        choice = input(f"Allow precise location in foreground? (y/n, currently {'enabled' if fg_precise else 'disabled'}): ").lower()
        if choice in ('y', 'n'):
            self.set("termux_api.permissions.location.foreground_precise", choice == 'y')
        
        # Other permissions
        permission_list = [
            ("camera", "📷 Camera access"),
            ("microphone", "🎤 Microphone access"),
            ("storage", "💾 Storage access"),
            ("sms", "📱 SMS access"),
            ("call_phone", "📞 Phone call access"),
            ("network", "🌐 Network access"),
            ("wifi", "📶 Wi-Fi control"),
            ("body_sensors", "❤️ Body sensors access"),
            ("nfc", "📲 NFC control"),
            ("bluetooth", "🔵 Bluetooth control"),
            ("infrared", "🔴 Infrared transmitter"),
            ("fingerprint", "👆 Fingerprint authentication"),
            ("clipboard", "📋 Clipboard access"),
            ("notifications", "🔔 Notifications access"),
            ("battery", "🔋 Battery status access"),
            ("phone_state", "📱 Phone state access"),
            ("contacts", "👥 Contacts access"),
            ("call_log", "📞 Call log access"),
            ("wallpaper", "🖼️ Wallpaper control"),
            ("torch", "🔦 Flashlight control"),
            ("vibrate", "📳 Vibration control"),
            ("wake_lock", "🔒 Wake lock control")
        ]
        
        print("\nOther permissions:")
        for perm_key, perm_name in permission_list:
            current = permissions.get(perm_key, True)
            choice = input(f"{perm_name}? (y/n, currently {'enabled' if current else 'disabled'}): ").lower()
            if choice in ('y', 'n'):
                self.set(f"termux_api.permissions.{perm_key}", choice == 'y')
        
        # Background services
        print("\n🔄 Background services:")
        bg_services = self.get("termux_api.background_services", {})
        
        service_list = [
            ("location_tracking", "📍 Location tracking"),
            ("notification_monitoring", "🔔 Notification monitoring"),
            ("battery_monitoring", "🔋 Battery monitoring"),
            ("call_monitoring", "📞 Call monitoring"),
            ("sms_monitoring", "📱 SMS monitoring")
        ]
        
        for service_key, service_name in service_list:
            current = bg_services.get(service_key, False)
            choice = input(f"Enable {service_name}? (y/n, currently {'enabled' if current else 'disabled'}): ").lower()
            if choice in ('y', 'n'):
                self.set(f"termux_api.background_services.{service_key}", choice == 'y')
        
        # Notification filters
        print("\n🔔 Notification filters:")
        notif_filters = self.get("termux_api.notification_filters", {})
        
        # Excluded apps
        excluded_apps = notif_filters.get("exclude_apps", [])
        print(f"Currently excluded apps: {', '.join(excluded_apps) if excluded_apps else 'None'}")
        new_excluded = input("Enter comma-separated list of apps to exclude (Enter to keep current): ")
        if new_excluded.strip():
            self.set("termux_api.notification_filters.exclude_apps", [app.strip() for app in new_excluded.split(",")])
        
        # Priority only
        priority_only = notif_filters.get("priority_only", False)
        choice = input(f"Monitor priority notifications only? (y/n, currently {'enabled' if priority_only else 'disabled'}): ").lower()
        if choice in ('y', 'n'):
            self.set("termux_api.notification_filters.priority_only", choice == 'y')
        
        # Update intervals
        try:
            print("\n⏱️ Update intervals:")
            current_loc_interval = self.get("termux_api.location_update_interval", 60)
            loc_interval = input(f"Location update interval in seconds (currently {current_loc_interval}): ")
            if loc_interval.strip() and loc_interval.isdigit():
                self.set("termux_api.location_update_interval", int(loc_interval))
            
            current_notif_interval = self.get("termux_api.notification_check_interval", 30)
            notif_interval = input(f"Notification check interval in seconds (currently {current_notif_interval}): ")
            if notif_interval.strip() and notif_interval.isdigit():
                self.set("termux_api.notification_check_interval", int(notif_interval))
        except ValueError:
            print("⚠️ Invalid input, using default values")
    
    def interactive_setup(self):
        """Run interactive setup for all configuration sections"""
        print("\n🔧 Renz Assistant Configuration Setup")
        print("==================================")
        
        self.setup_openrouter()
        self.setup_voice_recognition()
        self.setup_termux_api()
        
        print("\n✅ Configuration complete!")
        print(f"Configuration saved to: {self.config_file}")