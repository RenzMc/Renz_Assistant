#!/bin/bash
# Update script for Renz Assistant

# Print colored text
print_color() {
    case $1 in
        "red") echo -e "\e[31m$2\e[0m" ;;
        "green") echo -e "\e[32m$2\e[0m" ;;
        "yellow") echo -e "\e[33m$2\e[0m" ;;
        "blue") echo -e "\e[34m$2\e[0m" ;;
        "magenta") echo -e "\e[35m$2\e[0m" ;;
        "cyan") echo -e "\e[36m$2\e[0m" ;;
        *) echo "$2" ;;
    esac
}

# Welcome message
print_color "cyan" "
█▀█ █▀▀ █▄░█ ▀█   ▄▀█ █▀ █▀ █ █▀ ▀█▀ ▄▀█ █▄░█ ▀█▀
█▀▄ ██▄ █░▀█ █▄   █▀█ ▄█ ▄█ █ ▄█ ░█░ █▀█ █░▀█ ░█░
"
print_color "blue" "Update Script"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_color "yellow" "📦 Installing git..."
    pkg install -y git || { print_color "red" "❌ Failed to install git"; exit 1; }
fi

# Check if this is a git repository
if [ ! -d ".git" ]; then
    print_color "red" "❌ This is not a git repository. Please run this script from the root of the Renz Assistant repository."
    exit 1
fi

# Backup configuration
print_color "yellow" "📦 Backing up configuration..."
if [ -f "config.json" ]; then
    cp config.json config.json.backup
    print_color "green" "✅ Configuration backed up to config.json.backup"
else
    print_color "yellow" "⚠️ No configuration file found to backup"
fi

# Pull latest changes
print_color "yellow" "📦 Pulling latest changes from repository..."
git pull || { print_color "red" "❌ Failed to pull latest changes"; exit 1; }

# Update packages
print_color "yellow" "📦 Updating package lists..."
pkg update -y || { print_color "red" "❌ Failed to update package lists"; exit 1; }

# Update Python dependencies
print_color "yellow" "📦 Updating Python dependencies..."
pip install -r requirements.txt --upgrade || { print_color "red" "❌ Failed to update Python dependencies"; exit 1; }

# Make run script executable
print_color "yellow" "🔧 Making run script executable..."
chmod +x run_assistant.py || { print_color "red" "❌ Failed to make run script executable"; exit 1; }

# Restore configuration
if [ -f "config.json.backup" ]; then
    print_color "yellow" "📦 Restoring configuration..."
    cp config.json.backup config.json
    print_color "green" "✅ Configuration restored"
fi

# Run configuration
print_color "yellow" "🔧 Would you like to run the configuration to update settings? (y/n): "
read run_config
if [[ $run_config == "y" || $run_config == "Y" ]]; then
    print_color "cyan" "🔧 Running configuration..."
    ./run_assistant.py --config || { print_color "red" "❌ Configuration failed"; exit 1; }
fi

# Update complete
print_color "green" "✅ Renz Assistant update complete!"
print_color "cyan" "To start the assistant, run: ./run_assistant.py"
print_color "cyan" "To configure the assistant, run: ./run_assistant.py --config"