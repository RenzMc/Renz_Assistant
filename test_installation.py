#!/usr/bin/env python3
"""
Test script for Renz Assistant installation
This script checks if all required components are installed and working correctly
"""
import os
import sys
import time
import subprocess
import importlib
import platform

def print_color(color, text):
    """Print colored text"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def check_module(module_name):
    """Check if a Python module is installed"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def check_command(command):
    """Check if a command is available"""
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def main():
    """Main test function"""
    print_color("cyan", "\n=== Renz Assistant Installation Test ===\n")
    
    # Check Python version
    python_version = platform.python_version()
    print(f"Python version: {python_version}")
    if int(python_version.split('.')[0]) >= 3 and int(python_version.split('.')[1]) >= 6:
        print_color("green", "✅ Python version is compatible")
    else:
        print_color("red", "❌ Python version is not compatible. Renz Assistant requires Python 3.6+")
    
    # Check required modules
    required_modules = [
        "nltk", "edge_tts", "requests",
        "dateutil", "geopy"
    ]

    print("\nChecking required Python modules:")
    all_modules_installed = True
    for module in required_modules:
        if check_module(module):
            print_color("green", f"✅ {module} is installed")
        else:
            print_color("red", f"❌ {module} is not installed")
            all_modules_installed = False

    # Check optional modules
    optional_modules = ["vosk", "whisper"]
    
    print("\nChecking optional Python modules:")
    for module in optional_modules:
        if check_module(module):
            print_color("green", f"✅ {module} is installed")
        else:
            print_color("yellow", f"⚠️ {module} is not installed (optional)")
    
    # Check Termux API
    print("\nChecking Termux API:")
    termux_commands = [
        ["termux-battery-status"], 
        ["termux-microphone-record", "-h"],
        ["termux-tts-speak", "-h"],
        ["termux-location", "-h"]
    ]
    
    termux_api_available = True
    for cmd in termux_commands:
        if check_command(cmd):
            print_color("green", f"✅ {cmd[0]} is available")
        else:
            print_color("yellow", f"⚠️ {cmd[0]} is not available")
            termux_api_available = False
    
    # Check ffmpeg
    print("\nChecking ffmpeg:")
    if check_command(["ffmpeg", "-version"]):
        print_color("green", "✅ ffmpeg is installed")
    else:
        print_color("red", "❌ ffmpeg is not installed")
    
    # Check project files
    print("\nChecking project files:")
    required_files = [
        "run_assistant.py",
        "renz_assistant/main.py",
        "renz_assistant/modules/audio.py",
        "renz_assistant/modules/nlp.py",
        "renz_assistant/modules/config.py",
        "renz_assistant/modules/device.py",
        "renz_assistant/modules/voice_recognition.py",
        "renz_assistant/modules/openrouter.py"
    ]
    
    all_files_present = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print_color("green", f"✅ {file_path} exists")
        else:
            print_color("red", f"❌ {file_path} is missing")
            all_files_present = False
    
    # Check if run_assistant.py is executable
    if os.path.exists("run_assistant.py"):
        if os.access("run_assistant.py", os.X_OK):
            print_color("green", "✅ run_assistant.py is executable")
        else:
            print_color("yellow", "⚠️ run_assistant.py is not executable. Run 'chmod +x run_assistant.py'")
    
    # Check configuration
    print("\nChecking configuration:")
    if os.path.exists("config.json"):
        print_color("green", "✅ Configuration file exists")
        try:
            import json
            with open("config.json", "r") as f:
                config = json.load(f)
            
            # Check OpenRouter API key
            if "openrouter" in config and "api_key" in config["openrouter"] and config["openrouter"]["api_key"]:
                print_color("green", "✅ OpenRouter API key is configured")
            else:
                print_color("yellow", "⚠️ OpenRouter API key is not configured")
            
            # Check voice recognition settings
            if "voice_recognition" in config:
                print_color("green", f"✅ Voice recognition engine: {config['voice_recognition'].get('engine', 'termux_api')}")
            else:
                print_color("yellow", "⚠️ Voice recognition settings not found")
            
        except Exception as e:
            print_color("red", f"❌ Error reading configuration: {e}")
    else:
        print_color("yellow", "⚠️ Configuration file does not exist. Run './run_assistant.py --config' to create it")
    
    # Summary
    print("\n=== Test Summary ===")
    if all_modules_installed and all_files_present:
        print_color("green", "✅ All required components are installed")
    else:
        print_color("red", "❌ Some required components are missing")
    
    if not termux_api_available:
        print_color("yellow", "⚠️ Termux API is not fully available. Some features may not work")
        print_color("yellow", "   Make sure Termux API app is installed and permissions are granted")
    
    print("\nRecommendations:")
    if not all_modules_installed:
        print_color("yellow", "- Run 'pip install -r requirements.txt' to install missing modules")
    
    if not all_files_present:
        print_color("yellow", "- Make sure you have downloaded the complete project")
    
    if not termux_api_available:
        print_color("yellow", "- Install Termux API app from the same source as your Termux app")
        print_color("yellow", "- Grant necessary permissions to Termux API in Android settings")
    
    print_color("cyan", "\nTest completed!")

if __name__ == "__main__":
    main()