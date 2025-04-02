#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API Gateway URL
API_URL="http://localhost:3001"
AI_SERVICE_URL="http://localhost:8001"

# Session storage
SESSION_ID=""
CHART_ID=""

# User birth details
BIRTH_DATE=""
BIRTH_TIME=""
LOCATION_QUERY=""
LATITUDE=""
LONGITUDE=""
TIMEZONE=""

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    BIRTH TIME RECTIFIER API TESTING SUITE    ${NC}"
echo -e "${BLUE}===============================================${NC}"

# Function to check if a server is running
check_server() {
    local url=$1
    local name=$2

    echo -e "\n${YELLOW}Checking if $name is running...${NC}"

    if curl -s --connect-timeout 3 "$url/api/v1/health" > /dev/null; then
        echo -e "${GREEN}✅ $name is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $name is not running${NC}"
        return 1
    fi
}

# Function to execute a test and report results
test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4
    local session_header=""

    if [ -n "$SESSION_ID" ]; then
        session_header="-H 'X-Session-ID: $SESSION_ID'"
    fi

    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo -e "${YELLOW}Endpoint: $endpoint${NC}"
    echo -e "${YELLOW}Method: $method${NC}"

    if [ -n "$data" ]; then
        echo -e "${YELLOW}Data: $data${NC}"
    fi

    # Build curl command
    local cmd="curl -s -w '\n%{http_code}' -X $method"

    # Add headers and data if applicable
    if [ "$method" == "POST" ] || [ "$method" == "PUT" ]; then
        cmd="$cmd -H 'Content-Type: application/json'"
        if [ -n "$session_header" ]; then
            cmd="$cmd $session_header"
        fi
        if [ -n "$data" ]; then
            cmd="$cmd -d '$data'"
        fi
    else
        if [ -n "$session_header" ]; then
            cmd="$cmd $session_header"
        fi
    fi

    # Add the endpoint
    cmd="$cmd $API_URL$endpoint"

    echo -e "${YELLOW}Command: $cmd${NC}"

    # Execute curl and capture response and status code
    response=$(eval $cmd)
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    # Check if status code indicates success (2xx)
    if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
        echo -e "${GREEN}SUCCESS (Status $status_code)${NC}"
        echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
        # Return body for parsing, but filter out any console output
        echo "$body" | grep -v "SUCCESS" | grep -v "Command" | grep -v "Method" | grep -v "Endpoint"
        return 0
    else
        echo -e "${RED}FAILED (Status $status_code)${NC}"
        echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
        return 1
    fi
}

# Step 1: Check if servers are running
check_server "$API_URL" "API Gateway" || { echo -e "${RED}API Gateway must be running. Exiting.${NC}"; exit 1; }
check_server "$AI_SERVICE_URL" "AI Service" || { echo -e "${RED}AI Service must be running. Exiting.${NC}"; exit 1; }

# Step 2: Test API health
echo -e "\n${BLUE}=== Testing API Health ===${NC}"
test_endpoint "/api/v1/health" "GET" "" "API Gateway Health Check"

# Step 3: Initialize a session
echo -e "\n${BLUE}=== Initializing Session ===${NC}"
SESSION_RESPONSE=$(test_endpoint "/api/v1/session/init" "GET" "" "Session Initialization")
SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}Session created with ID: $SESSION_ID${NC}"
else
    echo -e "${RED}Failed to create session${NC}"
    SESSION_ID="fallback-session-$(date +%s)"
    echo -e "${YELLOW}Using fallback session ID: $SESSION_ID${NC}"
fi

# Step 4: Get user input for birth details
echo -e "\n${BLUE}=== Enter Birth Details ===${NC}"
read -p "Enter birth date (YYYY-MM-DD): " BIRTH_DATE
read -p "Enter birth time (HH:MM:SS): " BIRTH_TIME
read -p "Enter birth location (e.g., New York, USA): " LOCATION_QUERY

# Step 5: Test geocoding
echo -e "\n${BLUE}=== Testing Geocode API ===${NC}"
GEOCODE_ENDPOINT="/api/v1/geocode?query=$(echo "$LOCATION_QUERY" | sed 's/ /%20/g')"
GEOCODE_RESPONSE=$(test_endpoint "$GEOCODE_ENDPOINT" "GET" "" "Geocode Location: $LOCATION_QUERY")

