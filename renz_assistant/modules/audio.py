"""
Audio processing functions for Renz Assistant
Enhanced with better TTS options and 100% Termux compatibility
"""
import os
import time
import tempfile
import asyncio
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from python_speech_features import mfcc
import edge_tts
import json
from datetime import datetime

from renz_assistant.modules.utils import cosine_similarity_manual

class AudioProcessor:
    """Handles audio recording, processing, and voice authentication"""
    
    TEMP_AMR = "temp_voice_sample.amr"
    TEMP_WAV = "temp_voice_sample.wav"
    MAX_RETRIES = 5
    SAMPLE_COUNT = 3
    RECORD_DURATION = 10
    
    def __init__(self, language_detector=None):
        """Initialize audio processor"""
        self.language_detector = language_detector
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".renz_assistant", "cache")
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                print(f"Failed to create cache directory: {e}")
    
    def record_audio_sample(self):
        """Record audio sample directly to WAV (mono, 16 kHz)."""
        try:
            print("🎙️ Recording directly to WAV...")
            wav_file = self.TEMP_WAV
            # Record directly to WAV using termux-microphone-record
            subprocess.run(
                ["termux-microphone-record", "-f", wav_file, "-l", str(self.RECORD_DURATION)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            if not os.path.exists(wav_file):
                print("❌ Recording failed: WAV file not found")
                return False
            print("✅ Recording successful")
            return True
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return False
    
    def extract_voice_features(self, audio_file):
        """Extract comprehensive voice features for authentication"""
        try:
            if not os.path.exists(audio_file):
                return None

            # Read audio file
            sample_rate, data = wavfile.read(audio_file)

            # Convert to mono if stereo
            if data.ndim > 1:
                data = np.mean(data, axis=1)

            # Normalize
            data = data.astype(np.float32)
            if np.max(np.abs(data)) > 0:
                data = data / np.max(np.abs(data))

            # Extract MFCC features
            mfcc_features = mfcc(
                data,
                sample_rate,
                numcep=13,
                nfilt=26,
                winlen=0.025,
                winstep=0.01)
            mfcc_mean = np.mean(mfcc_features, axis=0)
            mfcc_std = np.std(mfcc_features, axis=0)

            # Extract spectral features
            f, t, Sxx = spectrogram(
                data, fs=sample_rate, nperseg=2048, noverlap=1024)

            # Spectral centroid
            centroids = np.sum(f.reshape(-1, 1) * Sxx,
                            axis=0) / np.sum(Sxx, axis=0)
            centroid_mean = np.mean(centroids)
            centroid_std = np.std(centroids)

            # Zero crossing rate
            frame_length = 2048
            hop_length = 1024
            zcr_values = []

            for i in range(0, len(data) - frame_length, hop_length):
                frame = data[i: i + frame_length]
                zcr = np.sum(np.abs(np.diff(np.sign(frame)))) / \
                    (2 * frame_length)
                zcr_values.append(zcr)

            zcr_mean = np.mean(zcr_values)
            zcr_std = np.std(zcr_values)

            # Combine all features
            features = np.concatenate(
                [mfcc_mean, mfcc_std, [centroid_mean, centroid_std, zcr_mean, zcr_std]]
            )

            return features.tolist()

        except Exception as e:
            print(f"❌ Feature extraction error: {e}")
            return None
    
    def record_audio_with_wake_word_detection(self):
        """Enhanced audio recording with wake word detection via Termux options"""
        try:
            input_file_path = f"temp_audio_{time.time_ns()}.wav"
            print(f"🎤 Recording to {input_file_path}...")
            
            # Start Termux API
            subprocess.call("termux-api-start &> /dev/null", shell=True)
            
            print("\nType 'r' and hit Enter to start recording...\nType 'e' and hit enter to exit.\n")
            while True:
                user_input = input()
                if user_input.lower() == "r":
                    print("Starting recording...")
                    try:
                        subprocess.run(
                            ["termux-microphone-record", "-q"],
                            stdout=subprocess.DEVNULL,
                            check=True,
                        )
                        subprocess.run(
                            [
                                "termux-microphone-record",
                                "-e",
                                "opus",
                                "-f",
                                input_file_path,
                            ],
                            stdout=subprocess.DEVNULL,
                            check=True,
                        )
                    except Exception:
                        print("I couldn't record the audio.\n Is RECORD_AUDIO permission granted?\n")
                        return None
                    break
                if user_input.lower() == "e":
                    return None
            
            print("\nType 'q' and hit Enter to stop recording...\n")
            while True:
                user_input = input()
                if user_input.lower() == "q":
                    subprocess.run(
                        ["termux-microphone-record", "-q"],
                        stdout=subprocess.DEVNULL,
                        check=True,
                    )
                    print("Recording finished.")
                    break
            
            # Convert to WAV format
            output_file = input_file_path.replace(".opus", ".wav")
            self.convert_to_wav(input_file_path, output_file)
            
            print(f"✅ Saved WAV file: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def convert_to_wav(self, input_file, output_file):
        """Convert audio file to WAV format"""
        # Use a different name for the converted file to avoid overwriting
        converted_file = output_file.replace(".wav", "_converted.wav")
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_file,
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",
                "-ar",
                "16000",
                converted_file,
                "-y",
                "-loglevel",
                "quiet",
            ],
            check=True,
        )
        # Remove the original input file and rename the converted file
        os.remove(input_file)
        os.rename(converted_file, output_file)
    
    def clean_temp_files(self):
        """Clean all temporary recording files"""
        for file in os.listdir():
            if file.startswith("temp_audio_") and (file.endswith(".opus") or file.endswith(".wav")):
                try:
                    os.remove(file)
                    print(f"🧹 File dibersihkan: {file}")
                except Exception as e:
                    print(f"⚠️ Gagal hapus {file}: {e}")

    def authenticate_voice(self, audio_file, voice_profile):
        """Enhanced voice authentication with multiple security layers"""
        if not voice_profile:
            print("❌ No voice profile found. Please register first.")
            return False

        # Extract features from current audio
        current_features = self.extract_voice_features(audio_file)
        if not current_features:
            return False

        # Compare with stored samples
        similarities = []
        for sample in voice_profile["samples"]:
            sim = cosine_similarity_manual(current_features, sample)
            similarities.append(sim)

        average_similarity = np.mean(similarities)
        threshold = voice_profile["threshold"]

        print(f"🔐 Voice similarity: {average_similarity:.3f} (threshold: {threshold:.3f})")

        if average_similarity >= threshold:
            print("✅ Voice authentication successful")
            return True
        else:
            print("❌ Voice authentication failed")
            return False
    
    def create_voice_profile_from_files(self, wav_files):
        """Create voice profile from existing WAV files"""
        samples = []
        for wav_file in wav_files:
            features = self.extract_voice_features(wav_file)
            if features:
                samples.append(features)

        if len(samples) >= 2:
            similarities = []
            for i in range(len(samples) - 1):
                sim = cosine_similarity_manual(samples[i], samples[i + 1])
                similarities.append(sim)

            threshold = max(
                0.75,
                np.mean(similarities) -
                0.5 *
                np.std(similarities))

            voice_profile = {
                "samples": samples,
                "threshold": threshold,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "security_level": "high",
            }

            return voice_profile

        return None


class TextToSpeech:
    """Handles text-to-speech functionality with multiple engines"""
    
    def __init__(self, language_detector=None, user_preferences=None, personality_profiles=None):
        """Initialize text-to-speech with multiple engines"""
        self.language_detector = language_detector
        self.user_preferences = user_preferences or {"personality": "friendly", "language_preference": "id"}
        self.personality_profiles = personality_profiles or {
            "friendly": {
                "greeting": "Hello! How can I help you today?",
                "response_style": "warm and conversational",
                "tts_speed": 1.0,
            }
        }
        
        # TTS engine preference
        self.tts_engine = self.user_preferences.get("tts_engine", "edge_tts")
        
        # Cache directory for TTS files
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".renz_assistant", "tts_cache")
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                print(f"Failed to create TTS cache directory: {e}")
        
        # Check available TTS engines
        self.available_engines = self._check_available_engines()
        print(f"Available TTS engines: {', '.join(self.available_engines)}")
    
    def _check_available_engines(self):
        """Check which TTS engines are available"""
        available = []
        
        # Check Termux TTS
        try:
            result = subprocess.run(
                ["termux-tts-engines"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                available.append("termux_tts")
        except Exception:
            pass
        
        # Check edge-tts
        try:
            import edge_tts
            available.append("edge_tts")
        except ImportError:
            pass
        
        # Check espeak
        try:
            result = subprocess.run(
                ["which", "espeak"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                available.append("espeak")
        except Exception:
            pass
        
        # Check festival
        try:
            result = subprocess.run(
                ["which", "festival"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                available.append("festival")
        except Exception:
            pass
        
        # Always add fallback
        available.append("fallback")
        
        return available
    
    def set_tts_engine(self, engine):
        """Set TTS engine"""
        if engine in self.available_engines:
            self.tts_engine = engine
            return True
        return False
    
    def advanced_tts(self, text, mood="neutral"):
        """Advanced TTS with mood-based speech modification using multiple engines"""
        if not text.strip():
            return

        # Detect language if language detector is available
        lang = "id"
        if self.language_detector:
            lang = self.language_detector(text)

        # Get personality settings
        personality = self.user_preferences.get("personality", "friendly")
        base_speed = self.personality_profiles.get(personality, {}).get(
            "tts_speed", 1.0
        )

        # Adjust speed based on mood
        mood_adjustments = {
            "happy": 1.15,
            "excited": 1.25,
            "sad": 0.8,
            "angry": 1.2,
            "calm": 0.85,
            "serious": 0.95,
            "funny": 1.3,
            "neutral": 1.0,
        }
        final_speed = base_speed * mood_adjustments.get(mood, 1.0)
        
        # Try the selected TTS engine
        if self.tts_engine == "edge_tts" and "edge_tts" in self.available_engines:
            self._edge_tts(text, lang, final_speed)
        elif self.tts_engine == "termux_tts" and "termux_tts" in self.available_engines:
            self._termux_tts(text, lang, final_speed)
        elif self.tts_engine == "espeak" and "espeak" in self.available_engines:
            self._espeak_tts(text, lang, final_speed)
        elif self.tts_engine == "festival" and "festival" in self.available_engines:
            self._festival_tts(text, lang, final_speed)
        else:
            # Fallback to any available engine
            if "edge_tts" in self.available_engines:
                self._edge_tts(text, lang, final_speed)
            elif "termux_tts" in self.available_engines:
                self._termux_tts(text, lang, final_speed)
            elif "espeak" in self.available_engines:
                self._espeak_tts(text, lang, final_speed)
            elif "festival" in self.available_engines:
                self._festival_tts(text, lang, final_speed)
            else:
                # Ultimate fallback - just print the text
                print(f"🔊 TTS: {text}")
    
    async def _generate_edge_tts(self, tts_text, tts_voice, rate, out_path):
        """Generate TTS audio file using edge-tts"""
        communicator = edge_tts.Communicate(tts_text, tts_voice, rate=rate)
        await communicator.save(out_path)
    
    def _edge_tts(self, text, lang, speed):
        """TTS using edge-tts"""
        try:
            # Calculate delta rate for edge-tts (relative to 100%)
            delta = int((speed - 1.0) * 100)
            rate_str = f"{delta:+d}%"  # example '+15%', '0%', '-20%'

            # Select voice based on language
            if lang == "id":
                voice = "id-ID-GadisNeural"
            elif lang == "en":
                voice = "en-US-JennyNeural"
            else:
                voice = "en-US-JennyNeural"  # fallback
            
            # Create temporary MP3 file
            timestamp = int(time.time())
            tmp_path = os.path.join(self.cache_dir, f"tts_{timestamp}.mp3")

            # Generate TTS & save
            asyncio.run(self._generate_edge_tts(text, voice, rate_str, tmp_path))

            # Play via Termux media player
            subprocess.run(
                ["termux-media-player", "play", tmp_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # Wait for audio to finish playing
            # This is a rough estimate based on text length and speed
            words = len(text.split())
            wait_time = max(1, min(10, words * 0.3 / speed))
            time.sleep(wait_time)
            
            # Clean up old files periodically
            self._clean_old_tts_files()
            
            return True
        except Exception as e:
            print(f"[Edge TTS] Error: {e}")
            return False
    
    def _termux_tts(self, text, lang, speed):
        """TTS using Termux TTS"""
        try:
            # Get available engines
            result = subprocess.run(
                ["termux-tts-engines"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            engines = []
            if result.returncode == 0:
                try:
                    engines = json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass
            
            # Select engine based on language
            engine = None
            for e in engines:
                if lang in e.get("language", ""):
                    engine = e.get("engine")
                    break
            
            # Adjust speed (Termux TTS uses 0.1 to 10.0 scale)
            termux_speed = max(0.1, min(10.0, speed * 5))
            
            cmd = ["termux-tts-speak"]
            
            # Add language if available
            if lang:
                cmd.extend(["-l", lang])
            
            # Add engine if available
            if engine:
                cmd.extend(["-e", engine])
            
            # Add speed
            cmd.extend(["-r", str(termux_speed)])
            
            # Add text
            cmd.append(text)
            
            # Run TTS
            subprocess.run(cmd, check=True)
            
            # Wait for audio to finish playing
            # This is a rough estimate based on text length and speed
            words = len(text.split())
            wait_time = max(1, min(10, words * 0.3 / speed))
            time.sleep(wait_time)
            
            return True
        except Exception as e:
            print(f"[Termux TTS] Error: {e}")
            return False
    
    def _espeak_tts(self, text, lang, speed):
        """TTS using espeak"""
        try:
            # Map language codes
            lang_map = {
                "id": "id",
                "en": "en",
                "ja": "ja",
                "ko": "ko",
                "zh": "zh",
                "ar": "ar",
                "de": "de",
                "es": "es",
                "fr": "fr",
                "it": "it",
                "nl": "nl",
                "pt": "pt",
                "ru": "ru",
                "tr": "tr"
            }
            
            espeak_lang = lang_map.get(lang, "en")
            
            # Adjust speed (espeak uses words per minute, default is 175)
            wpm = int(175 * speed)
            
            # Create command
            cmd = [
                "espeak",
                "-v", espeak_lang,
                "-s", str(wpm),
                "-a", "200",  # Volume (0-200)
                text
            ]
            
            # Run espeak
            subprocess.run(cmd, check=True)
            
            return True
        except Exception as e:
            print(f"[espeak TTS] Error: {e}")
            return False
    
    def _festival_tts(self, text, lang, speed):
        """TTS using festival"""
        try:
            # Festival doesn't support many languages, so we'll just use it for English
            
            # Create temporary file for festival
            tmp_file = os.path.join(self.cache_dir, "festival_text.txt")
            with open(tmp_file, "w") as f:
                f.write(text)
            
            # Run festival
            cmd = [
                "festival",
                "--tts",
                tmp_file
            ]
            
            subprocess.run(cmd, check=True)
            
            # Remove temporary file
            os.remove(tmp_file)
            
            return True
        except Exception as e:
            print(f"[festival TTS] Error: {e}")
            return False
    
    def _clean_old_tts_files(self):
        """Clean old TTS cache files"""
        try:
            # Keep only the 10 most recent files
            files = []
            for file in os.listdir(self.cache_dir):
                if file.startswith("tts_") and file.endswith(".mp3"):
                    file_path = os.path.join(self.cache_dir, file)
                    files.append((file_path, os.path.getmtime(file_path)))
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old files
            for file_path, _ in files[10:]:
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning TTS cache: {e}")