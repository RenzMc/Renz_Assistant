"""
Background services for Renz Assistant
"""
import time
import json
import threading
from datetime import datetime

class BackgroundServices:
    """Manages background services for Renz Assistant"""
    
    def __init__(self, assistant=None):
        """Initialize background services with reference to main assistant"""
        self.assistant = assistant
    
    def start_all_services(self):
        """Start all background services as daemon threads"""
        if not self.assistant:
            print("⚠️ Cannot start services: No assistant reference")
            return False
            
        threading.Thread(target=self.reminder_service, daemon=True).start()
        threading.Thread(target=self.notification_service, daemon=True).start()
        threading.Thread(target=self.idle_timeout_service, daemon=True).start()
        threading.Thread(target=self.learning_service, daemon=True).start()
        
        print("✅ Background services started")
        return True
    
    def reminder_service(self):
        """Enhanced reminder service with multiple types"""
        while True:
            try:
                if not self.assistant:
                    time.sleep(60)
                    continue
                    
                current_time = datetime.now()

                for reminder in self.assistant.reminders:
                    if reminder.get("executed", False):
                        continue

                    reminder_time = datetime.fromisoformat(reminder["time"])

                    if current_time >= reminder_time:
                        if reminder["type"] == "sound":
                            # Increase volume for alarms
                            self.assistant.control_volume("music", 90)
                            self.assistant.play_sound_file(reminder["sound_file"], reminder.get("duration", 30))
                        elif reminder["type"] == "tts":
                            self.assistant.tts.advanced_tts(reminder["message"], "serious")

                        reminder["executed"] = True
                        self.assistant.data_manager.save_reminders(self.assistant.reminders)

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                print(f"Reminder service error: {e}")
                time.sleep(60)

    def notification_service(self):
        """Enhanced notification reading service"""
        import subprocess
        
        while True:
            try:
                if not self.assistant or not self.assistant.is_active:
                    time.sleep(60)
                    continue
                    
                result = subprocess.run(
                    ["termux-notification-list"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.stdout.strip():
                    try:
                        notifications = json.loads(result.stdout)

                        for notif in notifications:
                            package_name = notif.get("packageName", "Unknown")
                            title = notif.get("title", "")
                            text = notif.get("text", "")

                            app_name = package_name.split(".")[-1].title()
                            message = f"New notification from {app_name}"
                            if title:
                                message += f": {title}"

                            print(f"📢 {message}")
                            self.assistant.tts.advanced_tts(message, "neutral")
                            time.sleep(2)

                    except json.JSONDecodeError:
                        pass

                time.sleep(60)  # Check every minute

            except Exception as e:
                time.sleep(60)

    def idle_timeout_service(self):
        """Service to handle idle timeout"""
        while True:
            try:
                if not self.assistant:
                    time.sleep(60)
                    continue
                    
                if self.assistant.is_active:
                    if time.time() - self.assistant.last_activity > self.assistant.idle_timeout:
                        self.assistant.is_active = False
                        self.assistant.security_authenticated = False
                        print("💤 Renz auto-sleep due to inactivity")
                        self.assistant.tts.advanced_tts("Going to sleep due to inactivity", "calm")

                time.sleep(60)  # Check every minute

            except Exception as e:
                time.sleep(60)

    def learning_service(self):
        """Adaptive learning service"""
        while True:
            try:
                if not self.assistant:
                    time.sleep(3600)
                    continue
                    
                current_hour = datetime.now().hour
                day_of_week = datetime.now().weekday()

                if self.assistant.user_preferences.get("auto_suggestions", True):
                    suggestions = self.assistant.analyze_usage_patterns()

                    if suggestions and self.assistant.is_active:
                        for suggestion in suggestions[:1]:
                            print(f"💡 {suggestion}")
                            self.assistant.tts.advanced_tts(suggestion, "friendly")
                            time.sleep(5)

                time.sleep(3600)  # Check every hour

            except Exception as e:
                time.sleep(3600)