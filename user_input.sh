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

# Extract and save the session ID
SESSION_ID=$(echo $RESPONSE | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)
if [[ -n "$SESSION_ID" ]]; then
    echo -e "\n${GREEN}✓ Session ID extracted: ${SESSION_ID}${NC}"
else
    echo -e "\n${RED}✗ Failed to extract session ID from response.${NC}"
    echo -e "${RED}Please check if the API is functioning correctly.${NC}"
    exit 1
fi

# Geocode API
echo -e "\n${BLUE}SEQUENCE 2: Geocoding${NC}"
echo -e "${BLUE}------------------------------${NC}"
echo -e "${YELLOW}API ENDPOINT REQUIREMENTS:${NC}"
echo -e "${YELLOW}- Endpoint: /api/geocode?query=<location>&limit=<limit>&include_timezone=<true/false>${NC}"
echo -e "${YELLOW}- Method: GET${NC}"
echo -e "${YELLOW}- Response Format: {\"success\":true,\"query\":\"<location>\",\"count\":n,\"results\":[...]}${NC}"

# User input for birth details
echo -e "\n${BLUE}Please enter your birth details:${NC}"
read -p "Birth Date (YYYY-MM-DD): " BIRTH_DATE
read -p "Birth Time (HH:MM:SS): " BIRTH_TIME
read -p "Birth Place (e.g., NYC, London, Tokyo): " BIRTH_PLACE

# Validate inputs
if [[ ! $BIRTH_DATE =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo -e "${RED}Invalid date format. Please use YYYY-MM-DD format.${NC}"
    exit 1
fi

if [[ ! $BIRTH_TIME =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
    echo -e "${RED}Invalid time format. Please use HH:MM:SS format.${NC}"
    exit 1
fi

if [[ -z "$BIRTH_PLACE" ]]; then
    echo -e "${RED}Birth place cannot be empty.${NC}"
    exit 1
fi

# Construct the geocode API URL
GEOCODE_URL="$API_BASE_URL/api/geocode?query=$(echo $BIRTH_PLACE | sed 's/ /%20/g')&limit=5&include_timezone=true"

echo -e "\n${YELLOW}Executing: curl \"$GEOCODE_URL\"${NC}"
GEOCODE_RESPONSE=$(curl -s "$GEOCODE_URL")
echo -e "${YELLOW}Geocode response:${NC}\n$GEOCODE_RESPONSE"

# Check if the geocode was successful
if echo "$GEOCODE_RESPONSE" | grep -q '"success":true'; then
    echo -e "\n${GREEN}✓ Geocoding successful!${NC}"

    # Extract the first result's coordinates for use in the next step
    LATITUDE=$(echo $GEOCODE_RESPONSE | grep -o '"latitude":[^,]*' | head -1 | cut -d':' -f2)
    LONGITUDE=$(echo $GEOCODE_RESPONSE | grep -o '"longitude":[^,]*' | head -1 | cut -d':' -f2)

    if [[ -n "$LATITUDE" && -n "$LONGITUDE" ]]; then
        echo -e "${GREEN}✓ Coordinates extracted: Latitude=${LATITUDE}, Longitude=${LONGITUDE}${NC}"
    else
        echo -e "${YELLOW}⚠ Could not extract coordinates. You may need to select from the results.${NC}"
    fi
else
    echo -e "\n${RED}✗ Geocoding failed. Please check your input and try again.${NC}"
fi

echo -e "\n${GREEN}Session initialization and geocoding test complete.${NC}"
echo -e "${YELLOW}Saved session ID: ${SESSION_ID} for future API calls.${NC}"
echo -e "${YELLOW}Birth details: Date=${BIRTH_DATE}, Time=${BIRTH_TIME}, Place=${BIRTH_PLACE}${NC}"
echo -e "${YELLOW}Awaiting further instructions...${NC}"
exit 0
