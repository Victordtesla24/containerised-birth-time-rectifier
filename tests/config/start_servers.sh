#!/bin/bash
# start_servers.sh - Script to start both API Gateway and AI Service servers
# Usage: ./start_servers.sh

# Set environment variables
export PYTHONPATH=$(pwd)

# Create required directories
mkdir -p logs
mkdir -p ai_service/sessions

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Birth Time Rectifier - Server Starter ===${NC}"
echo -e "${YELLOW}Starting servers...${NC}"

# Kill any existing instances
echo -e "${YELLOW}Checking for existing server processes...${NC}"
pkill -f "uvicorn ai_service.main:app" || true
pkill -f "uvicorn api_gateway.main:app" || true
sleep 1

# Function to start a server in a new terminal
start_server() {
    local server_type=$1
    local command=$2
    local log_file=$3

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e "tell application \"Terminal\" to do script \"cd $(pwd) && $command\""
        echo -e "${GREEN}Started $server_type in a new Terminal window${NC}"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v gnome-terminal &> /dev/null; then
            # Linux with Gnome Terminal
            gnome-terminal -- bash -c "cd $(pwd) && $command; exec bash"
        elif command -v xterm &> /dev/null; then
            # Linux with xterm
            xterm -e "cd $(pwd) && $command" &
        else
            # Fallback to background process with log
            echo -e "${YELLOW}No suitable terminal found. Running $server_type in background...${NC}"
            cd $(pwd) && $command > $log_file 2>&1 &
        fi
        echo -e "${GREEN}Started $server_type${NC}"
    else
        # Fallback for other systems
        echo -e "${YELLOW}Unsupported OS. Running $server_type in background...${NC}"
        cd $(pwd) && $command > $log_file 2>&1 &
    fi
}

# Start AI Service
AI_SERVICE_CMD="PYTHONPATH=$PYTHONPATH python -m uvicorn ai_service.main:app --host 0.0.0.0 --port 8000 --reload"
start_server "AI Service" "$AI_SERVICE_CMD" "logs/ai_service.log"

# Wait a moment before starting the API Gateway
sleep 2

# Start API Gateway
API_GATEWAY_CMD="PYTHONPATH=$PYTHONPATH python -m uvicorn api_gateway.main:app --host 0.0.0.0 --port 3000 --reload"
start_server "API Gateway" "$API_GATEWAY_CMD" "logs/api_gateway.log"

echo -e "${GREEN}Both servers started!${NC}"
echo -e "${BLUE}AI Service: http://localhost:8000${NC}"
echo -e "${BLUE}API Gateway: http://localhost:3000${NC}"
echo
echo -e "${YELLOW}Testing endpoints...${NC}"

# Wait for servers to be fully up
sleep 5

# Test session initialization
echo -e "${BLUE}Testing session initialization...${NC}"
curl -s -v http://localhost:3000/api/session/init

# Test geocoding endpoint
echo -e "\n\n${BLUE}Testing geocoding endpoint...${NC}"
SESSION_ID=$(curl -s http://localhost:3000/api/session/init | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)
curl -s -v -X POST -H "Content-Type: application/json" -H "X-Session-ID: $SESSION_ID" -d '{"query": "NYC"}' http://localhost:3000/api/geocode

echo -e "\n\n${GREEN}Server testing complete!${NC}"
echo -e "${YELLOW}Servers are running in separate terminal windows.${NC}"
echo -e "${YELLOW}Press Ctrl+C in those windows to stop the servers.${NC}"
