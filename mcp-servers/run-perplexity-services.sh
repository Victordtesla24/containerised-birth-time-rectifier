#!/bin/bash

# Perplexity Services Runner
# This script starts the Perplexity API bridge service

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BRIDGE_SCRIPT="$SCRIPT_DIR/direct-perplexity-bridge.js"
PID_FILE="$SCRIPT_DIR/perplexity-bridge.pid"
LOG_FILE="$SCRIPT_DIR/perplexity-bridge.log"

echo -e "${BLUE}=== Starting Perplexity Services ===${NC}"

# Check if the bridge is already running
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if ps -p $PID > /dev/null; then
    echo -e "${YELLOW}Perplexity bridge is already running with PID $PID${NC}"
    exit 0
  else
    echo -e "${YELLOW}Removing stale PID file${NC}"
    rm -f "$PID_FILE"
  fi
fi

# Start the Perplexity bridge service
echo -e "${GREEN}Starting Perplexity API bridge...${NC}"
node "$BRIDGE_SCRIPT" > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"
echo -e "${GREEN}Perplexity bridge started with PID $PID${NC}"

# Configure Cursor MCP
echo -e "${GREEN}Configuring Cursor MCP...${NC}"
node "$SCRIPT_DIR/cursor-mcp-setup.js" > /dev/null

echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${YELLOW}See CURSOR-INTEGRATION.md for usage instructions.${NC}" 