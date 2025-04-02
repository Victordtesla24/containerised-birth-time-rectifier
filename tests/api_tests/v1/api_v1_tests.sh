#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}       V1 API ENDPOINT TESTING SCRIPT         ${NC}"
echo -e "${BLUE}===============================================${NC}"

# API Gateway URL
API_URL="http://localhost:3001"

# Function to execute a test and report results
test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4

    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo -e "${YELLOW}Endpoint: $endpoint${NC}"
    echo -e "${YELLOW}Method: $method${NC}"

    # Build curl command
    local cmd="curl -s -w '\n%{http_code}' -X $method"

    # Add headers and data if applicable
    if [ "$method" == "POST" ] || [ "$method" == "PUT" ]; then
        cmd="$cmd -H 'Content-Type: application/json'"
        if [ -n "$data" ]; then
            cmd="$cmd -d '$data'"
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
        return 0
    else
        echo -e "${RED}FAILED (Status $status_code)${NC}"
        echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
        return 1
    fi
}

# Test v1 endpoints
echo -e "\n${BLUE}=== Testing API v1 Endpoints ===${NC}"

# Health check
test_endpoint "/api/v1/health" "GET" "" "Health Check"

# Session initialization
SESSION_RESPONSE=$(curl -s $API_URL/api/v1/session/init)
echo -e "\n${YELLOW}Session initialization response:${NC}"
echo "$SESSION_RESPONSE" | python -m json.tool 2>/dev/null || echo "$SESSION_RESPONSE"
SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}Got session ID: $SESSION_ID${NC}"
else
    echo -e "${RED}Failed to get session ID${NC}"
    SESSION_ID="test-session-$(date +%s)"
    echo -e "${YELLOW}Using fallback session ID: $SESSION_ID${NC}"
fi

# Test geocode endpoint
test_endpoint "/api/v1/geocode?query=New%20York" "GET" "" "Geocode"

# Test chart validation
test_endpoint "/api/v1/chart/validate" "POST" '{"birth_details":{"birth_date":"1990-01-01","birth_time":"12:00:00","latitude":40.7128,"longitude":-74.0060,"timezone":"America/New_York"}}' "Chart Validation"

# Test chart generation
GENERATE_DATA="{\"birth_details\":{\"birth_date\":\"1990-01-01\",\"birth_time\":\"12:00:00\",\"latitude\":40.7128,\"longitude\":-74.0060,\"timezone\":\"America/New_York\"},\"session_id\":\"$SESSION_ID\"}"
CHART_RESPONSE=$(curl -s -X POST $API_URL/api/v1/chart/generate -H "Content-Type: application/json" -d "$GENERATE_DATA")
echo -e "\n${YELLOW}Chart generation response:${NC}"
echo "$CHART_RESPONSE" | python -m json.tool 2>/dev/null || echo "$CHART_RESPONSE"
CHART_ID=$(echo $CHART_RESPONSE | grep -o '"chart_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')

if [ -n "$CHART_ID" ]; then
    echo -e "${GREEN}Got chart ID: $CHART_ID${NC}"
else
    echo -e "${RED}Failed to get chart ID${NC}"
    CHART_ID="test-chart-$(date +%s)"
    echo -e "${YELLOW}Using fallback chart ID: $CHART_ID${NC}"
fi

# Test questionnaire
test_endpoint "/api/v1/questionnaire?chart_id=$CHART_ID&session_id=$SESSION_ID" "GET" "" "Questionnaire"

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}       API TESTING COMPLETE                    ${NC}"
echo -e "${BLUE}===============================================${NC}"
