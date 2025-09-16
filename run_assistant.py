#!/usr/bin/env python3
"""
Entry point script to run Renz Assistant
"""
import os
import sys
import argparse
from renz_assistant.main import RenzAssistant
from renz_assistant.modules.config import Config

def main():
    """Main entry point with command line arguments"""
    parser = argparse.ArgumentParser(description="Renz Assistant - Advanced Voice Assistant for Termux")
    parser.add_argument("--config", "-c", action="store_true", help="Run configuration setup")
    parser.add_argument("--base-path", "-p", default=".", help="Base path for data files")
    args = parser.parse_args()
    
    # Ensure base path exists
    if not os.path.exists(args.base_path):
        os.makedirs(args.base_path)
    
    # Run configuration if requested
    if args.config:
        print("🔧 Running Renz Assistant Configuration")
        config = Config(os.path.join(args.base_path, "config.json"))
        config.interactive_setup()
        print("✅ Configuration complete!")
        sys.exit(0)
    
    # Run the assistant
    assistant = RenzAssistant(base_path=args.base_path)
    assistant.run()

if __name__ == "__main__":
    main()