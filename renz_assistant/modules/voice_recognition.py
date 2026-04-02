"""
Enhanced voice recognition module for Renz Assistant
"""
import os
import time
import json
import re
import asyncio
import subprocess
import tempfile
import threading
from pathlib import Path
from datetime import datetime

class VoiceRecognitionEngine:
    """Base class for voice recognition engines"""
    
    def __init__(self, config=None):
        """Initialize voice recognition engine"""
        self.config = config or {}
        self.language = self.config.get("language", "id")
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.timeout = self.config.get("timeout", 10)
        self.wake_word_sensitivity = self.config.get("wake_word_sensitivity", 0.7)
        self.continuous_listening = self.config.get("continuous_listening", False)
        
        # Create temp directory if it doesn't exist
        self.temp_dir = os.path.join(tempfile.gettempdir(), "renz_assistant")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def record_audio(self, duration=None, output_file=None):
        """Record audio using termux-microphone-record"""
        raise NotImplementedError("Subclasses must implement record_audio")
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file to text"""
        raise NotImplementedError("Subclasses must implement transcribe_audio")
    
    def listen_for_command(self):
        """Listen for a command and return the transcribed text"""
        raise NotImplementedError("Subclasses must implement listen_for_command")
    
    def start_continuous_listening(self, callback):
        """Start continuous listening for commands"""
        raise NotImplementedError("Subclasses must implement start_continuous_listening")
    
    def stop_continuous_listening(self):
        """Stop continuous listening"""
        raise NotImplementedError("Subclasses must implement stop_continuous_listening")
    
    def detect_wake_word(self, audio_file, wake_words):
        """Enhanced wake word detection with better accuracy
        Uses a combination of transcription and phonetic matching
        """
        try:
            # First, transcribe the audio
            text = self.transcribe_audio(audio_file).lower()
            
            # Direct match check
            for wake_word in wake_words:
                if wake_word.lower() in text:
                    print(f"✅ Wake word detected: {wake_word}")
                    return True, wake_word
            
            # If no direct match, try phonetic matching for better accuracy
            # This helps with accents and slight mispronunciations
            for wake_word in wake_words:
                # Calculate word similarity
                similarity = self._calculate_word_similarity(wake_word.lower(), text)
                if similarity > self.wake_word_sensitivity:
                    print(f"✅ Wake word detected (similarity: {similarity:.2f}): {wake_word}")
                    return True, wake_word
            
            return False, None
        
        except Exception as e:
            print(f"Error detecting wake word: {e}")
            return False, None
    
    def _calculate_word_similarity(self, wake_word, transcribed_text):
        """Calculate similarity between wake word and transcribed text"""
        # Simple word similarity calculation
        # For better results, you could use phonetic algorithms like Soundex or Metaphone
        
        # Check if wake word is a phrase
        wake_word_parts = wake_word.split()
        
        if len(wake_word_parts) == 1:
            # Single word wake word
            # Check for partial matches in the transcribed text
            words = transcribed_text.split()
            best_similarity = 0
            
            for word in words:
                similarity = self._string_similarity(wake_word, word)
                best_similarity = max(best_similarity, similarity)
            
            return best_similarity
        else:
            # Multi-word wake word
            # Check for the phrase in the transcribed text
            text_parts = transcribed_text.split()
            
            # Sliding window approach
            max_similarity = 0
            for i in range(len(text_parts) - len(wake_word_parts) + 1):
                window = text_parts[i:i+len(wake_word_parts)]
                window_text = " ".join(window)
                
                similarity = self._string_similarity(wake_word, window_text)
                max_similarity = max(max_similarity, similarity)
            
            return max_similarity
    
    def _string_similarity(self, s1, s2):
        """Calculate string similarity using Levenshtein distance"""
        # Levenshtein distance implementation
        if len(s1) == 0 or len(s2) == 0:
            return 0.0
        
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        
        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2+1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        
        # Convert distance to similarity score (0.0 to 1.0)
        max_len = max(len(s1), len(s2))
        similarity = 1.0 - (distances[-1] / max_len if max_len > 0 else 0)
        return similarity
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            for file in os.listdir(self.temp_dir):
                if file.startswith("renz_audio_") and (file.endswith(".wav") or file.endswith(".opus") or file.endswith(".mp3")):
                    os.remove(os.path.join(self.temp_dir, file))
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")


class TermuxAPIVoiceRecognition(VoiceRecognitionEngine):
    """Enhanced voice recognition using Termux API with improved accuracy"""
    
    def __init__(self, config=None):
        """Initialize Termux API voice recognition"""
        super().__init__(config)
        self._continuous_thread = None
        self._stop_continuous = False
        
        # Enhanced settings
        self.noise_suppression = self.config.get("noise_suppression", True)
        self.auto_gain_control = self.config.get("auto_gain_control", True)
        self.vad_sensitivity = self.config.get("vad_sensitivity", 3)
        self.silence_duration = self.config.get("silence_duration", 1.5)
        
        # Initialize OpenRouter client for fallback transcription
        try:
            from renz_assistant.modules.openrouter import OpenRouterClient
            openrouter_config = self.config.get("openrouter", {})
            self.openrouter_client = OpenRouterClient(
                api_key=openrouter_config.get("api_key", ""),
                default_model=openrouter_config.get("default_model", "openai/gpt-3.5-turbo")
            )
        except ImportError:
            self.openrouter_client = None
            print("⚠️ OpenRouter module not available for fallback transcription")
    
    def record_audio(self, duration=None, output_file=None):
        """Enhanced audio recording with noise suppression and auto gain control"""
        try:
            # Generate output file if not provided
            if output_file is None:
                timestamp = int(time.time() * 1000)
                output_file = os.path.join(self.temp_dir, f"renz_audio_{timestamp}.wav")
            
            # Stop any ongoing recording
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start recording with enhanced options
            cmd = ["termux-microphone-record", "-f", output_file]
            
            # Add duration if specified
            if duration:
                cmd.extend(["-l", str(duration)])
            
            # Add enhanced audio processing options
            if self.noise_suppression:
                cmd.append("-n")  # Enable noise suppression
            
            if self.auto_gain_control:
                cmd.append("-a")  # Enable auto gain control
            
            # Add VAD sensitivity (1-5)
            cmd.extend(["-v", str(self.vad_sensitivity)])
            
            # Add silence duration for auto-stop
            if not duration:  # Only use silence detection if no fixed duration
                cmd.extend(["-s", str(self.silence_duration)])
            
            # Execute the command
            subprocess.run(cmd, check=True)
            
            # Wait for specified duration if provided
            if duration:
                time.sleep(duration)
                # Stop recording
                subprocess.run(
                    ["termux-microphone-record", "-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Verify the file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return output_file
            else:
                print("⚠️ Recording failed or file is empty")
                return None
        
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
    
    def stop_recording(self):
        """Stop ongoing recording"""
        try:
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return False
    
    def transcribe_audio(self, audio_file):
        """Enhanced audio transcription with multiple fallback options"""
        if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
            print("⚠️ Audio file doesn't exist or is empty")
            return ""
        
        # Try multiple transcription methods in order of preference
        transcription = self._transcribe_with_termux_api(audio_file)
        
        # If termux API failed, try OpenRouter
        if not transcription and self.openrouter_client:
            print("ℹ️ Falling back to OpenRouter for transcription")
            transcription = self._transcribe_with_openrouter(audio_file)
        
        # Apply post-processing to improve accuracy
        if transcription:
            transcription = self._post_process_transcription(transcription)
        
        return transcription
    
    def _transcribe_with_termux_api(self, audio_file):
        """Transcribe using Termux API speech-to-text"""
        try:
            # Use termux-speech-to-text with language option
            cmd = ["termux-speech-to-text", "-f", audio_file]
            
            # Add language if specified
            if self.language:
                cmd.extend(["-l", self.language])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Increased timeout for longer audio
            )
            
            # Parse JSON result
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return data.get("text", "")
                except json.JSONDecodeError:
                    return result.stdout.strip()
            else:
                print(f"⚠️ Termux speech-to-text failed: {result.stderr}")
                return ""
        
        except Exception as e:
            print(f"Error with Termux transcription: {e}")
            return ""
    
    def _transcribe_with_openrouter(self, audio_file):
        """Transcribe audio using OpenRouter API (fallback)"""
        if not self.openrouter_client:
            return ""
        
        try:
            # Use OpenRouter's transcription API
            result = self.openrouter_client.transcribe_audio(audio_file)
            
            if "error" in result:
                print(f"⚠️ OpenRouter transcription error: {result['error']}")
                return ""
            
            return result.get("text", "")
        
        except Exception as e:
            print(f"Error with OpenRouter transcription: {e}")
            return ""
    
    def _post_process_transcription(self, text):
        """Apply post-processing to improve transcription accuracy"""
        if not text:
            return ""
        
        # Convert to lowercase for consistency
        text = text.lower()
        
        # Remove common speech recognition artifacts
        artifacts = [
            "um", "uh", "ah", "er", "hmm", "like", "you know", 
            "i mean", "actually", "basically", "literally"
        ]
        
        for artifact in artifacts:
            text = re.sub(r'\b' + artifact + r'\b', '', text)
        
        # Fix common transcription errors based on language
        if self.language == "id":
            # Indonesian-specific corrections
            corrections = {
                "rens": "renz",
                "rans": "renz",
                "ren": "renz",
                "ran": "renz",
                "wrens": "renz"
            }
        else:
            # English-specific corrections
            corrections = {
                "wrens": "renz",
                "ren": "renz",
                "wren": "renz",
                "rens": "renz"
            }
        
        for wrong, correct in corrections.items():
            text = re.sub(r'\b' + wrong + r'\b', correct, text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def listen_for_command(self):
        """Listen for a command and return the transcribed text"""
        try:
            print("🎤 Listening for command...")
            audio_file = self.record_audio(duration=self.timeout)
            
            if not audio_file or not os.path.exists(audio_file):
                print("❌ Failed to record audio")
                return ""
            
            print("🔍 Transcribing audio...")
            text = self.transcribe_audio(audio_file)
            
            # Clean up
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return text
        
        except Exception as e:
            print(f"Error listening for command: {e}")
            return ""
    
    def start_continuous_listening(self, callback):
        """Start continuous listening for commands"""
        if self._continuous_thread and self._continuous_thread.is_alive():
            print("Continuous listening already active")
            return False
        
        self._stop_continuous = False
        self._continuous_thread = threading.Thread(
            target=self._continuous_listening_worker,
            args=(callback,),
            daemon=True
        )
        self._continuous_thread.start()
        return True
    
    def _continuous_listening_worker(self, callback):
        """Enhanced worker thread for continuous listening with wake word detection"""
        print("🎤 Starting continuous listening...")
        
        # Get wake word settings
        wake_word_enabled = self.config.get("wake_word_enabled", True)
        wake_words = self.config.get("wake_words", ["hey renz", "ok renz", "hello renz", "hi renz"])
        
        # Track state
        listening_for_command = False
        command_timeout = 0
        last_activity_time = time.time()
        
        while not self._stop_continuous:
            try:
                current_time = time.time()
                
                # State: Actively listening for a command after wake word
                if listening_for_command:
                    # Check if we've timed out waiting for a command
                    if current_time - last_activity_time > command_timeout:
                        print("⏱️ Command timeout, returning to wake word detection")
                        listening_for_command = False
                        continue
                    
                    # Record audio for command (longer duration)
                    print("👂 Listening for command...")
                    audio_file = self.record_audio(duration=5)
                    
                    if not audio_file or not os.path.exists(audio_file):
                        time.sleep(0.5)
                        continue
                    
                    # Transcribe audio with higher accuracy
                    text = self.transcribe_audio(audio_file)
                    
                    # Clean up
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                    
                    # If we got text, call the callback and reset state
                    if text.strip():
                        print(f"🗣️ Command detected: {text}")
                        callback(text)
                        listening_for_command = False
                    else:
                        # No command detected, keep listening but update timeout
                        last_activity_time = current_time
                
                # State: Listening for wake word
                else:
                    if wake_word_enabled:
                        # Record a short audio segment for wake word detection
                        audio_file = self.record_audio(duration=2)
                        
                        if not audio_file or not os.path.exists(audio_file):
                            time.sleep(0.5)
                            continue
                        
                        # Check for wake word
                        detected, wake_word = self.detect_wake_word(audio_file, wake_words)
                        
                        # Clean up
                        if os.path.exists(audio_file):
                            os.remove(audio_file)
                        
                        if detected:
                            print(f"🔊 Wake word detected: {wake_word}")
                            # Switch to command listening mode
                            listening_for_command = True
                            last_activity_time = time.time()
                            command_timeout = 8  # 8 seconds to give command after wake word
                            
                            # Optional: Play a sound or give feedback that wake word was detected
                            subprocess.run(
                                ["termux-toast", f"Wake word detected: {wake_word}"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            
                            # Optional: Vibrate to indicate wake word detection
                            subprocess.run(
                                ["termux-vibrate", "-d", "100"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                    else:
                        # Wake word detection disabled, record and process all audio
                        audio_file = self.record_audio(duration=3)
                        
                        if not audio_file or not os.path.exists(audio_file):
                            time.sleep(0.5)
                            continue
                        
                        # Transcribe audio
                        text = self.transcribe_audio(audio_file)
                        
                        # Clean up
                        if os.path.exists(audio_file):
                            os.remove(audio_file)
                        
                        # If we got text, call the callback
                        if text.strip():
                            callback(text)
                
                # Small delay to prevent CPU overuse
                time.sleep(0.1)
            
            except Exception as e:
                print(f"Error in continuous listening: {e}")
                time.sleep(1)
    
    def stop_continuous_listening(self):
        """Stop continuous listening"""
        self._stop_continuous = True
        if self._continuous_thread:
            self._continuous_thread.join(timeout=2)
        self.stop_recording()
        return True


class VoskVoiceRecognition(VoiceRecognitionEngine):
    """Voice recognition using Vosk offline speech recognition"""
    
    def __init__(self, config=None):
        """Initialize Vosk voice recognition"""
        super().__init__(config)
        self._continuous_thread = None
        self._stop_continuous = False
        self._model = None
        
        # Try to import Vosk
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            import wave
            
            self.vosk_available = True
            self.wave = wave
            self.KaldiRecognizer = KaldiRecognizer
            
            # Set log level to warnings only
            SetLogLevel(-1)
            
            # Load model
            model_path = self.config.get("vosk_model_path", "model")
            if os.path.exists(model_path):
                self._model = Model(model_path)
                print(f"✅ Vosk model loaded from {model_path}")
            else:
                print(f"⚠️ Vosk model not found at {model_path}")
                self.vosk_available = False
        
        except ImportError:
            print("⚠️ Vosk not installed. Using fallback method.")
            self.vosk_available = False
    
    def record_audio(self, duration=None, output_file=None):
        """Record audio using termux-microphone-record"""
        try:
            # Generate output file if not provided
            if output_file is None:
                timestamp = int(time.time() * 1000)
                output_file = os.path.join(self.temp_dir, f"renz_audio_{timestamp}.wav")
            
            # Stop any ongoing recording
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start recording
            cmd = ["termux-microphone-record", "-f", output_file]
            if duration:
                cmd.extend(["-l", str(duration)])
            
            subprocess.run(cmd, check=True)
            
            # Wait for specified duration if provided
            if duration:
                time.sleep(duration)
                # Stop recording
                subprocess.run(
                    ["termux-microphone-record", "-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            return output_file if os.path.exists(output_file) else None
        
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
    
    def stop_recording(self):
        """Stop ongoing recording"""
        try:
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return False
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file using Vosk"""
        if not self.vosk_available or not self._model:
            # Fallback to Termux API
            return TermuxAPIVoiceRecognition(self.config).transcribe_audio(audio_file)
        
        try:
            # Open the audio file
            wf = self.wave.open(audio_file, "rb")
            
            # Check if the audio format is compatible with Vosk
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                print("Audio file must be WAV format mono PCM.")
                return ""
            
            # Create recognizer
            rec = self.KaldiRecognizer(self._model, wf.getframerate())
            rec.SetWords(True)
            
            # Process audio
            result = ""
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    if "text" in res:
                        result += res["text"] + " "
            
            # Get final result
            final_res = json.loads(rec.FinalResult())
            if "text" in final_res:
                result += final_res["text"]
            
            return result.strip()
        
        except Exception as e:
            print(f"Error transcribing with Vosk: {e}")
            # Fallback to Termux API
            return TermuxAPIVoiceRecognition(self.config).transcribe_audio(audio_file)
    
    def listen_for_command(self):
        """Listen for a command and return the transcribed text"""
        try:
            print("🎤 Listening for command...")
            audio_file = self.record_audio(duration=self.timeout)
            
            if not audio_file or not os.path.exists(audio_file):
                print("❌ Failed to record audio")
                return ""
            
            print("🔍 Transcribing audio...")
            text = self.transcribe_audio(audio_file)
            
            # Clean up
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return text
        
        except Exception as e:
            print(f"Error listening for command: {e}")
            return ""
    
    def start_continuous_listening(self, callback):
        """Start continuous listening for commands"""
        if self._continuous_thread and self._continuous_thread.is_alive():
            print("Continuous listening already active")
            return False
        
        self._stop_continuous = False
        self._continuous_thread = threading.Thread(
            target=self._continuous_listening_worker,
            args=(callback,),
            daemon=True
        )
        self._continuous_thread.start()
        return True
    
    def _continuous_listening_worker(self, callback):
        """Worker thread for continuous listening"""
        print("🎤 Starting continuous listening...")
        
        while not self._stop_continuous:
            try:
                # Record a short audio segment
                audio_file = self.record_audio(duration=3)
                
                if not audio_file or not os.path.exists(audio_file):
                    time.sleep(0.5)
                    continue
                
                # Transcribe audio
                text = self.transcribe_audio(audio_file)
                
                # Clean up
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                
                # If we got text, call the callback
                if text.strip():
                    callback(text)
                
                # Small delay to prevent CPU overuse
                time.sleep(0.2)
            
            except Exception as e:
                print(f"Error in continuous listening: {e}")
                time.sleep(1)
    
    def stop_continuous_listening(self):
        """Stop continuous listening"""
        self._stop_continuous = True
        if self._continuous_thread:
            self._continuous_thread.join(timeout=2)
        self.stop_recording()
        return True


