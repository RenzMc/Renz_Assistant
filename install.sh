#!/bin/bash
# Installation script for Renz Assistant

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

# Check if running in Termux
if [ -d "/data/data/com.termux" ]; then
    print_color "green" "✅ Running in Termux environment"
    IS_TERMUX=true
else
    print_color "yellow" "⚠️ Not running in Termux. Some features may not work correctly."
    IS_TERMUX=false
fi

# Welcome message
print_color "cyan" "
█▀█ █▀▀ █▄░█ ▀█   ▄▀█ █▀ █▀ █ █▀ ▀█▀ ▄▀█ █▄░█ ▀█▀
█▀▄ ██▄ █░▀█ █▄   █▀█ ▄█ ▄█ █ ▄█ ░█░ █▀█ █░▀█ ░█░
"
print_color "blue" "Advanced Voice Assistant for Termux"
print_color "blue" "Installation Script"
echo ""

if [ "$IS_TERMUX" = true ]; then
    # Update package lists
    print_color "yellow" "📦 Updating package lists..."
    pkg update -y || { print_color "red" "❌ Failed to update package lists"; exit 1; }

    # Install required system packages
    print_color "yellow" "📦 Installing required system packages..."
    pkg install -y python ffmpeg termux-api || { print_color "red" "❌ Failed to install required packages"; exit 1; }

    # Install Python dependencies via pip (lightweight, pure Python)
    print_color "yellow" "📦 Installing Python dependencies..."
    pip install -r requirements.txt || { print_color "red" "❌ Failed to install Python dependencies"; exit 1; }
else
    print_color "yellow" "📦 Installing Python dependencies..."
    pip install -r requirements.txt || { print_color "red" "❌ Failed to install Python dependencies"; exit 1; }
fi

# Make run script executable
print_color "yellow" "🔧 Making run script executable..."
chmod +x run_assistant.py || { print_color "red" "❌ Failed to make run script executable"; exit 1; }

if [ "$IS_TERMUX" = true ]; then
    # Setup storage access
    print_color "yellow" "🔧 Setting up storage access..."
    termux-setup-storage || print_color "yellow" "⚠️ Storage access setup may require manual confirmation"

    # Check for Termux API
    if command -v termux-battery-status &> /dev/null; then
        print_color "green" "✅ Termux API is installed"
    else
        print_color "red" "❌ Termux API is not installed."
        print_color "yellow" "Install it with: pkg install termux-api"
        print_color "yellow" "Also install the Termux:API app from the same source as your Termux app."
    fi
fi

# Run configuration
print_color "yellow" "🔧 Would you like to run the configuration now? (y/n): "
read run_config
if [[ $run_config == "y" || $run_config == "Y" ]]; then
    print_color "cyan" "🔧 Running configuration..."
    ./run_assistant.py --config || { print_color "red" "❌ Configuration failed"; exit 1; }
fi

if [ "$IS_TERMUX" = true ]; then
    # Create desktop shortcut
    print_color "yellow" "🔧 Would you like to create a shortcut to launch Renz Assistant? (y/n): "
    read create_shortcut
    if [[ $create_shortcut == "y" || $create_shortcut == "Y" ]]; then
        mkdir -p ~/.shortcuts
        cat > ~/.shortcuts/RenzAssistant << EOF
#!/bin/bash
cd $(pwd)
./run_assistant.py
EOF
        chmod +x ~/.shortcuts/RenzAssistant
        print_color "green" "✅ Shortcut created. You can find it in the Termux widget."
    fi
fi

# Installation complete
print_color "green" "✅ Renz Assistant installation complete!"
print_color "cyan" "To start the assistant, run: ./run_assistant.py"
print_color "cyan" "To configure the assistant, run: ./run_assistant.py --config"
if [ "$IS_TERMUX" = true ]; then
    print_color "yellow" "Make sure to grant all necessary permissions to Termux API app in Android settings."
fi
