"""
Storage and data persistence functions for Renz Assistant
"""
import os
import json
import pickle
from collections import defaultdict
from datetime import datetime

class DataManager:
    """Handles data storage and retrieval for Renz Assistant"""
    
    def __init__(self, base_path="."):
        """Initialize data manager with file paths"""
        self.base_path = base_path
        
        # File paths
        self.memory_file = os.path.join(base_path, "assistant_memory.json")
        self.voice_profile_file = os.path.join(base_path, "voice_profile.pkl")
        self.usage_log_file = os.path.join(base_path, "usage_log.json")
        self.notes_file = os.path.join(base_path, "notes.json")
        self.reminders_file = os.path.join(base_path, "reminders.json")
        self.user_preferences_file = os.path.join(base_path, "user_preferences.json")
        self.learning_file = os.path.join(base_path, "learning_data.json")
        self.personality_file = os.path.join(base_path, "personality_profiles.json")
    
    def load_memory(self):
        """Load conversation memory with enhanced structure"""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "conversations": [],
            "facts": {},
            "preferences": {},
            "learned_patterns": {},
            "user_context": {},
            "emotional_state_history": [],
        }

    def save_memory(self, memory):
        """Save conversation memory"""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    def load_voice_profile(self):
        """Load voice authentication profile"""
        if os.path.exists(self.voice_profile_file):
            with open(self.voice_profile_file, "rb") as f:
                return pickle.load(f)
        return None

    def save_voice_profile(self, profile):
        """Save voice authentication profile"""
        with open(self.voice_profile_file, "wb") as f:
            pickle.dump(profile, f)

    def load_usage_log(self):
        """Load usage statistics"""
        if os.path.exists(self.usage_log_file):
            with open(self.usage_log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert back to defaultdict
                result = {
                    "app_usage": defaultdict(int),
                    "command_usage": defaultdict(int),
                    "daily_stats": defaultdict(dict),
                    "time_patterns": defaultdict(list),
                    "frequency_analysis": defaultdict(int),
                }
                # Copy data from loaded file
                for key, value in data.items():
                    if key in result:
                        if isinstance(result[key], defaultdict):
                            result[key].update(value)
                        else:
                            result[key] = value
                return result
        return {
            "app_usage": defaultdict(int),
            "command_usage": defaultdict(int),
            "daily_stats": defaultdict(dict),
            "time_patterns": defaultdict(list),
            "frequency_analysis": defaultdict(int),
        }

    def save_usage_log(self, usage_log):
        """Save usage statistics"""
        with open(self.usage_log_file, "w", encoding="utf-8") as f:
            json.dump(dict(usage_log), f, ensure_ascii=False, indent=2)

    def load_notes(self):
        """Load notes"""
        if os.path.exists(self.notes_file):
            with open(self.notes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_notes(self, notes):
        """Save notes"""
        with open(self.notes_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)

    def load_reminders(self):
        """Load reminders"""
        if os.path.exists(self.reminders_file):
            with open(self.reminders_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_reminders(self, reminders):
        """Save reminders"""
        with open(self.reminders_file, "w", encoding="utf-8") as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)

    def load_user_preferences(self):
        """Load user preferences"""
        if os.path.exists(self.user_preferences_file):
            with open(self.user_preferences_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "personality": "friendly",
            "tts_speed": 1.0,
            "volume": 70,
            "language_preference": "id",
            "auto_suggestions": True,
            "learning_mode": True,
        }

    def save_user_preferences(self, user_preferences):
        """Save user preferences"""
        with open(self.user_preferences_file, "w", encoding="utf-8") as f:
            json.dump(user_preferences, f, ensure_ascii=False, indent=2)

    def load_learning_data(self):
        """Load learning and adaptation data"""
        if os.path.exists(self.learning_file):
            with open(self.learning_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "user_patterns": {},
            "adaptive_responses": {},
            "learning_progress": {},
            "contextual_understanding": {},
        }

    def save_learning_data(self, learning_data):
        """Save learning data"""
        with open(self.learning_file, "w", encoding="utf-8") as f:
            json.dump(learning_data, f, ensure_ascii=False, indent=2)

    def load_personality_profiles(self):
        """Load personality profiles"""
        if os.path.exists(self.personality_file):
            with open(self.personality_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "friendly": {
                "greeting": "Hello! How can I help you today?",
                "response_style": "warm and conversational",
                "tts_speed": 1.0,
            },
            "funny": {
                "greeting": "Hey there! Ready for some fun? 😄",
                "response_style": "humorous and entertaining",
                "tts_speed": 1.2,
            },
            "serious": {
                "greeting": "Good day. How may I assist you?",
                "response_style": "professional and direct",
                "tts_speed": 0.9,
            },
            "teacher": {
                "greeting": "Hello, student! What would you like to learn today?",
                "response_style": "educational and encouraging",
                "tts_speed": 0.8,
            },
            "calm": {
                "greeting": "Peace and tranquility. How can I help?",
                "response_style": "soothing and peaceful",
                "tts_speed": 0.7,
            },
        }
    
    def save_personality_profiles(self, personality_profiles):
        """Save personality profiles"""
        with open(self.personality_file, "w", encoding="utf-8") as f:
            json.dump(personality_profiles, f, ensure_ascii=False, indent=2)
    
    def log_activity(self, activity_type, details=None, usage_log=None):
        """Log user activity for analysis"""
        if usage_log is None:
            usage_log = self.load_usage_log()
        
        timestamp = datetime.now().isoformat()
        day_key = datetime.now().strftime("%Y-%m-%d")
        hour = datetime.now().hour
        
        # Update usage statistics
        if activity_type == "app_open":
            app_name = details
            usage_log["app_usage"][app_name] = usage_log["app_usage"].get(app_name, 0) + 1
        elif activity_type == "command":
            cmd = details
            usage_log["command_usage"][cmd] = usage_log["command_usage"].get(cmd, 0) + 1
        
        # Update daily stats
        if day_key not in usage_log["daily_stats"]:
            usage_log["daily_stats"][day_key] = {"activities": []}
        
        usage_log["daily_stats"][day_key]["activities"].append({
            "type": activity_type,
            "details": details,
            "timestamp": timestamp,
            "hour": hour
        })
        
        # Update time patterns
        usage_log["time_patterns"][str(hour)].append(activity_type)
        
        # Save updated log
        self.save_usage_log(usage_log)
        
        return usage_log