# Extract coordinates from response
LATITUDE=$(echo "$GEOCODE_RESPONSE" | grep -o '"latitude":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
LONGITUDE=$(echo "$GEOCODE_RESPONSE" | grep -o '"longitude":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
TIMEZONE=$(echo "$GEOCODE_RESPONSE" | grep -o '"timezone":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')

if [ -n "$LATITUDE" ] && [ -n "$LONGITUDE" ]; then
    echo -e "${GREEN}Successfully retrieved coordinates:${NC}"
    echo -e "${GREEN}Latitude: $LATITUDE${NC}"
    echo -e "${GREEN}Longitude: $LONGITUDE${NC}"
    echo -e "${GREEN}Timezone: $TIMEZONE${NC}"
else
    echo -e "${RED}Failed to retrieve coordinates${NC}"
    # Fallback to New York coordinates
    LATITUDE="40.7128"
    LONGITUDE="-74.0060"
    TIMEZONE="America/New_York"
    echo -e "${YELLOW}Using fallback coordinates for New York:${NC}"
    echo -e "${YELLOW}Latitude: $LATITUDE${NC}"
    echo -e "${YELLOW}Longitude: $LONGITUDE${NC}"
    echo -e "${YELLOW}Timezone: $TIMEZONE${NC}"
fi

# Step 6: Validate birth details
echo -e "\n${BLUE}=== Validating Birth Details ===${NC}"
# Create birth_details object for validation
VALIDATE_DATA="{\"birth_date\":\"$BIRTH_DATE\",\"birth_time\":\"$BIRTH_TIME\",\"latitude\":$LATITUDE,\"longitude\":$LONGITUDE,\"timezone\":\"$TIMEZONE\"}"
test_endpoint "/api/v1/chart/validate" "POST" "$VALIDATE_DATA" "Validate Birth Details"

# Step 7: Generate chart
echo -e "\n${BLUE}=== Generating Birth Chart ===${NC}"
# Create birth_details object for chart generation
GENERATE_DATA="{\"birth_date\":\"$BIRTH_DATE\",\"birth_time\":\"$BIRTH_TIME\",\"latitude\":$LATITUDE,\"longitude\":$LONGITUDE,\"timezone\":\"$TIMEZONE\",\"session_id\":\"$SESSION_ID\",\"verify_with_openai\":true}"
CHART_RESPONSE=$(test_endpoint "/api/v1/chart/generate" "POST" "$GENERATE_DATA" "Generate Birth Chart")

# Fix chart ID extraction to get only the chart_id value from the JSON response
CHART_ID=$(echo "$CHART_RESPONSE" | grep -o '"chart_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

if [ -n "$CHART_ID" ]; then
    echo -e "${GREEN}Chart generated with ID: $CHART_ID${NC}"
else
    echo -e "${RED}Failed to generate chart${NC}"
    CHART_ID="fallback-chart-$(date +%s)"
    echo -e "${YELLOW}Using fallback chart ID: $CHART_ID${NC}"
fi

# Step 8: Retrieve chart - fix endpoint construction
echo -e "\n${BLUE}=== Retrieving Chart Details ===${NC}"
CHART_ENDPOINT="/api/v1/chart/$CHART_ID"
test_endpoint "$CHART_ENDPOINT" "GET" "" "Retrieve Chart Details"

# Step 9: Get Questionnaire
echo -e "\n${BLUE}=== Retrieving Questionnaire ===${NC}"
QUESTIONNAIRE_ENDPOINT="/api/v1/questionnaire?chart_id=$CHART_ID"
test_endpoint "$QUESTIONNAIRE_ENDPOINT" "GET" "" "Get Questionnaire"

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}       API TESTING COMPLETE                    ${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "\n${YELLOW}Test Summary:${NC}"
echo -e "Session ID: $SESSION_ID"
echo -e "Chart ID: $CHART_ID"
echo -e "Birth Date: $BIRTH_DATE"
echo -e "Birth Time: $BIRTH_TIME"
echo -e "Location: $LOCATION_QUERY"
echo -e "Coordinates: $LATITUDE, $LONGITUDE"
echo -e "Timezone: $TIMEZONE"

echo -e "\n${YELLOW}Next steps in sequence diagram:${NC}"
echo -e "1. Answer questionnaire questions"
echo -e "2. Submit birth time rectification request"
echo -e "3. Compare charts"
echo -e "4. Export chart"

echo -e "\n${GREEN}To continue testing with the above data, run:${NC}"
echo -e "cd tests/shell_scripts/client_scripts"
echo -e "./advanced_api_tester.sh --session=$SESSION_ID --chart=$CHART_ID"
