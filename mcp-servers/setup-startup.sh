#!/bin/bash

# Setup Startup Script
# This script adds the Perplexity autostart to system startup

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Setup Perplexity Autostart ===${NC}"

# Get absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AUTOSTART_SCRIPT="$SCRIPT_DIR/perplexity-autostart.js"

if [ ! -f "$AUTOSTART_SCRIPT" ]; then
  echo -e "${RED}Error: Autostart script not found at $AUTOSTART_SCRIPT${NC}"
  exit 1
fi

# Make sure the script is executable
chmod +x "$AUTOSTART_SCRIPT"

# Determine OS type
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS - Setup launchd plist
  PLIST_PATH="$HOME/Library/LaunchAgents/com.cursor.perplexity.plist"
  
  echo -e "${GREEN}Setting up autostart for macOS...${NC}"
  
  # Create the plist file
  cat > "$PLIST_PATH" << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.cursor.perplexity</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/node</string>
    <string>${AUTOSTART_SCRIPT}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>StandardOutPath</key>
  <string>${SCRIPT_DIR}/perplexity-launchd.log</string>
  <key>StandardErrorPath</key>
  <string>${SCRIPT_DIR}/perplexity-launchd.log</string>
</dict>
</plist>
EOL
  
  # Load the plist
  launchctl load "$PLIST_PATH"
  
  echo -e "${GREEN}Autostart service installed and loaded.${NC}"
  echo -e "${YELLOW}The service will start automatically when you log in.${NC}"
  
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  # Linux - Setup systemd user service
  SERVICE_PATH="$HOME/.config/systemd/user/perplexity.service"
  SERVICE_DIR="$(dirname "$SERVICE_PATH")"
  
  echo -e "${GREEN}Setting up autostart for Linux...${NC}"
  
  # Create the service directory if it doesn't exist
  mkdir -p "$SERVICE_DIR"
  
  # Create the service file
  cat > "$SERVICE_PATH" << EOL
[Unit]
Description=Perplexity API Service for Cursor IDE
After=network.target

[Service]
ExecStart=/usr/bin/node ${AUTOSTART_SCRIPT}
Restart=on-failure
StandardOutput=file:${SCRIPT_DIR}/perplexity-systemd.log
StandardError=file:${SCRIPT_DIR}/perplexity-systemd.log

[Install]
WantedBy=default.target
EOL
  
  # Enable and start the service
  systemctl --user enable perplexity.service
  systemctl --user start perplexity.service
  
  echo -e "${GREEN}Autostart service installed and started.${NC}"
  echo -e "${YELLOW}The service will start automatically when you log in.${NC}"
  
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* ]]; then
  # Windows - Setup task scheduler
  echo -e "${GREEN}Setting up autostart for Windows...${NC}"
  
  # Create a batch script to run the autostart script
  BAT_PATH="$SCRIPT_DIR/perplexity-autostart.bat"
  
  cat > "$BAT_PATH" << EOL
@echo off
cd /d "${SCRIPT_DIR}"
node perplexity-autostart.js > perplexity-autostart.log 2>&1
EOL
  
  # Create a vbs script to run the batch file without showing a window
  VBS_PATH="$SCRIPT_DIR/perplexity-autostart.vbs"
  
  cat > "$VBS_PATH" << EOL
CreateObject("Wscript.Shell").Run """${BAT_PATH}""", 0, False
EOL
  
  # Add to startup folder
  STARTUP_FOLDER="$APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
  SHORTCUT_PATH="$STARTUP_FOLDER\PerplexityAutostart.lnk"
  
  echo -e "${YELLOW}To complete setup on Windows:${NC}"
  echo -e "1. Copy $VBS_PATH to your startup folder:"
  echo -e "   $STARTUP_FOLDER"
  echo -e "2. Or run the following command to create a shortcut:"
  echo -e "   powershell.exe -Command \"$SHORTCUT = (New-Object -ComObject WScript.Shell).CreateShortcut('$SHORTCUT_PATH'); $SHORTCUT.TargetPath = '$VBS_PATH'; $SHORTCUT.Save()\""
  
else
  # Unknown OS
  echo -e "${YELLOW}Autostart setup not available for your OS.${NC}"
  echo -e "Please add the following command to your startup items manually:"
  echo -e "  node $AUTOSTART_SCRIPT"
fi

# Regardless of the OS, add to shell profile for IDE startup (works with Cursor terminal)
# Determine which shell profile to use
if [ -f "$HOME/.bash_profile" ]; then
  PROFILE="$HOME/.bash_profile"
elif [ -f "$HOME/.profile" ]; then
  PROFILE="$HOME/.profile"
elif [ -f "$HOME/.bashrc" ]; then
  PROFILE="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
  PROFILE="$HOME/.zshrc"
else
  PROFILE="$HOME/.profile"
  touch "$PROFILE"
fi

# Add to profile if not already there
if ! grep -q "perplexity-autostart.js" "$PROFILE"; then
  echo -e "${GREEN}Adding autostart to shell profile at $PROFILE...${NC}"
  
  echo "" >> "$PROFILE"
  echo "# Perplexity API Bridge autostart for Cursor IDE" >> "$PROFILE"
  echo "if [ -f \"$AUTOSTART_SCRIPT\" ]; then" >> "$PROFILE"
  echo "  node \"$AUTOSTART_SCRIPT\"" >> "$PROFILE"
  echo "fi" >> "$PROFILE"
  
  echo -e "${GREEN}Added to shell profile successfully.${NC}"
else
  echo -e "${YELLOW}Autostart already in shell profile.${NC}"
fi

# Start the service immediately
echo -e "${GREEN}Starting Perplexity service now...${NC}"
node "$AUTOSTART_SCRIPT"

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}Please see CURSOR-INTEGRATION.md for usage instructions.${NC}" 