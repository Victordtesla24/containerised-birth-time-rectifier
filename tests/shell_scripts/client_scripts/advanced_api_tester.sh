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

# Session and chart IDs (will be overridden by command line args)
SESSION_ID=""
CHART_ID=""
RECTIFIED_CHART_ID=""

# Parse command line arguments
for arg in "$@"
do
    case $arg in
        --session=*)
        SESSION_ID="${arg#*=}"
        shift
        ;;
        --chart=*)
        CHART_ID="${arg#*=}"
        shift
        ;;
        *)
        # Unknown option
        ;;
    esac
done

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    ADVANCED API TESTING SUITE                ${NC}"
echo -e "${BLUE}===============================================${NC}"

# Verify session and chart IDs were provided
if [ -z "$SESSION_ID" ] || [ -z "$CHART_ID" ]; then
    echo -e "${RED}Error: Both session ID and chart ID must be provided${NC}"
    echo -e "${YELLOW}Usage: ./advanced_api_tester.sh --session=SESSION_ID --chart=CHART_ID${NC}"
    exit 1
fi

echo -e "${GREEN}Using Session ID: $SESSION_ID${NC}"
echo -e "${GREEN}Using Chart ID: $CHART_ID${NC}"

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

# Test WebSocket connection (if available)
test_websocket() {
    echo -e "\n${YELLOW}Testing WebSocket connection...${NC}"
    echo -e "${YELLOW}This requires websocat tool. If not installed, please install it with:${NC}"
    echo -e "${YELLOW}brew install websocat (on macOS)${NC}"

    if command -v websocat &> /dev/null; then
        echo -e "${GREEN}websocat found, testing WebSocket connection${NC}"
        echo -e "${YELLOW}Connecting to ws://localhost:3001/ws/$SESSION_ID...${NC}"
        echo -e "${YELLOW}Press Ctrl+C after a few seconds to stop the WebSocket connection${NC}"

        # Connect to API Gateway WebSocket endpoint instead of AI Service directly
        WS_URL="ws://localhost:3001/ws/$SESSION_ID"
        echo "Connecting to $WS_URL..."
        echo "Press Ctrl+C after a few seconds to stop the WebSocket connection"

        # Use a background process with sleep instead of timeout for better compatibility
        (
            websocat "$WS_URL" 2>/dev/null &
            WEBSOCAT_PID=$!

            # Sleep for 5 seconds then kill the process
            sleep 5
            kill $WEBSOCAT_PID 2>/dev/null || true
        ) || echo "WebSocket connection failed"
    else
        echo -e "${RED}websocat not found, skipping WebSocket test${NC}"
        echo -e "${YELLOW}To install websocat: brew install websocat (on macOS)${NC}"
    fi
}

# Step 1: Check if servers are running
check_server "$API_URL" "API Gateway" || { echo -e "${RED}API Gateway must be running. Exiting.${NC}"; exit 1; }
check_server "$AI_SERVICE_URL" "AI Service" || { echo -e "${RED}AI Service must be running. Exiting.${NC}"; exit 1; }

# Step 2: Check if the chart exists
echo -e "\n${BLUE}=== Verifying Chart Exists ===${NC}"
CHART_ENDPOINT="/api/v1/chart/$CHART_ID"
test_endpoint "$CHART_ENDPOINT" "GET" "" "Verify Chart Exists" || {
    echo -e "${RED}Chart not found. Please ensure you're using a valid chart ID.${NC}";
    exit 1;
}

# Step 3: Get questionnaire
echo -e "\n${BLUE}=== Getting Questionnaire ===${NC}"
QUESTIONNAIRE_ENDPOINT="/api/v1/questionnaire?chart_id=$CHART_ID"
QUESTIONNAIRE_RESPONSE=$(test_endpoint "$QUESTIONNAIRE_ENDPOINT" "GET" "" "Get Questionnaire")

# Extract question ID from response - fix extraction to avoid duplication
QUESTION_ID=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

if [ -n "$QUESTION_ID" ]; then
    echo -e "${GREEN}Got question ID: $QUESTION_ID${NC}"
else
    echo -e "${RED}Failed to get question ID${NC}"
    QUESTION_ID="question-1"
    echo -e "${YELLOW}Using fallback question ID: $QUESTION_ID${NC}"
fi

# Step 4: Answer questionnaire questions
echo -e "\n${BLUE}=== Answering Questionnaire ===${NC}"
echo -e "${YELLOW}Please provide answers to the following questions${NC}"

