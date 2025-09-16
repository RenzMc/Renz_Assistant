"""
Device-specific functions for Renz Assistant
Enhanced to work 100% with Termux API
Includes full TermuxAPI integration
"""
import os
import re
import json
import time
import shutil
import subprocess
import threading
from datetime import datetime
from dateutil import tz

class TermuxAPI:
    """Handles Termux API integration and features"""
    
    def __init__(self, config=None):
        """Initialize Termux API integration"""
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.permissions = self.config.get("permissions", {})
        self.location_update_interval = self.config.get("location_update_interval", 60)
        self.notification_check_interval = self.config.get("notification_check_interval", 30)
        
        # Background services
        self._location_thread = None
        self._notification_thread = None
        self._stop_threads = False
        
        # Cached data
        self.last_location = None
        self.last_location_time = 0
        self.last_notifications = []
        self.last_battery_status = None
        self.last_battery_time = 0
        
        # Check if Termux API is installed
        self.is_available = self._check_termux_api()
    
    def _check_termux_api(self):
        """Check if Termux API is installed and available"""
        try:
            result = subprocess.run(
                ["termux-api-start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def start_background_services(self):
        """Start background services for location and notifications"""
        if not self.enabled or not self.is_available:
            print("⚠️ Termux API is not enabled or not available")
            return False
        
        self._stop_threads = False
        
        # Start location tracking if enabled
        if (self.permissions.get("location", {}).get("background", False) or 
            self.permissions.get("location", {}).get("foreground_approximate", True) or 
            self.permissions.get("location", {}).get("foreground_precise", True)):
            self._location_thread = threading.Thread(
                target=self._location_tracking_worker,
                daemon=True
            )
            self._location_thread.start()
        
        # Start notification monitoring
        self._notification_thread = threading.Thread(
            target=self._notification_monitoring_worker,
            daemon=True
        )
        self._notification_thread.start()
        
        print("✅ Termux API background services started")
        return True
    
    def stop_background_services(self):
        """Stop background services"""
        self._stop_threads = True
        
        # Wait for threads to terminate
        if self._location_thread:
            self._location_thread.join(timeout=2)
        
        if self._notification_thread:
            self._notification_thread.join(timeout=2)
        
        print("✅ Termux API background services stopped")
        return True
    
    def _location_tracking_worker(self):
        """Background worker for location tracking"""
        print("📍 Starting location tracking service...")
        
        while not self._stop_threads:
            try:
                # Get location based on permissions
                if self.permissions.get("location", {}).get("foreground_precise", True):
                    provider = "gps"
                elif self.permissions.get("location", {}).get("foreground_approximate", True):
                    provider = "network"
                else:
                    # Sleep and continue if no permission
                    time.sleep(self.location_update_interval)
                    continue
                
                # Get location
                location = self.get_location(provider)
                
                if location:
                    self.last_location = location
                    self.last_location_time = time.time()
                
                # Sleep for the configured interval
                time.sleep(self.location_update_interval)
            
            except Exception as e:
                print(f"Error in location tracking: {e}")
                time.sleep(self.location_update_interval)
    
    def _notification_monitoring_worker(self):
        """Background worker for notification monitoring"""
        print("🔔 Starting notification monitoring service...")
        
        while not self._stop_threads:
            try:
                # Get notifications
                notifications = self.get_notifications()
                
                if notifications:
                    # Check for new notifications
                    new_notifications = []
                    for notif in notifications:
                        if notif not in self.last_notifications:
                            new_notifications.append(notif)
                    
                    # Update last notifications
                    self.last_notifications = notifications
                    
                    # Process new notifications (can be extended to call callbacks)
                    for notif in new_notifications:
                        print(f"🔔 New notification: {notif.get('title', 'Unknown')} - {notif.get('content', '')}")
                
                # Sleep for the configured interval
                time.sleep(self.notification_check_interval)
            
            except Exception as e:
                print(f"Error in notification monitoring: {e}")
                time.sleep(self.notification_check_interval)
    
    # Location Services
    
    def get_location(self, provider="gps"):
        """Get current location using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            # Check permissions
            if provider == "gps" and not self.permissions.get("location", {}).get("foreground_precise", True):
                return None
            
            if provider == "network" and not self.permissions.get("location", {}).get("foreground_approximate", True):
                return None
            
            # Get location
            result = subprocess.run(
                ["termux-location", "-p", provider],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    location_data = json.loads(result.stdout)
                    return {
                        "latitude": location_data.get("latitude"),
                        "longitude": location_data.get("longitude"),
                        "altitude": location_data.get("altitude"),
                        "accuracy": location_data.get("accuracy"),
                        "bearing": location_data.get("bearing"),
                        "speed": location_data.get("speed"),
                        "provider": location_data.get("provider"),
                        "timestamp": datetime.now().isoformat()
                    }
                except json.JSONDecodeError:
                    print(f"Error parsing location data: {result.stdout}")
                    return None
            else:
                print(f"Error getting location: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting location: {e}")
            return None
    
    def get_cached_location(self, max_age_seconds=300):
        """Get cached location if available and not too old"""
        if self.last_location and (time.time() - self.last_location_time) <= max_age_seconds:
            return self.last_location
        
        # Get fresh location
        return self.get_location()
    
    # Notification Services
    
    def get_notifications(self):
        """Get current notifications using Termux API"""
        if not self.enabled or not self.is_available:
            return []
        
        try:
            result = subprocess.run(
                ["termux-notification-list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing notification data: {result.stdout}")
                    return []
            else:
                print(f"Error getting notifications: {result.stderr}")
                return []
        
        except Exception as e:
            print(f"Error getting notifications: {e}")
            return []
    
    def create_notification(self, title, content, id=None, channel_id=None, priority=None, 
                           ongoing=False, alert_once=True, group=None, image_path=None, 
                           action=None, action_title=None, led_color=None, vibrate_pattern=None,
                           sound=True, button1=None, button1_action=None, button2=None, button2_action=None,
                           button3=None, button3_action=None):
        """Create a notification using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            cmd = ["termux-notification", "--title", title, "--content", content]
            
            # Add optional parameters
            if id is not None:
                cmd.extend(["--id", str(id)])
            
            if channel_id:
                cmd.extend(["--channel-id", channel_id])
            
            if priority:
                cmd.extend(["--priority", priority])
            
            if ongoing:
                cmd.append("--ongoing")
            
            if alert_once:
                cmd.append("--alert-once")
            
            if group:
                cmd.extend(["--group", group])
            
            if image_path and os.path.exists(image_path):
                cmd.extend(["--image-path", image_path])
            
            if action:
                cmd.extend(["--action", action])
            
            if action_title:
                cmd.extend(["--action-title", action_title])
            
            if led_color:
                cmd.extend(["--led-color", led_color])
            
            if vibrate_pattern:
                cmd.extend(["--vibrate-pattern", vibrate_pattern])
            
            if not sound:
                cmd.append("--sound")
            
            # Add buttons
            if button1 and button1_action:
                cmd.extend(["--button1", button1, "--button1-action", button1_action])
            
            if button2 and button2_action:
                cmd.extend(["--button2", button2, "--button2-action", button2_action])
            
            if button3 and button3_action:
                cmd.extend(["--button3", button3, "--button3-action", button3_action])
            
            # Create notification
            subprocess.run(cmd, check=True)
            return True
        
        except Exception as e:
            print(f"Error creating notification: {e}")
            return False
    
    def remove_notification(self, notification_id):
        """Remove a notification using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-notification-remove", str(notification_id)],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error removing notification: {e}")
            return False
    
    # Battery Services
    
    def get_battery_status(self):
        """Get battery status using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    battery_data = json.loads(result.stdout)
                    self.last_battery_status = battery_data
                    self.last_battery_time = time.time()
                    return battery_data
                except json.JSONDecodeError:
                    print(f"Error parsing battery data: {result.stdout}")
                    return None
            else:
                print(f"Error getting battery status: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting battery status: {e}")
            return None
    
    def get_cached_battery_status(self, max_age_seconds=60):
        """Get cached battery status if available and not too old"""
        if self.last_battery_status and (time.time() - self.last_battery_time) <= max_age_seconds:
            return self.last_battery_status
        
        # Get fresh battery status
        return self.get_battery_status()
    
    # Camera Services
    
    def take_photo(self, camera_id=0, output_file=None):
        """Take a photo using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        if not self.permissions.get("camera", True):
            print("⚠️ Camera permission not granted")
            return None
        
        try:
            # Generate output file if not provided
            if output_file is None:
                timestamp = int(time.time() * 1000)
                output_file = f"photo_{timestamp}.jpg"
            
            # Take photo
            cmd = ["termux-camera-photo"]
            
            # Add camera ID if specified
            if camera_id is not None:
                cmd.extend(["-c", str(camera_id)])
            
            cmd.append(output_file)
            
            subprocess.run(cmd, check=True)
            
            # Check if file was created
            if os.path.exists(output_file):
                return output_file
            else:
                print(f"Error: Photo file not created at {output_file}")
                return None
        
        except Exception as e:
            print(f"Error taking photo: {e}")
            return None
    
    # SMS Services
    
    def send_sms(self, number, message):
        """Send SMS using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        if not self.permissions.get("sms", True):
            print("⚠️ SMS permission not granted")
            return False
        
        try:
            subprocess.run(
                ["termux-sms-send", "-n", number, message],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False
    
    def list_sms(self, limit=10, offset=0, type="inbox", unread_only=False):
        """List SMS messages using Termux API"""
        if not self.enabled or not self.is_available:
            return []
        
        if not self.permissions.get("sms", True):
            print("⚠️ SMS permission not granted")
            return []
        
        try:
            cmd = ["termux-sms-list"]
            
            # Add parameters
            if limit:
                cmd.extend(["-l", str(limit)])
            
            if offset:
                cmd.extend(["-o", str(offset)])
            
            if type:
                cmd.extend(["-t", type])
            
            if unread_only:
                cmd.append("-u")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing SMS data: {result.stdout}")
                    return []
            else:
                print(f"Error listing SMS: {result.stderr}")
                return []
        
        except Exception as e:
            print(f"Error listing SMS: {e}")
            return []
    
    # Call Services
    
    def make_call(self, number):
        """Make a phone call using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        if not self.permissions.get("call_phone", True):
            print("⚠️ Call phone permission not granted")
            return False
        
        try:
            subprocess.run(
                ["termux-telephony-call", number],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error making call: {e}")
            return False
    
    def get_call_log(self, limit=10, offset=0):
        """Get call log using Termux API"""
        if not self.enabled or not self.is_available:
            return []
        
        try:
            cmd = ["termux-call-log"]
            
            # Add parameters
            if limit:
                cmd.extend(["-l", str(limit)])
            
            if offset:
                cmd.extend(["-o", str(offset)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing call log data: {result.stdout}")
                    return []
            else:
                print(f"Error getting call log: {result.stderr}")
                return []
        
        except Exception as e:
            print(f"Error getting call log: {e}")
            return []
    
    # Network Services
    
    def get_wifi_info(self):
        """Get Wi-Fi connection info using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        if not self.permissions.get("wifi", True):
            print("⚠️ Wi-Fi permission not granted")
            return None
        
        try:
            result = subprocess.run(
                ["termux-wifi-connectioninfo"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing Wi-Fi info data: {result.stdout}")
                    return None
            else:
                print(f"Error getting Wi-Fi info: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting Wi-Fi info: {e}")
            return None
    
    def scan_wifi(self):
        """Scan for Wi-Fi networks using Termux API"""
        if not self.enabled or not self.is_available:
            return []
        
        if not self.permissions.get("wifi", True):
            print("⚠️ Wi-Fi permission not granted")
            return []
        
        try:
            result = subprocess.run(
                ["termux-wifi-scaninfo"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing Wi-Fi scan data: {result.stdout}")
                    return []
            else:
                print(f"Error scanning Wi-Fi: {result.stderr}")
                return []
        
        except Exception as e:
            print(f"Error scanning Wi-Fi: {e}")
            return []
    
    def enable_wifi(self):
        """Enable Wi-Fi using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        if not self.permissions.get("wifi", True):
            print("⚠️ Wi-Fi permission not granted")
            return False
        
        try:
            subprocess.run(
                ["termux-wifi-enable", "true"],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error enabling Wi-Fi: {e}")
            return False
    
    def disable_wifi(self):
        """Disable Wi-Fi using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        if not self.permissions.get("wifi", True):
            print("⚠️ Wi-Fi permission not granted")
            return False
        
        try:
            subprocess.run(
                ["termux-wifi-enable", "false"],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error disabling Wi-Fi: {e}")
            return False
    
    # Sensor Services
    
    def get_sensor_list(self):
        """Get list of available sensors using Termux API"""
        if not self.enabled or not self.is_available:
            return []
        
        try:
            result = subprocess.run(
                ["termux-sensor", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing sensor list data: {result.stdout}")
                    return []
            else:
                print(f"Error getting sensor list: {result.stderr}")
                return []
        
        except Exception as e:
            print(f"Error getting sensor list: {e}")
            return []
    
    def get_sensor_data(self, sensor_name, limit=1):
        """Get sensor data using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        if sensor_name.startswith("heart") and not self.permissions.get("body_sensors", False):
            print("⚠️ Body sensors permission not granted")
            return None
        
        try:
            cmd = ["termux-sensor", "-s", sensor_name, "-n", str(limit)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing sensor data: {result.stdout}")
                    return None
            else:
                print(f"Error getting sensor data: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting sensor data: {e}")
            return None
    
    # NFC Services
    
    def read_nfc(self, timeout=60):
        """Read NFC tag using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        if not self.permissions.get("nfc", False):
            print("⚠️ NFC permission not granted")
            return None
        
        try:
            result = subprocess.run(
                ["termux-nfc", "-r", "-t", str(timeout)],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing NFC data: {result.stdout}")
                    return None
            else:
                print(f"Error reading NFC: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error reading NFC: {e}")
            return None
    
    def write_nfc(self, data, timeout=60):
        """Write to NFC tag using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        if not self.permissions.get("nfc", False):
            print("⚠️ NFC permission not granted")
            return False
        
        try:
            # Create temporary file with data
            temp_file = f"/tmp/nfc_data_{int(time.time())}.txt"
            with open(temp_file, "w") as f:
                f.write(data)
            
            # Write to NFC tag
            result = subprocess.run(
                ["termux-nfc", "-w", temp_file, "-t", str(timeout)],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            
            # Remove temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            if result.returncode == 0:
                return True
            else:
                print(f"Error writing to NFC: {result.stderr}")
                return False
        
        except Exception as e:
            print(f"Error writing to NFC: {e}")
            return False
    
    # Device Control Services
    
    def set_brightness(self, brightness):
        """Set screen brightness using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-brightness", str(brightness)],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error setting brightness: {e}")
            return False
    
    def get_brightness(self):
        """Get screen brightness using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                ["termux-brightness"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return int(result.stdout.strip())
                except ValueError:
                    print(f"Error parsing brightness data: {result.stdout}")
                    return None
            else:
                print(f"Error getting brightness: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting brightness: {e}")
            return None
    
    def set_volume(self, stream, volume):
        """Set volume using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-volume", stream, str(volume)],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False
    
    def get_volume(self):
        """Get volume information using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                ["termux-volume"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing volume data: {result.stdout}")
                    return None
            else:
                print(f"Error getting volume: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting volume: {e}")
            return None
    
    def toggle_flashlight(self, on=True):
        """Toggle flashlight using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-torch", "on" if on else "off"],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error toggling flashlight: {e}")
            return False
    
    def vibrate(self, duration_ms=1000, force=False):
        """Vibrate device using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            cmd = ["termux-vibrate"]
            
            # Add parameters
            if duration_ms:
                cmd.extend(["-d", str(duration_ms)])
            
            if force:
                cmd.append("-f")
            
            subprocess.run(cmd, check=True)
            return True
        
        except Exception as e:
            print(f"Error vibrating device: {e}")
            return False
    
    # Dialog Services
    
    def show_dialog(self, dialog_type="text", title=None, hint=None, 
                   values=None, multiple=False, password=False):
        """Show dialog using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            cmd = ["termux-dialog", dialog_type]
            
            # Add parameters
            if title:
                cmd.extend(["-t", title])
            
            if hint:
                cmd.extend(["-i", hint])
            
            if values:
                cmd.extend(["-v", values])
            
            if multiple:
                cmd.append("-m")
            
            if password:
                cmd.append("-p")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for user input
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing dialog data: {result.stdout}")
                    return None
            else:
                print(f"Error showing dialog: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error showing dialog: {e}")
            return None
    
    def show_toast(self, message, short=True):
        """Show toast message using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            cmd = ["termux-toast"]
            
            # Add parameters
            if not short:
                cmd.append("-l")
            
            cmd.append(message)
            
            subprocess.run(cmd, check=True)
            return True
        
        except Exception as e:
            print(f"Error showing toast: {e}")
            return False
    
    def text_to_speech(self, text, language=None, region=None, variant=None, 
                      pitch=None, rate=None, stream=None):
        """Convert text to speech using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            cmd = ["termux-tts-speak"]
            
            # Add parameters
            if language:
                cmd.extend(["-l", language])
            
            if region:
                cmd.extend(["-r", region])
            
            if variant:
                cmd.extend(["-v", variant])
            
            if pitch:
                cmd.extend(["-p", str(pitch)])
            
            if rate:
                cmd.extend(["-e", str(rate)])
            
            if stream:
                cmd.extend(["-s", stream])
            
            cmd.append(text)
            
            subprocess.run(cmd, check=True)
            return True
        
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return False
    
    # Clipboard Services
    
    def set_clipboard(self, text):
        """Set clipboard content using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            process = subprocess.Popen(
                ["termux-clipboard-set"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode())
            return process.returncode == 0
        
        except Exception as e:
            print(f"Error setting clipboard: {e}")
            return False
    
    def get_clipboard(self):
        """Get clipboard content using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                ["termux-clipboard-get"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Error getting clipboard: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting clipboard: {e}")
            return None
    
    # Infrared Services
    
    def transmit_ir(self, frequency, pattern):
        """Transmit infrared pattern using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-infrared-transmit", "-f", str(frequency), "-p", pattern],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error transmitting IR: {e}")
            return False
    
    # Fingerprint Services
    
    def authenticate_with_fingerprint(self, title=None, description=None, subtitle=None, cancel=None):
        """Authenticate using fingerprint with Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            cmd = ["termux-fingerprint"]
            
            # Add parameters
            if title:
                cmd.extend(["-t", title])
            
            if description:
                cmd.extend(["-d", description])
            
            if subtitle:
                cmd.extend(["-s", subtitle])
            
            if cancel:
                cmd.extend(["-c", cancel])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return data.get("auth_result") == "SUCCESS"
                except json.JSONDecodeError:
                    print(f"Error parsing fingerprint data: {result.stdout}")
                    return False
            else:
                print(f"Error authenticating with fingerprint: {result.stderr}")
                return False
        
        except Exception as e:
            print(f"Error authenticating with fingerprint: {e}")
            return False
    
    # System Services
    
    def get_device_info(self):
        """Get device information using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                ["termux-telephony-deviceinfo"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing device info data: {result.stdout}")
                    return None
            else:
                print(f"Error getting device info: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting device info: {e}")
            return None
    
    def get_sim_info(self):
        """Get SIM card information using Termux API"""
        if not self.enabled or not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                ["termux-telephony-cellinfo"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"Error parsing SIM info data: {result.stdout}")
                    return None
            else:
                print(f"Error getting SIM info: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error getting SIM info: {e}")
            return None
    
    def open_url(self, url):
        """Open URL using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-open-url", url],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error opening URL: {e}")
            return False
    
    def open_file(self, file_path):
        """Open file using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False
            
            subprocess.run(
                ["termux-open", file_path],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error opening file: {e}")
            return False
    
    def set_wallpaper(self, file_path, lockscreen=False):
        """Set wallpaper using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False
            
            cmd = ["termux-wallpaper", "-f", file_path]
            
            if lockscreen:
                cmd.append("-l")
            
            subprocess.run(cmd, check=True)
            return True
        
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            return False
    
    def acquire_wakelock(self):
        """Acquire wakelock using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-wake-lock"],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error acquiring wakelock: {e}")
            return False
    
    def release_wakelock(self):
        """Release wakelock using Termux API"""
        if not self.enabled or not self.is_available:
            return False
        
        try:
            subprocess.run(
                ["termux-wake-unlock"],
                check=True
            )
            return True
        
        except Exception as e:
            print(f"Error releasing wakelock: {e}")
            return False


class DeviceInterface:
    """Handles device-specific operations using Termux API with 100% reliability"""
    
    def __init__(self, language="id"):
        """Initialize device interface"""
        self.language = language
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".renz_assistant", "cache")
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                print(f"Failed to create cache directory: {e}")
        
        # Check if Termux API is available
        self.termux_api_available = self._check_termux_api()
        if self.termux_api_available:
            print("✅ Termux API is available")
        else:
            print("⚠️ Termux API is not available. Some features may not work.")
            
        # Initialize TermuxAPI instance
        self.termux = TermuxAPI()
    
    def _check_termux_api(self):
        """Check if Termux API is available"""
        try:
            # Try a simple Termux API command
            result = subprocess.run(
                ["termux-api-start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _run_termux_command(self, command, args=None, timeout=10, fallback_func=None, fallback_args=None):
        """
        Run a Termux API command with fallback
        
        Args:
            command: Termux API command to run
            args: List of arguments for the command
            timeout: Command timeout in seconds
            fallback_func: Function to call if command fails
            fallback_args: Arguments for fallback function
            
        Returns:
            Command output or fallback function result
        """
        if not self.termux_api_available:
            if fallback_func:
                return fallback_func(*fallback_args) if fallback_args else fallback_func()
            return None
        
        try:
            cmd = [command]
            if args:
                cmd.extend(args)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Command {command} failed: {result.stderr}")
                if fallback_func:
                    return fallback_func(*fallback_args) if fallback_args else fallback_func()
                return None
        except subprocess.TimeoutExpired:
            print(f"Command {command} timed out after {timeout} seconds")
            if fallback_func:
                return fallback_func(*fallback_args) if fallback_args else fallback_func()
            return None
        except Exception as e:
            print(f"Error running command {command}: {e}")
            if fallback_func:
                return fallback_func(*fallback_args) if fallback_args else fallback_func()
            return None
    
    def get_battery_status(self):
        """Get device battery status"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            battery_data = self.termux.get_battery_status()
            if battery_data:
                percentage = battery_data.get("percentage", "unknown")
                status = battery_data.get("status", "unknown")
                temperature = battery_data.get("temperature", "unknown")
                current = battery_data.get("current", "unknown")
                
                msg_en = f"Battery: {percentage}% ({status}), Temperature: {temperature}°C, Current: {current} mA"
                msg_id = f"Baterai: {percentage}% ({status}), Suhu: {temperature}°C, Arus: {current} mA"
                
                return msg_id if self.language == "id" else msg_en
        
        # Fall back to original implementation
        def fallback():
            return "Battery status unavailable"
        
        result = self._run_termux_command("termux-battery-status", fallback_func=fallback)
        
        if result and result != fallback():
            try:
                battery_data = json.loads(result)
                percentage = battery_data.get("percentage", "unknown")
                status = battery_data.get("status", "unknown")
                temperature = battery_data.get("temperature", "unknown")
                current = battery_data.get("current", "unknown")
                
                msg_en = f"Battery: {percentage}% ({status}), Temperature: {temperature}°C, Current: {current} mA"
                msg_id = f"Baterai: {percentage}% ({status}), Suhu: {temperature}°C, Arus: {current} mA"
                
                return msg_id if self.language == "id" else msg_en
            except json.JSONDecodeError:
                return fallback()
        
        return fallback()
    
    def get_current_time(self):
        """Get current time"""
        try:
            local_timezone = tz.tzlocal()
            current_time = datetime.now(local_timezone)
            
            if self.language == "id":
                # Indonesian format
                time_str = current_time.strftime("Waktu sekarang: %H:%M:%S")
            else:
                # English format
                time_str = current_time.strftime("Current time: %I:%M:%S %p")
            
            return time_str
        except Exception as e:
            return f"Time unavailable: {e}"
    
    def get_current_date(self):
        """Get current date"""
        try:
            local_timezone = tz.tzlocal()
            current_time = datetime.now(local_timezone)
            
            if self.language == "id":
                # Indonesian format
                # Map English day and month names to Indonesian
                days_id = {
                    "Monday": "Senin",
                    "Tuesday": "Selasa",
                    "Wednesday": "Rabu",
                    "Thursday": "Kamis",
                    "Friday": "Jumat",
                    "Saturday": "Sabtu",
                    "Sunday": "Minggu"
                }
                
                months_id = {
                    "January": "Januari",
                    "February": "Februari",
                    "March": "Maret",
                    "April": "April",
                    "May": "Mei",
                    "June": "Juni",
                    "July": "Juli",
                    "August": "Agustus",
                    "September": "September",
                    "October": "Oktober",
                    "November": "November",
                    "December": "Desember"
                }
                
                day_en = current_time.strftime("%A")
                month_en = current_time.strftime("%B")
                
                day_id = days_id.get(day_en, day_en)
                month_id = months_id.get(month_en, month_en)
                
                date_str = f"Hari ini: {day_id}, {current_time.day} {month_id} {current_time.year}"
            else:
                # English format
                date_str = current_time.strftime("Today is: %A, %B %d, %Y")
            
            return date_str
        except Exception as e:
            return f"Date unavailable: {e}"
    
    def send_sms(self, phone_number, message, log_activity_callback=None):
        """Send SMS via Termux API"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            success = self.termux.send_sms(phone_number, message)
            if success:
                if log_activity_callback:
                    log_activity_callback("sms_sent", {"to": phone_number, "message": message[:50]})
                
                msg_en = f"SMS sent to {phone_number}"
                msg_id = f"SMS terkirim ke {phone_number}"
                return msg_id if self.language == "id" else msg_en
        
        # Fall back to original implementation
        def fallback():
            msg_en = f"Failed to send SMS: Termux API not available"
            msg_id = f"Gagal mengirim SMS: Termux API tidak tersedia"
            return msg_id if self.language == "id" else msg_en
        
        result = self._run_termux_command(
            "termux-sms-send",
            ["-n", phone_number, message],
            timeout=15,
            fallback_func=fallback
        )
        
        if result is None:  # Command succeeded with no output
            if log_activity_callback:
                log_activity_callback("sms_sent", {"to": phone_number, "message": message[:50]})
            
            msg_en = f"SMS sent to {phone_number}"
            msg_id = f"SMS terkirim ke {phone_number}"
            return msg_id if self.language == "id" else msg_en
        
        return result  # This will be the fallback message if command failed
    
    def list_sms(self, filter_unread=False, tts_callback=None):
        """List SMS messages"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            sms_list = self.termux.list_sms(unread_only=filter_unread)
            if sms_list is not None:
                messages = []
                
                for sms in sms_list:
                    status = "Unread" if not sms.get("read", True) else "Read"
                    status_id = "Belum dibaca" if not sms.get("read", True) else "Sudah dibaca"
                    
                    msg = sms.get("body", "")[:50]
                    addr = sms.get("address", "")
                    
                    if self.language == "id":
                        messages.append(f"[{status_id}] {addr}: {msg}")
                    else:
                        messages.append(f"[{status}] {addr}: {msg}")
                
                if not messages:
                    text = "No messages" if self.language == "en" else "Tidak ada pesan"
                    if tts_callback:
                        tts_callback(text)
                    return text
                
                text = "\n".join(messages)
                if tts_callback:
                    tts_callback(text)
                return text
        
        # Fall back to original implementation
        def fallback():
            msg_en = "Failed to list SMS: Termux API not available"
            msg_id = "Gagal menampilkan SMS: Termux API tidak tersedia"
            return msg_id if self.language == "id" else msg_en
        
        cmd = ["termux-sms-list"]
        if filter_unread:
            cmd.append("-u")
        
        result = self._run_termux_command(
            cmd[0],
            cmd[1:] if len(cmd) > 1 else None,
            timeout=15,
            fallback_func=fallback
        )
        
        if result and result != fallback():
            try:
                sms_list = json.loads(result)
                messages = []
                
                for sms in sms_list:
                    status = "Unread" if not sms.get("read", True) else "Read"
                    status_id = "Belum dibaca" if not sms.get("read", True) else "Sudah dibaca"
                    
                    msg = sms.get("body", "")[:50]
                    addr = sms.get("address", "")
                    
                    if self.language == "id":
                        messages.append(f"[{status_id}] {addr}: {msg}")
                    else:
                        messages.append(f"[{status}] {addr}: {msg}")
                
                if not messages:
                    text = "No messages" if self.language == "en" else "Tidak ada pesan"
                    if tts_callback:
                        tts_callback(text)
                    return text
                
                text = "\n".join(messages)
                if tts_callback:
                    tts_callback(text)
                return text
            except json.JSONDecodeError:
                return fallback()
        
        return fallback()
    
    def get_call_logs(self, max_entries=10, tts_callback=None):
        """Get call logs"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            call_logs = self.termux.get_call_log(limit=max_entries)
            if call_logs is not None:
                logs = []
                
                for log in call_logs[:max_entries]:
                    ctype = log.get("type", "unknown").capitalize()
                    ctype_id = {
                        "Incoming": "Masuk",
                        "Outgoing": "Keluar",
                        "Missed": "Tidak terjawab",
                        "Rejected": "Ditolak",
                        "Unknown": "Tidak diketahui"
                    }.get(ctype, ctype)
                    
                    num = log.get("number", "")
                    dur = log.get("duration", 0)
                    dt = datetime.fromtimestamp(int(log.get("date", 0)) / 1000)
                    
                    if self.language == "id":
                        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        logs.append(f"{dt_str} - {ctype_id} - {num} - Durasi: {dur} detik")
                    else:
                        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        logs.append(f"{dt_str} - {ctype} - {num} - Duration: {dur}s")
                
                if not logs:
                    text = "No call logs" if self.language == "en" else "Tidak ada riwayat panggilan"
                    if tts_callback:
                        tts_callback(text)
                    return text
                
                text = "\n".join(logs)
                if tts_callback:
                    tts_callback(text)
                return text
        
        # Fall back to original implementation
        def fallback():
            msg_en = "Failed to get call logs: Termux API not available"
            msg_id = "Gagal mendapatkan log panggilan: Termux API tidak tersedia"
            return msg_id if self.language == "id" else msg_en
        
        result = self._run_termux_command(
            "termux-call-log",
            ["-l", str(max_entries)],
            timeout=15,
            fallback_func=fallback
        )
        
        if result and result != fallback():
            try:
                call_logs = json.loads(result)
                logs = []
                
                for log in call_logs[:max_entries]:
                    ctype = log.get("type", "unknown").capitalize()
                    ctype_id = {
                        "Incoming": "Masuk",
                        "Outgoing": "Keluar",
                        "Missed": "Tidak terjawab",
                        "Rejected": "Ditolak",
                        "Unknown": "Tidak diketahui"
                    }.get(ctype, ctype)
                    
                    num = log.get("number", "")
                    dur = log.get("duration", 0)
                    dt = datetime.fromtimestamp(int(log.get("date", 0)) / 1000)
                    
                    if self.language == "id":
                        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        logs.append(f"{dt_str} - {ctype_id} - {num} - Durasi: {dur} detik")
                    else:
                        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        logs.append(f"{dt_str} - {ctype} - {num} - Duration: {dur}s")
                
                if not logs:
                    text = "No call logs" if self.language == "en" else "Tidak ada riwayat panggilan"
                    if tts_callback:
                        tts_callback(text)
                    return text
                
                text = "\n".join(logs)
                if tts_callback:
                    tts_callback(text)
                return text
            except json.JSONDecodeError:
                return fallback()
        
        return fallback()
        
    def get_device_info(self, tts_callback=None):
        """Get device information"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            device_info = self.termux.get_device_info()
            sim_info = self.termux.get_sim_info()
            
            if device_info or sim_info:
                info_str = "📱 " + ("Info Perangkat:" if self.language == "id" else "Device Info:") + "\n"
                
                if device_info:
                    for k, v in device_info.items():
                        info_str += f"• {k}: {v}\n"
                
                info_str += "\n📶 " + ("Info SIM:" if self.language == "id" else "SIM Info:") + "\n"
                
                if sim_info:
                    for k, v in sim_info.items():
                        info_str += f"• {k}: {v}\n"
                
                if tts_callback:
                    tts_callback(info_str)
                
                return info_str
        
        # Fall back to original implementation
        def fallback():
            msg_en = "Failed to get device info: Termux API not available"
            msg_id = "Gagal mendapatkan info perangkat: Termux API tidak tersedia"
            return msg_id if self.language == "id" else msg_en
        
        # Get device info
        device_info_result = self._run_termux_command(
            "termux-telephony-deviceinfo",
            timeout=10
        )
        
        # Get SIM info
        sim_info_result = self._run_termux_command(
            "termux-telephony-cellinfo",
            timeout=10
        )
        
        if not device_info_result and not sim_info_result:
            return fallback()
        
        try:
            info_str = "📱 " + ("Info Perangkat:" if self.language == "id" else "Device Info:") + "\n"
            
            if device_info_result:
                try:
                    device_info = json.loads(device_info_result)
                    for k, v in device_info.items():
                        info_str += f"• {k}: {v}\n"
                except json.JSONDecodeError:
                    pass
            
            info_str += "\n📶 " + ("Info SIM:" if self.language == "id" else "SIM Info:") + "\n"
            
            if sim_info_result:
                try:
                    sim_info = json.loads(sim_info_result)
                    for k, v in sim_info.items():
                        info_str += f"• {k}: {v}\n"
                except json.JSONDecodeError:
                    pass
            
            if tts_callback:
                tts_callback(info_str)
            
            return info_str
        except Exception as e:
            return f"Failed to get device info: {e}"
            
    def set_clipboard(self, text, tts_callback=None):
        """Set clipboard content"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            success = self.termux.set_clipboard(text)
            if success:
                msg_en = "Copied to clipboard"
                msg_id = "Teks disalin ke clipboard"
                t = msg_id if self.language == "id" else msg_en
                if tts_callback:
                    tts_callback(t)
                return t
        
        # Fall back to original implementation
        def fallback():
            msg_en = "Failed to set clipboard: Termux API not available"
            msg_id = "Gagal menyalin ke clipboard: Termux API tidak tersedia"
            return msg_id if self.language == "id" else msg_en
        
        try:
            process = subprocess.Popen(
                ["termux-clipboard-set"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode())
            success = process.returncode == 0
            
            if success:
                msg_en = "Copied to clipboard"
                msg_id = "Teks disalin ke clipboard"
                t = msg_id if self.language == "id" else msg_en
                if tts_callback:
                    tts_callback(t)
                return t
            else:
                return fallback()
        except Exception:
            return fallback()
    
    def get_clipboard(self, tts_callback=None):
        """Get clipboard content"""
        # Use TermuxAPI implementation if available
        if self.termux_api_available and self.termux.is_available:
            content = self.termux.get_clipboard()
            if content is not None:
                content = content.strip()
                if content:
                    msg_en = f"Clipboard content:\n{content}"
                    msg_id = f"Isi clipboard:\n{content}"
                    t = msg_id if self.language == "id" else msg_en
                    if tts_callback:
                        tts_callback(t)
                    return t
                else:
                    t = "Clipboard empty" if self.language == "en" else "Clipboard kosong"
                    if tts_callback:
                        tts_callback(t)
                    return t
        
        # Fall back to original implementation
        def fallback():
            msg_en = "Failed to get clipboard: Termux API not available"
            msg_id = "Gagal mendapatkan clipboard: Termux API tidak tersedia"
            return msg_id if self.language == "id" else msg_en
        
        result = self._run_termux_command(
            "termux-clipboard-get",
            timeout=5,
            fallback_func=fallback
        )
        
        if result and result != fallback():
            content = result.strip()
            if content:
                msg_en = f"Clipboard content:\n{content}"
                msg_id = f"Isi clipboard:\n{content}"
                t = msg_id if self.language == "id" else msg_en
                if tts_callback:
                    tts_callback(t)
                return t
            else:
                t = "Clipboard empty" if self.language == "en" else "Clipboard kosong"
                if tts_callback:
                    tts_callback(t)
                return t
        
        return result  # This will be the fallback message if command failed