class WhisperVoiceRecognition(VoiceRecognitionEngine):
    """Voice recognition using OpenAI's Whisper model"""
    
    def __init__(self, config=None):
        """Initialize Whisper voice recognition"""
        super().__init__(config)
        self._continuous_thread = None
        self._stop_continuous = False
        self._model = None
        
        # Try to import whisper
        try:
            import whisper
            self.whisper = whisper
            self.whisper_available = True
            
            # Load model
            model_name = self.config.get("whisper_model", "base")
            self._model = whisper.load_model(model_name)
            print(f"✅ Whisper model '{model_name}' loaded")
        
        except ImportError:
            print("⚠️ Whisper not installed. Using fallback method.")
            self.whisper_available = False
    
    def record_audio(self, duration=None, output_file=None):
        """Record audio using termux-microphone-record"""
        try:
            # Generate output file if not provided
            if output_file is None:
                timestamp = int(time.time() * 1000)
                output_file = os.path.join(self.temp_dir, f"renz_audio_{timestamp}.wav")
            
            # Stop any ongoing recording
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start recording
            cmd = ["termux-microphone-record", "-f", output_file]
            if duration:
                cmd.extend(["-l", str(duration)])
            
            subprocess.run(cmd, check=True)
            
            # Wait for specified duration if provided
            if duration:
                time.sleep(duration)
                # Stop recording
                subprocess.run(
                    ["termux-microphone-record", "-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            return output_file if os.path.exists(output_file) else None
        
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
    
    def stop_recording(self):
        """Stop ongoing recording"""
        try:
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return False
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file using Whisper"""
        if not self.whisper_available or not self._model:
            # Fallback to Termux API
            return TermuxAPIVoiceRecognition(self.config).transcribe_audio(audio_file)
        
        try:
            # Transcribe audio
            result = self._model.transcribe(audio_file, language=self.language)
            return result["text"].strip()
        
        except Exception as e:
            print(f"Error transcribing with Whisper: {e}")
            # Fallback to Termux API
            return TermuxAPIVoiceRecognition(self.config).transcribe_audio(audio_file)
    
    def listen_for_command(self):
        """Listen for a command and return the transcribed text"""
        try:
            print("🎤 Listening for command...")
            audio_file = self.record_audio(duration=self.timeout)
            
            if not audio_file or not os.path.exists(audio_file):
                print("❌ Failed to record audio")
                return ""
            
            print("🔍 Transcribing audio...")
            text = self.transcribe_audio(audio_file)
            
            # Clean up
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return text
        
        except Exception as e:
            print(f"Error listening for command: {e}")
            return ""
    
    def start_continuous_listening(self, callback):
        """Start continuous listening for commands"""
        if self._continuous_thread and self._continuous_thread.is_alive():
            print("Continuous listening already active")
            return False
        
        self._stop_continuous = False
        self._continuous_thread = threading.Thread(
            target=self._continuous_listening_worker,
            args=(callback,),
            daemon=True
        )
        self._continuous_thread.start()
        return True
    
    def _continuous_listening_worker(self, callback):
        """Worker thread for continuous listening"""
        print("🎤 Starting continuous listening...")
        
        while not self._stop_continuous:
            try:
                # Record a short audio segment
                audio_file = self.record_audio(duration=3)
                
                if not audio_file or not os.path.exists(audio_file):
                    time.sleep(0.5)
                    continue
                
                # Transcribe audio
                text = self.transcribe_audio(audio_file)
                
                # Clean up
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                
                # If we got text, call the callback
                if text.strip():
                    callback(text)
                
                # Small delay to prevent CPU overuse
                time.sleep(0.2)
            
            except Exception as e:
                print(f"Error in continuous listening: {e}")
                time.sleep(1)
    
    def stop_continuous_listening(self):
        """Stop continuous listening"""
        self._stop_continuous = True
        if self._continuous_thread:
            self._continuous_thread.join(timeout=2)
        self.stop_recording()
        return True


class VoiceRecognitionManager:
    """Manager class for voice recognition engines"""
    
    def __init__(self, config=None):
        """Initialize voice recognition manager"""
        self.config = config or {}
        self.engine_name = self.config.get("engine", "termux_api")
        self.engine = self._create_engine()
    
    def _create_engine(self):
        """Create voice recognition engine based on configuration"""
        if self.engine_name == "vosk":
            return VoskVoiceRecognition(self.config)
        elif self.engine_name == "whisper":
            return WhisperVoiceRecognition(self.config)
        else:
            return TermuxAPIVoiceRecognition(self.config)
    
    def change_engine(self, engine_name):
        """Change voice recognition engine"""
        self.engine_name = engine_name
        self.engine = self._create_engine()
        return True
    
    def record_audio(self, duration=None, output_file=None):
        """Record audio using current engine"""
        return self.engine.record_audio(duration, output_file)
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file using current engine"""
        return self.engine.transcribe_audio(audio_file)
    
    def listen_for_command(self):
        """Listen for a command and return the transcribed text"""
        return self.engine.listen_for_command()
    
    def start_continuous_listening(self, callback):
        """Start continuous listening for commands"""
        return self.engine.start_continuous_listening(callback)
    
    def stop_continuous_listening(self):
        """Stop continuous listening"""
        return self.engine.stop_continuous_listening()
    
    def detect_wake_word(self, audio_file, wake_words):
        """Detect wake word in audio file"""
        return self.engine.detect_wake_word(audio_file, wake_words)
    
    def cleanup(self):
        """Clean up temporary files"""
        return self.engine.cleanup()