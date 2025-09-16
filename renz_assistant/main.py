"""
Main module for Renz Assistant
"""
import os
import sys
import time
import json
import random
import signal
import threading
from datetime import datetime

# Import modules
from renz_assistant.modules.utils import cosine_similarity_manual
from renz_assistant.modules.audio import AudioProcessor, TextToSpeech
from renz_assistant.modules.nlp import LanguageProcessor
from renz_assistant.modules.storage import DataManager
from renz_assistant.modules.services import BackgroundServices
from renz_assistant.modules.device import DeviceInterface, TermuxAPI
from renz_assistant.modules.weather import WeatherService
from renz_assistant.modules.config import Config
from renz_assistant.modules.voice_recognition import VoiceRecognitionManager
from renz_assistant.modules.openrouter import OpenRouterClient, AIAssistant

class RenzAssistant:
    """Main Renz Assistant class that integrates all modules"""
    
    def __init__(self, base_path="."):
        """Initialize Renz Assistant"""
        print("🎉 Initializing Renz Advanced Voice Assistant...")
        
        # Initialize configuration
        self.config = Config(os.path.join(base_path, "config.json"))
        
        # Initialize data manager
        self.data_manager = DataManager(base_path)
        
        # Load data
        self.memory = self.data_manager.load_memory()
        self.voice_profile = self.data_manager.load_voice_profile()
        self.usage_log = self.data_manager.load_usage_log()
        self.notes = self.data_manager.load_notes()
        self.reminders = self.data_manager.load_reminders()
        self.user_preferences = self.data_manager.load_user_preferences()
        self.learning_data = self.data_manager.load_learning_data()
        self.personality_profiles = self.data_manager.load_personality_profiles()
        
        # Save memory to ensure file exists
        self.data_manager.save_memory(self.memory)
        
        # Initialize language processor
        self.nlp = LanguageProcessor()
        
        # Initialize audio processor
        self.audio = AudioProcessor()
        
        # Initialize TTS
        self.tts = TextToSpeech(
            language_detector=self.nlp.detect_lang,
            user_preferences=self.user_preferences,
            personality_profiles=self.personality_profiles
        )
        
        # Initialize device interface
        self.language = self.user_preferences.get("language_preference", "id")
        self.device = DeviceInterface(language=self.language)
        
        # Initialize weather service
        self.weather = WeatherService(memory=self.memory)
        
        # Initialize Termux API
        termux_config = self.config.get("termux_api", {})
        self.termux_api = TermuxAPI(termux_config)
        
        # Initialize voice recognition
        voice_config = self.config.get("voice_recognition", {})
        self.voice_recognition = VoiceRecognitionManager(voice_config)
        
        # Initialize OpenRouter client
        openrouter_config = self.config.get("openrouter", {})
        self.openrouter = OpenRouterClient(
            api_key=openrouter_config.get("api_key", ""),
            default_model=openrouter_config.get("default_model", "openai/gpt-3.5-turbo")
        )
        
        # Initialize AI Assistant
        system_prompt = (
            "You are Renz, an advanced voice assistant for Android devices. "
            "You are helpful, friendly, and concise in your responses. "
            "You can control device features, provide information, and assist with tasks. "
            "Always prioritize the user's privacy and security."
        )
        self.ai_assistant = AIAssistant(
            client=self.openrouter,
            system_prompt=system_prompt
        )
        
        # State variables
        self.is_active = False
        self.current_mood = "neutral"
        self.last_command = ""
        self.last_response = ""
        self.conversation_context = []
        self.music_queue = []
        self.current_music_index = 0
        self.is_playing_music = False
        self.security_authenticated = False
        self.idle_timeout = self.config.get("system.idle_timeout", 300)  # 5 minutes
        self.last_activity = time.time()
        self.current_wav_file = None
        
        # Wake words (multilingual)
        self.wake_words = [
            "hey renz",
            "hai",
            "hi",
            "ren",
            "bangun",
            "turn on the system",
            "nyalakan sistem",
            "aktif",
            "online",
            "wakeup",
            "renz",
            "hai renz",
            "halo renz",
            "hello renz",
            "renz turn on the system",
            "renz wake up",
            "yo renz",
            "renz are you there",
            "renz listen up",
            "wake up renz",
            "renz bangun",
            "renz aktif",
            "renz hidupkan",
            "renz mulai",
            "renz ayo aktif",
            "renz saatnya kerja",
            "renz waktunya aktif",
        ]

        # Sleep words
        self.sleep_words = [
            "renz turn off the system",
            "tidur renz",
            "goodbye renz",
            "renz sleep",
            "renz shutdown",
            "renz mati",
            "renz off",
            "matikan sistem",
        ]
        
        # Jokes dictionary
        self.jokes = {
            "kenapa matahari tenggelam": "Karena nggak bisa berenang",
            "burung, burung apa yang suka nolak": "Burung gakgak",
            "sayuran apa yang dingin": "Kembang cold",
            "nun mati bertemu ain": "Ain-nya terkejut",
            "gula, gula apa yang bukan gula": "Gula aren't",
            "nama kota apa yang banyak bapak-bapaknya": "Purwodaddy",
            "bakso apa yang nggak boleh dilihat tapi enak dimakan": "Bakso aurat",
            "hewan apa yang taat lalu lintas": "Unta-makan keselamatan",
            "ikan, ikan apa yang bisa terbang": "Lelelawar",
            "kenapa air mata warnanya bening": "Kalau warna ijo namanya air matcha",
            "susu, susu apa yang selalu telat": "Susu kedelay",
            "superhero yang selalu selamat di setiap keadaan": "AkuAman",
            "roti, roti apa yang suka nyuri": "Jambread",
            "kumis, kumis apa yang bikin salting": "Kumiss you",
            "kenapa ginjal ada dua": "Karena kalau satu ganjil",
            "gunung sumbing kalau meletus bunyinya": "Nuaaall",
            "huruf apa yang paling kedinginan": "B, karena berada di tengah-tengah AC",
            "kera, kera apa yang diinjak nggak marah": "Keramik",
            "gajah, gajah apa yang baik": "Gajahat",
            "kue, kue apa yang nggak pernah bohong": "Kue cucur",
            "hewan apa yang deket banget sama temen": "A Crab",
            "siapa pemain bola yang punya usaha pengobatan": "David Bekam",
            "bubur apa yang kecil tapi bisa digedein": "Bubur zoom-zoom",
        }
        
        # Initialize knowledge base
        self.setup_knowledge_base()
        
        # Initialize background services
        self.services = BackgroundServices(self)
        
        # Graceful shutdown on Ctrl+C
        signal.signal(signal.SIGINT, self.handle_exit)
        
        # Check voice profile
        if not self.voice_profile:
            print("🔐 Voice profile not found. Starting registration process...")
            self.register_voice_profile()
            
        # Start background services
        self.services.start_all_services()
        
        # Start Termux API services if enabled
        if self.config.get("termux_api.enabled", True):
            self.termux_api.start_background_services()
        
        print("✅ Renz Assistant initialized successfully!")
    
    def setup_knowledge_base(self):
        """Setup knowledge base for assistant"""
        self.knowledge_base = {
            "mathematics": {
                "algebra": "I can help with algebraic equations, polynomials, and systems of equations",
                "calculus": "I can assist with derivatives, integrals, and limits",
                "geometry": "I can help with geometric calculations and proofs",
            },
            "physics": {
                "mechanics": "I can help with motion, forces, and energy calculations",
                "thermodynamics": "I can assist with heat, temperature, and energy transfer",
                "electromagnetism": "I can help with electrical and magnetic phenomena",
            },
            "chemistry": {
                "organic": "I can help with organic compounds and reactions",
                "inorganic": "I can assist with inorganic chemistry and periodic table",
                "analytical": "I can help with chemical analysis and lab techniques",
            },
            "biology": {
                "cell_biology": "I can help with cellular processes and structures",
                "genetics": "I can assist with inheritance patterns and DNA",
                "ecology": "I can help with ecosystems and environmental interactions",
            },
        }
    
    def handle_exit(self, signum, frame):
        """Handle graceful exit"""
        self._cleanup_temp()
        
        # Stop Termux API services
        if self.termux_api:
            self.termux_api.stop_background_services()
        
        # Clean up voice recognition resources
        if self.voice_recognition:
            self.voice_recognition.cleanup()
        
        sys.exit(0)
    
    def _cleanup_temp(self):
        """Clean up temporary files"""
        try:
            temp_patterns = ["temp_voice_sample", "temp_audio_"]
            for filename in os.listdir("."):
                if any(filename.startswith(pattern) for pattern in temp_patterns):
                    if filename.endswith(".amr") or filename.endswith(".wav") or filename.endswith(".opus"):
                        os.remove(filename)
                        print(f"Removed temp file: {filename}")
        except Exception as e:
            print(f"Error during temp files cleanup: {e}")
    
    def register_voice_profile(self):
        """Enhanced voice registration with security features"""
        try:
            print("🎤 Voice Authentication Setup")
            print("Choose registration method:")
            print("1. Record new samples (Recommended)")
            print("2. Use existing WAV files")

            choice = input("Enter choice (1 or 2): ").strip()

            if choice == "2":
                print("Enter WAV file paths (minimum 3 files):")
                wav_files = []
                while len(wav_files) < 3:
                    path = input(f"WAV file {len(wav_files) + 1}: ").strip()
                    if not path:
                        break
                    if os.path.exists(path):
                        wav_files.append(path)
                    else:
                        print("File not found!")

                if len(wav_files) >= 3:
                    voice_profile = self.audio.create_voice_profile_from_files(wav_files)
                    if voice_profile:
                        self.voice_profile = voice_profile
                        self.data_manager.save_voice_profile(voice_profile)
                        print("🎉 Voice profile created successfully!")
                        self.tts.advanced_tts("Voice authentication setup complete!", "happy")
                        return True
                    else:
                        print("Insufficient files. Switching to recording mode.")

            # Record new samples
            samples = []
            print("🔐 Recording voice samples for authentication...")

            for i in range(self.audio.SAMPLE_COUNT):
                print(f"\n🔊 Sample {i + 1}/{self.audio.SAMPLE_COUNT}")
                print(
                    "Please say: 'My name is [your name] and I authorize access to Renz'"
                )

                self.tts.advanced_tts(f"Recording sample {i + 1}. Please speak clearly.", "neutral")
                time.sleep(1)

                if self.audio.record_audio_sample():
                    features = self.audio.extract_voice_features(self.audio.TEMP_WAV)
                    if features:
                        samples.append(features)
                        print("✅ Sample recorded successfully")
                    else:
                        print("❌ Failed to extract features. Try again.")
                        i -= 1
                else:
                    print("❌ Recording failed. Try again.")
                    i -= 1

                self._cleanup_temp()

            if len(samples) >= self.audio.SAMPLE_COUNT:
                # Calculate dynamic threshold
                similarities = []
                for i in range(len(samples) - 1):
                    sim = cosine_similarity_manual(samples[i], samples[i + 1])
                    similarities.append(sim)

                import numpy as np
                mean_sim = np.mean(similarities)
                std_sim = np.std(similarities)
                threshold = max(0.75, mean_sim - 0.5 * std_sim)

                voice_profile = {
                    "samples": samples,
                    "threshold": threshold,
                    "created_at": datetime.now().isoformat(),
                    "security_level": "high",
                }

                self.data_manager.save_voice_profile(voice_profile)
                self.voice_profile = voice_profile

                print("🎉 Voice profile created successfully!")
                self.tts.advanced_tts(
                    "Voice authentication setup complete!", "happy")
                return True

            return False

        except Exception as e:
            print(f"❌ Voice registration failed: {e}")
            return False
    
    def authenticate_voice_for_command(self):
        """Quick voice authentication for sensitive commands"""
        if self.security_authenticated:
            return True

        print("🔐 Voice authentication required")
        self.tts.advanced_tts("Please provide voice authentication", "serious")

        # Record short authentication sample
        if self.audio.record_audio_sample():
            result = self.audio.authenticate_voice(self.audio.TEMP_WAV, self.voice_profile)
            self._cleanup_temp()
            if result:
                self.security_authenticated = True
            return result

        return False
    
    def start_jokes_mode(self):
        """Start interactive jokes session"""
        stop_phrases = {"exit", "stop", "berhenti", "cukup", "selesai", "keluar", "ga lucu"}
        
        print("🤖 Yuk kita bercanda! Ketik 'exit' atau 'stop' untuk selesai.")
        keys = list(self.jokes.keys())
        random.shuffle(keys)

        for question in keys:
            # Display question
            print(f"\n❓ {question.capitalize()}?")
            self.tts.advanced_tts(f"{question}?", "funny")

            # Wait for user input
            user_input = input("👤 ").strip().lower()
            if user_input in stop_phrases:
                print("✅ Sesi jokes selesai. Semoga terhibur!")
                self.tts.advanced_tts("Sesi jokes selesai. Semoga terhibur!", "happy")
                break

            # If not stop, continue with punchline & laughter
            punch = self.jokes[question]
            print(f"😁 {punch}")
            self.tts.advanced_tts(punch, "funny")
            print("😂 HAHAHAHA!")
            self.tts.advanced_tts("HAHAHAHHAAWAHA", "happy")
        else:
            # All jokes have been read
            print("\n✅ Semua jokes sudah dibacakan!")
            self.tts.advanced_tts("Semua jokes sudah dibacakan!", "happy")
    
    def log_activity(self, activity_type, details=None):
        """Log user activity"""
        return self.data_manager.log_activity(activity_type, details, self.usage_log)
    
    def analyze_usage_patterns(self):
        """Analyze usage patterns for suggestions"""
        # This is a placeholder implementation
        # In a full implementation, this would analyze the usage_log data
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 10:
            return ["Good morning! Would you like to hear today's weather forecast?"]
        elif 11 <= current_hour < 14:
            return ["It's lunch time. Would you like me to set a reminder for your afternoon tasks?"]
        elif 18 <= current_hour < 22:
            return ["Good evening! Would you like me to summarize your day's activities?"]
        
        return []
    
    def process_command(self, text):
        """Process user command"""
        # Update last activity time
        self.last_activity = time.time()
        
        # Check for wake/sleep words
        action = self.nlp.process_wake_sleep_words(text, self.wake_words, self.sleep_words, self.is_active)
        if action == "wake":
            self.is_active = True
            personality = self.user_preferences.get("personality", "friendly")
            greeting = self.personality_profiles.get(personality, {}).get("greeting", "Hello! How can I help?")
            print("🎉 Renz activated!")
            self.tts.advanced_tts(greeting, "happy")
            return True
        elif action == "sleep":
            self.is_active = False
            print("💤 Renz going to sleep...")
            self.tts.advanced_tts("Going to sleep. Say wake word to activate me again.", "calm")
            return True
        
        # If not active, don't process further
        if not self.is_active:
            return False
        
        # Detect mood
        mood = self.nlp.detect_mood(text, self.conversation_context)
        self.current_mood = mood
        
        # Store in conversation context
        self.conversation_context.append({
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "mood": mood
        })
        
        # Keep context manageable
        if len(self.conversation_context) > 20:
            self.conversation_context = self.conversation_context[-20:]
        
        # Store in memory
        self.memory["emotional_state_history"].append({
            "mood": mood,
            "timestamp": datetime.now().isoformat(),
            "text": text[:100]
        })
        
        # Keep only last 50 mood entries
        if len(self.memory["emotional_state_history"]) > 50:
            self.memory["emotional_state_history"] = self.memory["emotional_state_history"][-50:]
        
        self.data_manager.save_memory(self.memory)
        
        # Process specific commands
        
        # Check for configuration command
        if "configure" in text.lower() or "setup" in text.lower() or "settings" in text.lower():
            print("🔧 Starting configuration...")
            self.tts.advanced_tts("Starting configuration. Please follow the instructions on screen.", "neutral")
            self.config.interactive_setup()
            self.tts.advanced_tts("Configuration complete!", "happy")
            return True
        
        # Check for app opening command
        app_name = self.nlp.extract_app_name(text)
        if app_name:
            response = self.device.open_app(app_name, self.log_activity)
            self.tts.advanced_tts(response)
            return True
        
        # Check for jokes mode
        if "joke" in text.lower() or "jokes" in text.lower() or "lucu" in text.lower():
            self.start_jokes_mode()
            return True
        
        # Check for weather request
        if "weather" in text.lower() or "cuaca" in text.lower():
            response = self.weather.get_current_weather(save_callback=self.data_manager.save_memory)
            self.tts.advanced_tts(response)
            return True
        
        # Check for time request
        if "time" in text.lower() or "waktu" in text.lower() or "jam" in text.lower():
            response = self.device.get_current_time()
            self.tts.advanced_tts(response)
            return True
        
        # Check for date request
        if "date" in text.lower() or "tanggal" in text.lower():
            response = self.device.get_current_date()
            self.tts.advanced_tts(response)
            return True
        
        # Check for battery status request
        if "battery" in text.lower() or "baterai" in text.lower():
            # Use Termux API if available
            if self.termux_api and self.termux_api.is_available:
                battery_data = self.termux_api.get_battery_status()
                if battery_data:
                    percentage = battery_data.get("percentage", "unknown")
                    status = battery_data.get("status", "unknown")
                    temperature = battery_data.get("temperature", "unknown")
                    response = f"Battery: {percentage}% ({status}), Temperature: {temperature}°C"
                else:
                    response = self.device.get_battery_status()
            else:
                response = self.device.get_battery_status()
            
            self.tts.advanced_tts(response)
            return True
        
        # Check for location request
        if "location" in text.lower() or "lokasi" in text.lower() or "where am i" in text.lower() or "dimana" in text.lower():
            if self.termux_api and self.termux_api.is_available:
                location = self.termux_api.get_location()
                if location:
                    lat = location.get("latitude")
                    lon = location.get("longitude")
                    response = f"Your current location is at coordinates: {lat}, {lon}"
                else:
                    response = "I couldn't determine your location. Please check location permissions."
            else:
                response = "Location services are not available."
            
            self.tts.advanced_tts(response)
            return True
        
        # Check for flashlight control
        if "flashlight" in text.lower() or "flash" in text.lower() or "light" in text.lower() or "senter" in text.lower():
            if "on" in text.lower() or "nyala" in text.lower() or "turn on" in text.lower():
                if self.termux_api and self.termux_api.is_available:
                    success = self.termux_api.toggle_flashlight(True)
                    response = "Flashlight turned on" if success else "Failed to turn on flashlight"
                else:
                    response = self.device.control_flashlight("on")
            elif "off" in text.lower() or "mati" in text.lower() or "turn off" in text.lower():
                if self.termux_api and self.termux_api.is_available:
                    success = self.termux_api.toggle_flashlight(False)
                    response = "Flashlight turned off" if success else "Failed to turn off flashlight"
                else:
                    response = self.device.control_flashlight("off")
            else:
                response = "Please specify whether to turn the flashlight on or off."
            
            self.tts.advanced_tts(response)
            return True
        
        # Check for volume control
        if "volume" in text.lower() or "sound" in text.lower() or "suara" in text.lower():
            # Extract number from text
            import re
            volume_match = re.search(r'\b(\d+)\b', text)
            
            if volume_match:
                volume_level = int(volume_match.group(1))
                
                # Determine which volume stream to adjust
                stream = "music"  # Default
                if "alarm" in text.lower():
                    stream = "alarm"
                elif "ring" in text.lower() or "call" in text.lower():
                    stream = "ring"
                elif "notification" in text.lower() or "notif" in text.lower():
                    stream = "notification"
                
                # Set volume
                if self.termux_api and self.termux_api.is_available:
                    success = self.termux_api.set_volume(stream, volume_level)
                    response = f"{stream.capitalize()} volume set to {volume_level}" if success else f"Failed to set {stream} volume"
                else:
                    response = self.device.control_volume(stream, volume_level)
            else:
                response = "Please specify a volume level between 0 and 15."
            
            self.tts.advanced_tts(response)
            return True
        
        # Check for Wi-Fi control
        if "wifi" in text.lower() or "wi-fi" in text.lower() or "wi fi" in text.lower():
            if "on" in text.lower() or "enable" in text.lower() or "activate" in text.lower() or "nyala" in text.lower():
                if self.termux_api and self.termux_api.is_available:
                    success = self.termux_api.enable_wifi()
                    response = "Wi-Fi enabled" if success else "Failed to enable Wi-Fi"
                else:
                    response = "Wi-Fi control is not available."
            elif "off" in text.lower() or "disable" in text.lower() or "deactivate" in text.lower() or "mati" in text.lower():
                if self.termux_api and self.termux_api.is_available:
                    success = self.termux_api.disable_wifi()
                    response = "Wi-Fi disabled" if success else "Failed to disable Wi-Fi"
                else:
                    response = "Wi-Fi control is not available."
            elif "status" in text.lower() or "info" in text.lower():
                if self.termux_api and self.termux_api.is_available:
                    wifi_info = self.termux_api.get_wifi_info()
                    if wifi_info:
                        ssid = wifi_info.get("ssid", "Unknown")
                        ip = wifi_info.get("ip", "Unknown")
                        response = f"Connected to Wi-Fi network: {ssid}, IP address: {ip}"
                    else:
                        response = "Wi-Fi information not available."
                else:
                    response = "Wi-Fi information is not available."
            else:
                response = "Please specify whether to turn Wi-Fi on, off, or check status."
            
            self.tts.advanced_tts(response)
            return True
        
        # Check for SMS commands
        if "sms" in text.lower() or "text" in text.lower() or "message" in text.lower() or "pesan" in text.lower():
            if "send" in text.lower() or "kirim" in text.lower():
                # Extract phone number and message
                # This is a simplified implementation
                self.tts.advanced_tts("Who would you like to send a message to?")
                recipient = input("Recipient: ")
                
                self.tts.advanced_tts("What message would you like to send?")
                message = input("Message: ")
                
                if self.termux_api and self.termux_api.is_available:
                    success = self.termux_api.send_sms(recipient, message)
                    response = f"Message sent to {recipient}" if success else f"Failed to send message to {recipient}"
                else:
                    response = self.device.send_sms(recipient, message, self.log_activity)
            elif "read" in text.lower() or "list" in text.lower() or "baca" in text.lower():
                if self.termux_api and self.termux_api.is_available:
                    messages = self.termux_api.list_sms(limit=5)
                    if messages:
                        response = "Recent messages:\n"
                        for msg in messages:
                            sender = msg.get("address", "Unknown")
                            body = msg.get("body", "")[:50]
                            response += f"From {sender}: {body}...\n"
                    else:
                        response = "No messages found."
                else:
                    response = self.device.list_sms(filter_unread=True, tts_callback=self.tts.advanced_tts)
            else:
                response = "Please specify whether to send or read SMS messages."
            
            self.tts.advanced_tts(response)
            return True
        
        # Check for call commands
        if "call" in text.lower() or "phone" in text.lower() or "dial" in text.lower() or "telpon" in text.lower():
            # Extract contact name or number
            contact = self.nlp.extract_contact_name(text)
            
            if contact:
                if self.termux_api and self.termux_api.is_available:
                    self.tts.advanced_tts(f"Calling {contact}...")
                    success = self.termux_api.make_call(contact)
                    if not success:
                        self.tts.advanced_tts(f"Failed to call {contact}")
                else:
                    response = self.device.make_call(contact)
                    self.tts.advanced_tts(response)
            else:
                self.tts.advanced_tts("Who would you like to call?")
                contact = input("Contact: ")
                
                if self.termux_api and self.termux_api.is_available:
                    self.tts.advanced_tts(f"Calling {contact}...")
                    success = self.termux_api.make_call(contact)
                    if not success:
                        self.tts.advanced_tts(f"Failed to call {contact}")
                else:
                    response = self.device.make_call(contact)
                    self.tts.advanced_tts(response)
            
            return True
        
        # Check for photo commands
        if "photo" in text.lower() or "picture" in text.lower() or "camera" in text.lower() or "foto" in text.lower():
            if self.termux_api and self.termux_api.is_available:
                self.tts.advanced_tts("Taking a photo...")
                photo_file = self.termux_api.take_photo()
                if photo_file:
                    self.tts.advanced_tts(f"Photo saved as {photo_file}")
                else:
                    self.tts.advanced_tts("Failed to take photo")
            else:
                self.tts.advanced_tts("Camera functionality is not available")
            
            return True
        
        # If no specific command matched, use AI assistant
        if self.openrouter.api_key:
            print("🤖 Processing with AI...")
            
            # Stream response for better user experience
            def handle_stream(chunk):
                print(chunk, end="", flush=True)
            
            self.tts.advanced_tts("Let me think about that...")
            
            # Get AI response
            response = self.ai_assistant.get_response(text)
            
            print(f"\n🤖 {response}")
            self.tts.advanced_tts(response)
            return True
        else:
            # Default response for unrecognized commands
            self.tts.advanced_tts("I'm not sure how to help with that. Could you try a different command?")
            return True
    
    def run(self):
        """Main run loop"""
        print("🎤 Renz Assistant is running. Say a wake word to activate.")
        print("Press Ctrl+C to exit.")
        
        # Check if OpenRouter API key is configured
        if not self.openrouter.api_key:
            print("\n⚠️ OpenRouter API key not configured.")
            print("Some features will be limited. Run configuration to set up API key.")
            print("You can configure by saying 'configure' or 'setup' after activating the assistant.\n")
        
        # Check if continuous listening is enabled
        continuous_listening = self.config.get("voice_recognition.continuous_listening", False)
        
        if continuous_listening:
            print("🎤 Continuous listening mode enabled")
            
            def handle_speech(text):
                if text:
                    print(f"\nHeard: {text}")
                    self.process_command(text)
            
            self.voice_recognition.start_continuous_listening(handle_speech)
        
        while True:
            try:
                if not continuous_listening:
                    # Record audio with wake word detection
                    print("\nListening for command... (Type 'r' to record, 'q' to quit)")
                    user_input = input("> ")
                    
                    if user_input.lower() == 'q':
                        print("Exiting Renz Assistant...")
                        self._cleanup_temp()
                        break
                    
                    if user_input.lower() == 'r':
                        # Use voice recognition
                        text = self.voice_recognition.listen_for_command()
                        if text:
                            print(f"You said: {text}")
                            self.process_command(text)
                    else:
                        # Process text input directly
                        self.process_command(user_input)
                else:
                    # In continuous listening mode, just wait for input to exit
                    user_input = input("\nPress 'q' to quit: ")
                    if user_input.lower() == 'q':
                        print("Exiting Renz Assistant...")
                        self.voice_recognition.stop_continuous_listening()
                        self._cleanup_temp()
                        break
                    
                    # Sleep to prevent CPU usage
                    time.sleep(1)
                
            except KeyboardInterrupt:
                print("\nExiting Renz Assistant...")
                if continuous_listening:
                    self.voice_recognition.stop_continuous_listening()
                self._cleanup_temp()
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                continue

def main():
    """Main entry point"""
    assistant = RenzAssistant()
    assistant.run()

if __name__ == "__main__":
    main()