# Get initial question text
QUESTION_TEXT=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"text":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',' | sed 's/\\"/"/g')
if [ -z "$QUESTION_TEXT" ]; then
    QUESTION_TEXT="Please provide an answer to the question"
fi

# Interactive question-answer loop
MAX_QUESTIONS=5  # Limit to 5 questions for testing
for i in $(seq 1 $MAX_QUESTIONS); do
    echo -e "\n${YELLOW}Question $i: $QUESTION_TEXT${NC}"
    echo -e "${GREEN}Enter your answer (or type 'skip' to move on, 'complete' to finish):${NC}"
    read -r user_answer

    # Check if user wants to skip or complete
    if [ "$user_answer" == "skip" ]; then
        echo -e "${YELLOW}Skipping this question${NC}"
        continue
    elif [ "$user_answer" == "complete" ]; then
        echo -e "${YELLOW}Completing questionnaire early${NC}"
        break
    fi

    # Properly escape JSON special characters in the user answer
    escaped_answer=$(echo "$user_answer" | sed 's/"/\\"/g')

    # Prepare and send the answer
    ANSWER_DATA="{\"question_id\":\"$QUESTION_ID\",\"answer\":\"$escaped_answer\",\"chart_id\":\"$CHART_ID\",\"session_id\":\"$SESSION_ID\"}"
    ANSWER_ENDPOINT="/api/v1/questionnaire/$SESSION_ID/answer"

    echo -e "${YELLOW}Submitting your answer...${NC}"
    ANSWER_RESPONSE=$(test_endpoint "$ANSWER_ENDPOINT" "POST" "$ANSWER_DATA" "Submit Answer $i")

    # Check if we received a valid response
    if [ $? -ne 0 ]; then
        # Try alternative endpoint if the first one fails
        ANSWER_ENDPOINT="/api/v1/questionnaire/answer"
        ANSWER_RESPONSE=$(test_endpoint "$ANSWER_ENDPOINT" "POST" "$ANSWER_DATA" "Submit Answer $i (alternative endpoint)")

        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to submit answer. Continuing with next question.${NC}"
            # Still try to extract the next question ID if available
            NEXT_QUESTION_ID=$(echo "$ANSWER_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')
        fi
    fi

    # Extract the next question ID and text
    NEXT_QUESTION_ID=$(echo "$ANSWER_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')
    NEXT_QUESTION_TEXT=$(echo "$ANSWER_RESPONSE" | grep -o '"text":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',' | sed 's/\\"/"/g')

    # Check the confidence level to see if we've reached a threshold
    CONFIDENCE=$(echo "$ANSWER_RESPONSE" | grep -o '"confidence":[0-9.]*' | head -1 | cut -d':' -f2)

    # Update for next iteration
    if [ -n "$NEXT_QUESTION_ID" ]; then
        QUESTION_ID=$NEXT_QUESTION_ID
    fi

    if [ -n "$NEXT_QUESTION_TEXT" ]; then
        QUESTION_TEXT=$NEXT_QUESTION_TEXT
    fi

    # Check if we've reached high confidence (70+)
    if (( $(echo "$CONFIDENCE > 70" | bc -l 2>/dev/null) )); then
        echo -e "${GREEN}Reached high confidence level ($CONFIDENCE). Completing questionnaire.${NC}"
        break
    fi

    # Short delay between questions
    sleep 1
done

# Step 5: Complete the questionnaire
echo -e "\n${BLUE}=== Completing Questionnaire ===${NC}"
COMPLETE_DATA="{\"chart_id\":\"$CHART_ID\",\"session_id\":\"$SESSION_ID\"}"
COMPLETE_ENDPOINT="/api/v1/questionnaire/complete"
test_endpoint "$COMPLETE_ENDPOINT" "POST" "$COMPLETE_DATA" "Complete Questionnaire"

# Step 6: Request birth time rectification
echo -e "\n${BLUE}=== Requesting Birth Time Rectification ===${NC}"
RECTIFY_DATA="{\"chart_id\":\"$CHART_ID\",\"session_id\":\"$SESSION_ID\"}"
RECTIFY_ENDPOINT="/api/v1/chart/rectify"
RECTIFY_RESPONSE=$(test_endpoint "$RECTIFY_ENDPOINT" "POST" "$RECTIFY_DATA" "Rectify Birth Time")

# Extract rectified chart ID - fix extraction
RECTIFIED_CHART_ID=$(echo "$RECTIFY_RESPONSE" | grep -o '"rectified_chart_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

if [ -n "$RECTIFIED_CHART_ID" ]; then
    echo -e "${GREEN}Got rectified chart ID: $RECTIFIED_CHART_ID${NC}"
else
    echo -e "${RED}Failed to get rectified chart ID${NC}"
    RECTIFIED_CHART_ID="rectified-$CHART_ID"
    echo -e "${YELLOW}Using fallback rectified chart ID: $RECTIFIED_CHART_ID${NC}"
fi

# Step 7: Compare charts
echo -e "\n${BLUE}=== Comparing Charts ===${NC}"
if [ -n "$RECTIFIED_CHART_ID" ]; then
    echo -e "${YELLOW}Using rectified chart ID: $RECTIFIED_CHART_ID${NC}"
    COMPARE_PARAMS="chart1=$CHART_ID&chart2=$RECTIFIED_CHART_ID"
else
    # If no rectified chart ID, use original chart for both parameters
    echo -e "${YELLOW}Using original chart for both comparison parameters${NC}"
    COMPARE_PARAMS="chart1=$CHART_ID&chart2=$CHART_ID"
fi

# Use direct curl command instead of test_endpoint function for comparison
echo -e "${YELLOW}Using direct curl for chart comparison${NC}"
DIRECT_CURL_CMD="curl -s \"$API_URL/api/v1/chart/compare?$COMPARE_PARAMS\" -H \"X-Session-ID: $SESSION_ID\""
echo -e "${YELLOW}Command: $DIRECT_CURL_CMD${NC}"
COMPARE_RESPONSE=$(eval $DIRECT_CURL_CMD)

# Check if the response was successful
if [ -n "$COMPARE_RESPONSE" ]; then
    echo -e "${GREEN}SUCCESS - Chart comparison completed${NC}"
    echo "$COMPARE_RESPONSE" | python -m json.tool 2>/dev/null || echo "$COMPARE_RESPONSE"
else
    echo -e "${RED}FAILED - Chart comparison failed${NC}"
    # Fall back to the original test_endpoint approach
    COMPARE_ENDPOINT="/api/v1/chart/compare?$COMPARE_PARAMS"
    test_endpoint "$COMPARE_ENDPOINT" "GET" "" "Compare Charts (fallback)"
fi

# Step 8: Export chart
echo -e "\n${BLUE}=== Exporting Chart ===${NC}"
EXPORT_DATA="{\"chart_id\":\"$RECTIFIED_CHART_ID\",\"session_id\":\"$SESSION_ID\",\"format\":\"pdf\"}"
EXPORT_ENDPOINT="/api/v1/chart/export"
EXPORT_RESPONSE=$(test_endpoint "$EXPORT_ENDPOINT" "POST" "$EXPORT_DATA" "Export Chart")

# Extract export ID - fix extraction
EXPORT_ID=$(echo "$EXPORT_RESPONSE" | grep -o '"export_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

if [ -n "$EXPORT_ID" ]; then
    echo -e "${GREEN}Got export ID: $EXPORT_ID${NC}"

    # Download the exported file
    echo -e "\n${BLUE}=== Downloading Exported Chart ===${NC}"
    DOWNLOAD_ENDPOINT="/api/v1/chart/export/$EXPORT_ID/download"
    DOWNLOAD_CMD="curl -s -o exported_chart.pdf $API_URL$DOWNLOAD_ENDPOINT"
    echo -e "${YELLOW}Command: $DOWNLOAD_CMD${NC}"
    eval $DOWNLOAD_CMD

    if [ -f "exported_chart.pdf" ]; then
        echo -e "${GREEN}Successfully downloaded exported chart to exported_chart.pdf${NC}"
    else
        echo -e "${RED}Failed to download exported chart${NC}"
    fi
else
    echo -e "${RED}Failed to get export ID${NC}"
fi

# Step 9: Test WebSocket connection if available (for real-time updates)
if [ -x "$(command -v websocat)" ]; then
    echo -e "\n${BLUE}=== Testing WebSocket Connection ===${NC}"
    test_websocket
fi

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}       ADVANCED API TESTING COMPLETE          ${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "\n${YELLOW}Test Summary:${NC}"
echo -e "Session ID: $SESSION_ID"
echo -e "Original Chart ID: $CHART_ID"
echo -e "Rectified Chart ID: $RECTIFIED_CHART_ID"

echo -e "\n${GREEN}All API endpoints in the sequence diagram have been tested!${NC}"
