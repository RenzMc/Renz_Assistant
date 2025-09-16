# Renz Assistant - Enhanced Voice Assistant for Android

An advanced modular voice assistant for Termux on Android devices with full Termux API integration.

## 🌟 Features

- **Enhanced Voice Recognition**: Multiple voice recognition engines (Termux API, Vosk, Whisper)
- **Wake Word Detection**: Activate the assistant with customizable wake words
- **Continuous Listening**: Background listening mode with wake word detection
- **Full Termux API Integration**: Access all device features through Termux API
- **AI-Powered Conversations**: Integration with OpenRouter API for intelligent responses
- **Multilingual Support**: Works in multiple languages (default: Indonesian)
- **Device Control**: Control device features like brightness, volume, flashlight, etc.
- **Weather Information**: Get weather forecasts and conditions
- **SMS and Call Management**: Send SMS, make calls, and view call logs
- **Location Services**: Access device location and provide location-based services
- **Notification Management**: Monitor and manage device notifications
- **Voice Authentication**: Secure access with voice profile recognition
- **Camera and Photo Capabilities**: Take photos and manage images
- **Body Sensor Access**: Access health and fitness data
- **NFC Control**: Read and write NFC tags
- **Bluetooth and Wi-Fi Management**: Control wireless connections
- **Infrared Transmission**: Control devices using IR blaster
- **Fingerprint Authentication**: Secure operations with biometrics
- **Customizable Personality**: Different assistant personalities and response styles

## 📋 Requirements

