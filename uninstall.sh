#!/bin/bash
# Uninstall script for Renz Assistant

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
print_color "red" "Uninstall Script"
echo ""

# Confirm uninstallation
print_color "red" "⚠️ WARNING: This will remove Renz Assistant and all associated data."
print_color "yellow" "Are you sure you want to uninstall Renz Assistant? (y/n): "
read confirm_uninstall
if [[ $confirm_uninstall != "y" && $confirm_uninstall != "Y" ]]; then
    print_color "green" "✅ Uninstallation cancelled."
    exit 0
fi

# Get current directory
CURRENT_DIR=$(pwd)

# Remove shortcut if exists
if [ -f ~/.shortcuts/RenzAssistant ]; then
    print_color "yellow" "🗑️ Removing shortcut..."
    rm ~/.shortcuts/RenzAssistant
    print_color "green" "✅ Shortcut removed"
fi

# Ask if user wants to keep configuration
print_color "yellow" "Do you want to keep your configuration files for future reinstallation? (y/n): "
read keep_config
if [[ $keep_config == "y" || $keep_config == "Y" ]]; then
    print_color "yellow" "📦 Backing up configuration..."
    mkdir -p ~/renz_backup
    
    # Copy configuration files
    if [ -f "config.json" ]; then
        cp config.json ~/renz_backup/
    fi
    
    # Copy data files
    for file in assistant_memory.json voice_profile.pkl usage_log.json notes.json reminders.json user_preferences.json learning_data.json personality_profiles.json; do
        if [ -f "$file" ]; then
            cp "$file" ~/renz_backup/
        fi
    done
    
    print_color "green" "✅ Configuration backed up to ~/renz_backup"
fi

# Remove virtual environment if exists
if [ -d "venv" ]; then
    print_color "yellow" "🗑️ Removing virtual environment..."
    rm -rf venv
    print_color "green" "✅ Virtual environment removed"
fi

# Ask if user wants to remove the entire directory
print_color "yellow" "Do you want to remove the entire Renz Assistant directory? (y/n): "
read remove_dir
if [[ $remove_dir == "y" || $remove_dir == "Y" ]]; then
    # Go up one directory
    cd ..
    
    # Get directory name
    DIR_NAME=$(basename "$CURRENT_DIR")
    
    print_color "yellow" "🗑️ Removing directory $DIR_NAME..."
    rm -rf "$DIR_NAME"
    print_color "green" "✅ Directory removed"
    
    print_color "green" "✅ Renz Assistant has been completely uninstalled."
else
    print_color "green" "✅ Renz Assistant files have been cleaned up, but the directory remains."
    print_color "yellow" "You can manually delete the directory if needed."
fi

print_color "blue" "Thank you for using Renz Assistant! If you're uninstalling due to an issue, please consider reporting it to help us improve."