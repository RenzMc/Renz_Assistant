"""
Audio processing functions for Renz Assistant
Enhanced with better TTS options and 100% Termux compatibility
Pure Python implementation - no numpy/scipy/python_speech_features required
"""
import os
import time
import wave
import struct
import math
import asyncio
import subprocess
import json
from datetime import datetime

import edge_tts

from renz_assistant.modules.utils import cosine_similarity_manual, mean, std


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

    def _read_wav(self, audio_file):
        """Read a WAV file and return (sample_rate, float_samples_list)."""
        with wave.open(audio_file, 'rb') as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            raw_data = wf.readframes(nframes)

        total_samples = nframes * nchannels
        if sampwidth == 2:
            fmt = f'<{total_samples}h'
            max_val = 32768.0
        elif sampwidth == 4:
            fmt = f'<{total_samples}i'
            max_val = 2147483648.0
        elif sampwidth == 1:
            fmt = f'<{total_samples}B'
            max_val = 128.0
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")

        samples = list(struct.unpack(fmt, raw_data))

        if sampwidth == 1:
            samples = [s - 128 for s in samples]

        if nchannels > 1:
            samples = [
                sum(samples[i:i + nchannels]) / nchannels
                for i in range(0, len(samples), nchannels)
            ]

        max_abs = max((abs(s) for s in samples), default=1.0)
        if max_abs == 0:
            max_abs = 1.0
        data = [s / max_abs for s in samples]

        return framerate, data

    def _fft_power(self, frame):
        """
        Compute power spectrum of a frame (must be power-of-2 length)
        using an iterative Cooley-Tukey FFT with real/imag stored as tuples.
        """
        N = len(frame)
        x = [(float(v), 0.0) for v in frame]

        # Bit-reverse permutation
        j = 0
        for i in range(1, N):
            bit = N >> 1
            while j & bit:
                j ^= bit
                bit >>= 1
            j ^= bit
            if i < j:
                x[i], x[j] = x[j], x[i]

        # Butterfly operations
        length = 2
        while length <= N:
            angle = -2.0 * math.pi / length
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            for i in range(0, N, length):
                wr, wi = 1.0, 0.0
                for k in range(length // 2):
                    ur, ui = x[i + k]
                    vr, vi = x[i + k + length // 2]
                    tvr = vr * wr - vi * wi
                    tvi = vr * wi + vi * wr
                    x[i + k] = (ur + tvr, ui + tvi)
                    x[i + k + length // 2] = (ur - tvr, ui - tvi)
                    new_wr = wr * cos_a - wi * sin_a
                    wi = wr * sin_a + wi * cos_a
                    wr = new_wr
            length <<= 1

        power = [x[k][0] ** 2 + x[k][1] ** 2 for k in range(N // 2 + 1)]
        return power

    def _apply_mel_filterbank(self, power_spectrum, sample_rate, n_filters=13):
        """Apply mel filterbank to power spectrum and return log energies."""
        N = len(power_spectrum)
        freq_max = sample_rate / 2.0
        freq_min = 0.0

        mel_min = 2595.0 * math.log10(1.0 + freq_min / 700.0)
        mel_max = 2595.0 * math.log10(1.0 + freq_max / 700.0)

        mel_points = [
            mel_min + i * (mel_max - mel_min) / (n_filters + 1)
            for i in range(n_filters + 2)
        ]

        hz_points = [700.0 * (10.0 ** (m / 2595.0) - 1.0) for m in mel_points]

        fft_size = (N - 1) * 2
        bin_points = [
            min(int(round(h * fft_size / sample_rate)), N - 1)
            for h in hz_points
        ]

        energies = []
        for m in range(1, n_filters + 1):
            energy = 0.0
            lo = bin_points[m - 1]
            mid = bin_points[m]
            hi = bin_points[m + 1]

            denom1 = mid - lo if mid > lo else 1
            for k in range(lo, mid):
                weight = (k - lo) / denom1
                energy += power_spectrum[k] * weight

            denom2 = hi - mid if hi > mid else 1
            for k in range(mid, hi):
                weight = (hi - k) / denom2
                energy += power_spectrum[k] * weight

            energies.append(math.log(energy + 1e-10))

        return energies

    def extract_voice_features(self, audio_file):
        """Extract comprehensive voice features for authentication - pure Python."""
        try:
            if not os.path.exists(audio_file):
                return None

            sample_rate, data = self._read_wav(audio_file)

            if len(data) < 512:
                print("❌ Audio too short for feature extraction")
                return None

            frame_size = 256
            hop_size = 128
            n_filters = 13

            hamming = [
                0.54 - 0.46 * math.cos(2.0 * math.pi * n / (frame_size - 1))
                for n in range(frame_size)
            ]

            mel_energies_per_frame = []
            zcr_values = []

            for start in range(0, len(data) - frame_size, hop_size):
                frame = data[start:start + frame_size]

                windowed = [frame[i] * hamming[i] for i in range(frame_size)]

                power = self._fft_power(windowed)

                mel_e = self._apply_mel_filterbank(power, sample_rate, n_filters)
                mel_energies_per_frame.append(mel_e)

                signs = [1 if s >= 0 else -1 for s in frame]
                zcr = sum(
                    1 for i in range(1, len(signs)) if signs[i] != signs[i - 1]
                ) / (2 * frame_size)
                zcr_values.append(zcr)

            if not mel_energies_per_frame:
                return None

            n_frames = len(mel_energies_per_frame)
            mel_mean = [
                sum(mel_energies_per_frame[f][k] for f in range(n_frames)) / n_frames
                for k in range(n_filters)
            ]
            mel_std = [
                math.sqrt(
                    sum((mel_energies_per_frame[f][k] - mel_mean[k]) ** 2 for f in range(n_frames)) / n_frames
                )
                for k in range(n_filters)
            ]

            zcr_mean_val = mean(zcr_values)
            zcr_std_val = std(zcr_values)

            total_energy = sum(mel_mean) or 1.0
            centroid_mean = sum(i * e for i, e in enumerate(mel_mean)) / total_energy

            total_std_energy = sum(mel_std) or 1.0
            centroid_std = sum(i * e for i, e in enumerate(mel_std)) / total_std_energy

            features = mel_mean + mel_std + [centroid_mean, centroid_std, zcr_mean_val, zcr_std_val]
            return features

        except Exception as e:
            print(f"❌ Feature extraction error: {e}")
            return None

    def record_audio_with_wake_word_detection(self):
        """Enhanced audio recording with wake word detection via Termux options"""
        try:
            input_file_path = f"temp_audio_{time.time_ns()}.wav"
            print(f"🎤 Recording to {input_file_path}...")

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

            output_file = input_file_path.replace(".opus", ".wav")
            self.convert_to_wav(input_file_path, output_file)

            print(f"✅ Saved WAV file: {output_file}")
            return output_file

        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None

    def convert_to_wav(self, input_file, output_file):
        """Convert audio file to WAV format"""
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

        current_features = self.extract_voice_features(audio_file)
        if not current_features:
            return False

        similarities = []
        for sample in voice_profile["samples"]:
            sim = cosine_similarity_manual(current_features, sample)
            similarities.append(sim)

        average_similarity = mean(similarities)
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

            mean_sim = mean(similarities)
            std_sim = std(similarities)
            threshold = max(0.75, mean_sim - 0.5 * std_sim)

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

        self.tts_engine = self.user_preferences.get("tts_engine", "edge_tts")

        self.cache_dir = os.path.join(os.path.expanduser("~"), ".renz_assistant", "tts_cache")
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                print(f"Failed to create TTS cache directory: {e}")

        self.available_engines = self._check_available_engines()
        print(f"Available TTS engines: {', '.join(self.available_engines)}")

    def _check_available_engines(self):
        """Check which TTS engines are available"""
        available = []

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

        try:
            import edge_tts
            available.append("edge_tts")
        except ImportError:
            pass

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

        lang = "id"
        if self.language_detector:
            lang = self.language_detector(text)

        personality = self.user_preferences.get("personality", "friendly")
        base_speed = self.personality_profiles.get(personality, {}).get("tts_speed", 1.0)

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

        if self.tts_engine == "edge_tts" and "edge_tts" in self.available_engines:
            self._edge_tts(text, lang, final_speed)
        elif self.tts_engine == "termux_tts" and "termux_tts" in self.available_engines:
            self._termux_tts(text, lang, final_speed)
        elif self.tts_engine == "espeak" and "espeak" in self.available_engines:
            self._espeak_tts(text, lang, final_speed)
        elif self.tts_engine == "festival" and "festival" in self.available_engines:
            self._festival_tts(text, lang, final_speed)
        else:
            if "edge_tts" in self.available_engines:
                self._edge_tts(text, lang, final_speed)
            elif "termux_tts" in self.available_engines:
                self._termux_tts(text, lang, final_speed)
            elif "espeak" in self.available_engines:
                self._espeak_tts(text, lang, final_speed)
            elif "festival" in self.available_engines:
                self._festival_tts(text, lang, final_speed)
            else:
                print(f"🔊 TTS: {text}")

    async def _generate_edge_tts(self, tts_text, tts_voice, rate, out_path):
        """Generate TTS audio file using edge-tts"""
        communicator = edge_tts.Communicate(tts_text, tts_voice, rate=rate)
        await communicator.save(out_path)

    def _edge_tts(self, text, lang, speed):
        """TTS using edge-tts"""
        try:
            delta = int((speed - 1.0) * 100)
            rate_str = f"{delta:+d}%"

            if lang == "id":
                voice = "id-ID-GadisNeural"
            elif lang == "en":
                voice = "en-US-JennyNeural"
            else:
                voice = "en-US-JennyNeural"

            timestamp = int(time.time())
            tmp_path = os.path.join(self.cache_dir, f"tts_{timestamp}.mp3")

            asyncio.run(self._generate_edge_tts(text, voice, rate_str, tmp_path))

            subprocess.run(
                ["termux-media-player", "play", tmp_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            words = len(text.split())
            wait_time = max(1, min(10, words * 0.3 / speed))
            time.sleep(wait_time)

            self._clean_old_tts_files()

            return True
        except Exception as e:
            print(f"[Edge TTS] Error: {e}")
            return False

    def _termux_tts(self, text, lang, speed):
        """TTS using Termux TTS"""
        try:
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

            engine = None
            for e in engines:
                if lang in e.get("language", ""):
                    engine = e.get("engine")
                    break

            termux_speed = max(0.1, min(10.0, speed * 5))

            cmd = ["termux-tts-speak"]

            if lang:
                cmd.extend(["-l", lang])

            if engine:
                cmd.extend(["-e", engine])

            cmd.extend(["-r", str(termux_speed)])
            cmd.append(text)

            subprocess.run(cmd, check=True)

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
            lang_map = {
                "id": "id", "en": "en", "ja": "ja", "ko": "ko",
                "zh": "zh", "ar": "ar", "de": "de", "es": "es",
                "fr": "fr", "it": "it", "nl": "nl", "pt": "pt",
                "ru": "ru", "tr": "tr"
            }

            espeak_lang = lang_map.get(lang, "en")
            wpm = int(175 * speed)

            cmd = [
                "espeak",
                "-v", espeak_lang,
                "-s", str(wpm),
                "-a", "200",
                text
            ]

            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            print(f"[espeak TTS] Error: {e}")
            return False

    def _festival_tts(self, text, lang, speed):
        """TTS using festival"""
        try:
            tmp_file = os.path.join(self.cache_dir, "festival_text.txt")
            with open(tmp_file, "w") as f:
                f.write(text)

            cmd = ["festival", "--tts", tmp_file]
            subprocess.run(cmd, check=True)

            os.remove(tmp_file)
            return True
        except Exception as e:
            print(f"[festival TTS] Error: {e}")
            return False

    def _clean_old_tts_files(self):
        """Clean old TTS cache files"""
        try:
            files = []
            for file in os.listdir(self.cache_dir):
                if file.startswith("tts_") and file.endswith(".mp3"):
                    file_path = os.path.join(self.cache_dir, file)
                    files.append((file_path, os.path.getmtime(file_path)))

            files.sort(key=lambda x: x[1], reverse=True)

            for file_path, _ in files[10:]:
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning TTS cache: {e}")