- Android device with Termux installed
- [Termux:API](https://f-droid.org/id/packages/com.termux.api/) app installed
- Python 3.7+ installed in Termux
- Internet connection for AI features and weather information

## 🚀 Installation

1. Install Termux and Termux:API from F-Droid:
   - [Termux](https://f-droid.org/packages/com.termux/)
   - [Termux:API](https://f-droid.org/packages/com.termux.api/)

2. Open Termux and install required packages:
   ```bash
   pkg update && pkg upgrade -y
   pkg install python git python-pip termux-api ffmpeg -y
   ```

3. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/renz-assistant.git
   cd renz-assistant
   ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the installation script:
   ```bash
   bash install.sh
   ```

## ⚙️ Configuration

Renz Assistant has extensive configuration options. Run the interactive setup to configure all settings:

```bash
./run_assistant.py --config
```

You can also access the configuration by saying "configure" or "setup" after activating the assistant.

### OpenRouter API Configuration

To use AI features, you need to set up an OpenRouter API key:

1. Create an account at [OpenRouter](https://openrouter.ai/)
2. Get your API key from the dashboard
3. Configure Renz Assistant with your API key:
   ```bash
   ./run_assistant.py --config-openrouter
   ```

### Voice Recognition Configuration

Configure voice recognition settings:

```bash
./run_assistant.py --config-voice
```

Options include:
- Engine selection (Termux API, Vosk, Whisper)
- Wake word customization
- Continuous listening mode
- Language settings
- Noise suppression and audio processing

### Termux API Permissions

Configure Termux API permissions:

```bash
./run_assistant.py --config-termux
```

Available permissions:
- Location (background, foreground approximate, foreground precise)
- Camera and microphone access
- SMS and call functionality
- Network and Wi-Fi control
- Body sensors access
- NFC and Bluetooth control
- And many more

## 🎮 Usage

### Starting the Assistant

```bash
./run_assistant.py
```

### Voice Authentication

On first run, you'll be prompted to create a voice profile for authentication:
1. Choose recording method (record new samples or use existing WAV files)
2. If recording new samples, speak the prompted phrase clearly
3. The system will create your voice profile for future authentication

### Wake Words

Activate the assistant with any of these wake words:
- "Hey Renz"
- "Ok Renz"
- "Hello Renz"
- "Hi Renz"
- "Renz"
- "Wake up Renz"
- "Renz bangun"
- "Renz aktif"
- And many more (customizable in settings)

### Sleep Words

Put the assistant to sleep with:
- "Renz turn off the system"
- "Tidur Renz"
- "Goodbye Renz"
- "Renz sleep"
- And others (customizable in settings)

### Example Commands

- "What's the weather like today?"
- "Send a message to John"
- "Call Mom"
- "Set brightness to 80%"
- "Turn on the flashlight"
- "What time is it?"
- "Tell me a joke"
- "What's the capital of France?"
- "Open WhatsApp"
- "Get my current location"
- "Take a photo"
- "Enable Wi-Fi"
- "Set volume to 10"
- "Configure settings"

## 📱 Termux API Features

Renz Assistant integrates with all Termux API features:

### Location Services
- Background location tracking
- Foreground approximate location
- Foreground precise location

### Device Control
- Screen brightness control
- Volume control
- Flashlight control
- Vibration control
- Wake lock management
- Wallpaper setting

### Communication
- SMS sending and reading
- Phone call management
- Call log access
- Contact management

### Notifications
- Notification monitoring
- Notification creation
- Notification removal

### Sensors
- Battery status monitoring
- Wi-Fi control and monitoring
- Bluetooth control
- NFC reading and writing
- Body sensors access
- Infrared transmission

### Media
- Camera access for photos
- Audio recording
- Text-to-speech
- Speech-to-text

### System
- Clipboard access
- Storage access
- Dialog creation
- Toast messages

## 🔧 Troubleshooting

### Termux API Not Available
If you see "Termux API not available" errors:
1. Make sure Termux:API app is installed
2. Run `termux-setup-storage` to grant storage permissions
3. Restart Termux and try again

### Voice Recognition Issues
If voice recognition is not working properly:
1. Try changing the voice recognition engine in the configuration
2. Make sure you have granted microphone permissions to Termux
3. Check if your device supports the selected voice recognition engine

### OpenRouter API Issues
If AI features are not working:
1. Check your internet connection
2. Verify your API key is correctly configured
3. Check if you have exceeded your API usage limits

### Microphone Issues
If you encounter microphone recording problems:
1. Ensure Termux API has microphone permissions
2. Run `termux-microphone-info` to check if your microphone is detected
3. Try `termux-setup-storage` to ensure proper storage access

### TTS Issues
If text-to-speech doesn't work:
1. Check your internet connection (edge-tts requires internet)
2. Ensure volume is turned up
3. Try `termux-tts-speak "test"` to verify Termux TTS is working

## 📚 Project Structure

```
renz_assistant/
├── modules/
│   ├── __init__.py
│   ├── audio.py        # Audio processing and TTS
│   ├── config.py       # Configuration management
│   ├── device.py       # Device-specific functions with Termux API
│   ├── nlp.py          # Natural language processing
│   ├── openrouter.py   # AI integration with OpenRouter
│   ├── services.py     # Background services
│   ├── storage.py      # Data persistence
│   ├── utils.py        # Utility functions
│   ├── voice_recognition.py # Enhanced voice recognition
│   └── weather.py      # Weather services
├── __init__.py
└── main.py             # Main assistant class
```

## 🎨 Customization

### Personality Profiles

Edit the personality profiles in `storage.py` to customize how the assistant responds:
- friendly
- funny
- serious
- teacher
- calm

### Language Preference

Change the default language in user preferences:
- "id" for Indonesian
- "en" for English

### Voice Recognition Engine

Choose between different voice recognition engines:
- termux_api: Uses Termux API's built-in speech recognition
- vosk: Offline speech recognition (requires additional model download)
- whisper: High-accuracy speech recognition using OpenAI's Whisper model

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [Termux](https://termux.com/) for the terminal emulator
- [Termux:API](https://wiki.termux.com/wiki/Termux:API) for the Android API integration
- [OpenRouter](https://openrouter.ai/) for the AI capabilities
- [Vosk](https://alphacephei.com/vosk/) for offline speech recognition
- [OpenAI Whisper](https://github.com/openai/whisper) for advanced speech recognition