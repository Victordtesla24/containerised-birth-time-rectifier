#!/bin/bash

# Test script for AI model integration
# This script tests the AI model integration by making calls to the test endpoints

# Set API URL
API_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if the OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Warning: OPENAI_API_KEY environment variable is not set.${NC}"
    echo -e "${RED}Some tests may fail. Set it with: export OPENAI_API_KEY=your_key_here${NC}"
    echo ""
fi

# Function to make API calls
call_api() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4

    echo -e "${BLUE}Testing: ${description}${NC}"
    echo "Endpoint: $endpoint"
    echo "Method: $method"
    if [ ! -z "$data" ]; then
        echo "Data: $data"
    fi

    if [ "$method" == "GET" ]; then
        curl -s -X GET "${API_URL}${endpoint}"
    else
        curl -s -X $method "${API_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi

    echo -e "\n${GREEN}Test complete${NC}"
    echo "----------------------------------------"
}

# Test 1: Check if API is running
echo -e "${BLUE}Checking if API is running...${NC}"
HEALTH_RESPONSE=$(curl -s "${API_URL}/api/health")

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo -e "${GREEN}API is running successfully!${NC}"
else
    echo -e "${RED}API is not running or health check failed. Start the API first.${NC}"
    exit 1
fi
echo "----------------------------------------"

# Test 2: Model routing for rectification task (should use o1-preview)
echo -e "${BLUE}Testing model routing for rectification task...${NC}"
call_api "/api/ai/test_model_routing" "POST" '{"task_type": "rectification", "prompt": "Test prompt for rectification", "max_tokens": 50}' "Rectification task routing (should use o1-preview)"

# Test 3: Model routing for explanation task (should use gpt-4-turbo)
echo -e "${BLUE}Testing model routing for explanation task...${NC}"
call_api "/api/ai/test_model_routing" "POST" '{"task_type": "explanation", "prompt": "Test prompt for explanation", "max_tokens": 50}' "Explanation task routing (should use gpt-4-turbo)"

# Test 4: Model routing for auxiliary task (should use gpt-4o-mini)
echo -e "${BLUE}Testing model routing for auxiliary task...${NC}"
call_api "/api/ai/test_model_routing" "POST" '{"task_type": "auxiliary", "prompt": "Test prompt for auxiliary task", "max_tokens": 50}' "Auxiliary task routing (should use gpt-4o-mini)"

# Test 5: Test explanation generation
echo -e "${BLUE}Testing explanation generation...${NC}"
call_api "/api/ai/test_explanation" "POST" '{
    "adjustment_minutes": 15,
    "reliability": "high",
    "questionnaire_data": {
        "responses": [
            {"question": "Were you born in the morning or evening?", "answer": "Evening"},
            {"question": "Describe a significant life event", "answer": "Career change at 30"}
        ]
    }
}' "Explanation generation"

# Test 6: Test rectification
echo -e "${BLUE}Testing rectification...${NC}"
call_api "/api/ai/test_rectification" "POST" '{
    "birth_details": {
        "birthDate": "1990-01-01",
        "birthTime": "12:00",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York"
    },
    "questionnaire_data": {
        "responses": [
            {"question": "Were you born in the morning or evening?", "answer": "Afternoon"},
            {"question": "Any major life events?", "answer": "Career change at 28, marriage at 30"}
        ]
    }
}' "Rectification process"

# Test 7: Check usage statistics
echo -e "${BLUE}Testing usage statistics...${NC}"
call_api "/api/ai/usage_statistics" "GET" "" "Usage statistics"

echo -e "${GREEN}All tests completed!${NC}"
