#!/bin/bash

# Birth Time Rectifier - Session Initialization Script
# This script verifies services are running and initializes a session

# Define colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API Base URL
API_BASE_URL="http://localhost:8000"

# Script paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_SCRIPT="$SCRIPT_DIR/tests/shell_scripts/server/run_both_servers.sh"

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}  BIRTH TIME RECTIFIER - SESSION INIT TEST${NC}"
echo -e "${GREEN}===============================================${NC}"
echo -e "${YELLOW}Testing against API: $API_BASE_URL${NC}"

# Check if the API servers are running
echo -e "\n${BLUE}Checking if API servers are running...${NC}"
if curl -s -m 2 "$API_BASE_URL/api/health" > /dev/null; then
    echo -e "${GREEN}✓ API servers are running!${NC}"
else
    echo -e "${RED}✗ API servers are not running.${NC}"
    echo -e "${YELLOW}Attempting to start servers...${NC}"

    if [[ -f "$SERVER_SCRIPT" ]]; then
        echo -e "Executing: $SERVER_SCRIPT"
        chmod +x "$SERVER_SCRIPT"
        (cd "$SCRIPT_DIR" && "$SERVER_SCRIPT") &

        # Store the server process ID
        SERVER_PID=$!
        echo -e "${YELLOW}Server process started with PID $SERVER_PID${NC}"

        # Wait for servers to start (up to 30 seconds)
        echo -e "Waiting for servers to start..."
        for i in {1..30}; do
            if curl -s -m 2 "$API_BASE_URL/api/health" > /dev/null; then
                echo -e "${GREEN}✓ Servers started successfully!${NC}"
                break
            fi
            echo -n "."
            sleep 1
            if [ $i -eq 30 ]; then
                echo -e "\n${RED}Failed to start servers after 30 seconds.${NC}"
                echo -e "${RED}Please start the servers manually with:${NC}"
                echo -e "${YELLOW}cd $SCRIPT_DIR && $SERVER_SCRIPT${NC}"
                exit 1
            fi
        done
    else
        echo -e "${RED}Server script not found at: $SERVER_SCRIPT${NC}"
        echo -e "${RED}Please start the servers manually.${NC}"
        exit 1
    fi
fi

# Initialize Session
echo -e "\n${BLUE}SEQUENCE 1: Initializing Session${NC}"
echo -e "${BLUE}------------------------------${NC}"
echo -e "${YELLOW}API ENDPOINT REQUIREMENTS:${NC}"
echo -e "${YELLOW}- Endpoint: /api/session/init${NC}"
echo -e "${YELLOW}- Method: GET${NC}"
echo -e "${YELLOW}- Response Format: {\"session_id\":\"uuid\",\"expires_at\":timestamp,\"status\":\"active\"}${NC}"

# Test using verbose output first
echo -e "\n${YELLOW}Testing with verbose output:${NC}"
curl -v "$API_BASE_URL/api/session/init"
echo -e "\n"

# Now try the normal command
echo -e "${YELLOW}Executing: curl \"$API_BASE_URL/api/session/init\"${NC}"
RESPONSE=$(curl -s "$API_BASE_URL/api/session/init")
echo -e "${YELLOW}Raw response:${NC}\n$RESPONSE"

echo -e "\n${GREEN}Session initialization test complete.${NC}"
echo -e "${YELLOW}Please examine the API response above.${NC}"
exit 0
