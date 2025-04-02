#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# API Gateway URL
API_URL="http://localhost:3001"
AI_SERVICE_URL="http://localhost:8001"

# Session and chart IDs (will be overridden by command line args or new session)
SESSION_ID=""
CHART_ID=""
RECTIFIED_CHART_ID=""

# Confidence threshold
CONFIDENCE_THRESHOLD=90
CURRENT_CONFIDENCE=0

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
        --threshold=*)
        CONFIDENCE_THRESHOLD="${arg#*=}"
        shift
        ;;
        *)
        # Unknown option
        ;;
    esac
done

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    OPENAI INTEGRATION & QUESTIONNAIRE TESTER  ${NC}"
echo -e "${BLUE}===============================================${NC}"
echo -e "${YELLOW}Testing with confidence threshold: $CONFIDENCE_THRESHOLD%${NC}"

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

# Function to start WebSocket connection
start_websocket() {
    if ! command -v websocat &> /dev/null; then
        echo -e "${RED}Error: websocat is not installed.${NC}"
        echo -e "${YELLOW}Please install websocat to test WebSocket connections:${NC}"
        echo -e "${YELLOW}  - On macOS: brew install websocat${NC}"
        echo -e "${YELLOW}  - On Linux: cargo install websocat${NC}"
        echo -e "${YELLOW}  - Or download from: https://github.com/vi/websocat/releases${NC}"
        return 1
    fi

    echo -e "\n${YELLOW}Starting WebSocket connection in background...${NC}"
    echo -e "${YELLOW}WebSocket URL: ws://localhost:8001/ws/${SESSION_ID}${NC}"

    # Start websocat in background and save its process ID
    websocat "ws://localhost:8001/ws/${SESSION_ID}" > websocket_output.log 2>&1 &
    WS_PID=$!

    echo -e "${GREEN}WebSocket connection started with PID $WS_PID${NC}"
    echo -e "${YELLOW}Output will be saved to websocket_output.log${NC}"

    # Return the PID
    echo $WS_PID
}

# Function to extract OpenAI verification information from chart data
extract_verification_info() {
    local chart_data=$1

    # Extract verification information
    local verified=$(echo "$chart_data" | grep -o '"verified":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    local confidence=$(echo "$chart_data" | grep -o '"confidence_score":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    local corrections=$(echo "$chart_data" | grep -o '"corrections_applied":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    local message=$(echo "$chart_data" | grep -o '"message":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')
    local method=$(echo "$chart_data" | grep -o '"verification_method":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')

    echo -e "\n${CYAN}=== OpenAI Chart Verification Results ===${NC}"
    echo -e "${CYAN}Verified: $verified${NC}"
    echo -e "${CYAN}Confidence Score: $confidence${NC}"
    echo -e "${CYAN}Corrections Applied: $corrections${NC}"
    echo -e "${CYAN}Message: $message${NC}"
    echo -e "${CYAN}Method: $method${NC}"

    # Return the confidence score
    echo $confidence
}

# Function to answer questions until confidence threshold is reached
answer_questions_until_threshold() {
    local chart_id=$1
    local threshold=$2
    local current_confidence=0
    local question_count=0
    local max_questions=20 # Safety limit

    echo -e "\n${BLUE}=== Starting Questionnaire Flow ===${NC}"
    echo -e "${YELLOW}Will continue until confidence threshold of $threshold% is reached${NC}"

    # Get initial questionnaire
    QUESTIONNAIRE_ENDPOINT="/api/v1/questionnaire?chart_id=$chart_id"
    QUESTIONNAIRE_RESPONSE=$(test_endpoint "$QUESTIONNAIRE_ENDPOINT" "GET" "" "Get Initial Questionnaire")

    # Extract question ID and text
    QUESTION_ID=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')
    QUESTION_TEXT=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"text":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')
    QUESTION_TYPE=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"type":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')
    current_confidence=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"confidence":[^,}]*' | head -1 | cut -d':' -f2 | tr -d ' ')

    # If confidence is not a number, set to 0
    if ! [[ "$current_confidence" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        current_confidence=0
    fi

    while (( $(echo "$current_confidence < $threshold" | bc -l) )) && [ $question_count -lt $max_questions ]; do
        (( question_count++ ))

        echo -e "\n${CYAN}=== Question $question_count ===${NC}"
        echo -e "${CYAN}ID: $QUESTION_ID${NC}"
        echo -e "${CYAN}Type: $QUESTION_TYPE${NC}"
        echo -e "${CYAN}Question: $QUESTION_TEXT${NC}"
        echo -e "${CYAN}Current Confidence: $current_confidence%${NC}"

        local answer=""
        local options=""

        # If question type is multiple_choice, extract and display options
        if [ "$QUESTION_TYPE" == "multiple_choice" ]; then
            options=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"options":\[.*\]' | sed 's/"options":\[//' | sed 's/\]$//')

            # Parse and display options
            echo -e "${YELLOW}Options:${NC}"
            local option_count=0
            while read -r option; do
                option_id=$(echo "$option" | grep -o '"id":"[^"]*"' | cut -d':' -f2 | tr -d '"' | tr -d ',')
                option_text=$(echo "$option" | grep -o '"text":"[^"]*"' | cut -d':' -f2 | tr -d '"')
                (( option_count++ ))
                echo -e "${YELLOW}$option_count) $option_text ($option_id)${NC}"
            done < <(echo "$options" | grep -o '{[^}]*}')

            # Ask user to choose an option
            read -p "Select an option (1-$option_count): " option_choice

            # Get the selected option ID
            local selected_option=""
            local choice_count=0
            while read -r option; do
                (( choice_count++ ))
                if [ "$choice_count" -eq "$option_choice" ]; then
                    selected_option=$(echo "$option" | grep -o '"id":"[^"]*"' | cut -d':' -f2 | tr -d '"' | tr -d ',')
                    selected_text=$(echo "$option" | grep -o '"text":"[^"]*"' | cut -d':' -f2 | tr -d '"')
                    break
                fi
            done < <(echo "$options" | grep -o '{[^}]*}')

            answer="Selected option: $selected_text"
        else
            # Free text answer
            read -p "Enter your answer: " answer
        fi

        echo -e "${GREEN}Your answer: $answer${NC}"

        # Submit answer
        ANSWER_DATA="{\"question_id\":\"$QUESTION_ID\",\"answer\":\"$answer\",\"chart_id\":\"$chart_id\",\"session_id\":\"$SESSION_ID\"}"
        ANSWER_ENDPOINT="/api/v1/questionnaire/answer"
        ANSWER_RESPONSE=$(test_endpoint "$ANSWER_ENDPOINT" "POST" "$ANSWER_DATA" "Submit Answer to Question $question_count")

        # Extract next question or completion status
        if echo "$ANSWER_RESPONSE" | grep -q '"confidence"'; then
            # Extract new confidence level
            current_confidence=$(echo "$ANSWER_RESPONSE" | grep -o '"confidence":[^,}]*' | head -1 | cut -d':' -f2 | tr -d ' ')

            # If confidence is not a number, set to previous value
            if ! [[ "$current_confidence" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
                echo -e "${YELLOW}Warning: Could not extract confidence score. Using previous value.${NC}"
                # Keep previous confidence
            fi

            # Check if we've reached the threshold
            if (( $(echo "$current_confidence >= $threshold" | bc -l) )); then
                echo -e "\n${GREEN}====================================${NC}"
                echo -e "${GREEN}Confidence threshold reached: $current_confidence% >= $threshold%${NC}"
                echo -e "${GREEN}====================================${NC}"
                break
            fi

            # Extract next question information
            QUESTION_ID=$(echo "$ANSWER_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')
            QUESTION_TEXT=$(echo "$ANSWER_RESPONSE" | grep -o '"text":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')
            QUESTION_TYPE=$(echo "$ANSWER_RESPONSE" | grep -o '"type":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')

            # If no more questions, break
            if [ -z "$QUESTION_ID" ]; then
                echo -e "\n${YELLOW}No more questions available. Completing questionnaire.${NC}"
                break
            fi

            # Store response for next iteration
            QUESTIONNAIRE_RESPONSE=$ANSWER_RESPONSE
        else
            echo -e "\n${RED}Could not get next question. Questionnaire may be complete.${NC}"
            break
        fi

        echo -e "\n${YELLOW}Moving to next question. Current confidence: $current_confidence%${NC}"
    done

    echo -e "\n${BLUE}=== Completing Questionnaire ===${NC}"
    echo -e "${YELLOW}Total questions answered: $question_count${NC}"
    echo -e "${YELLOW}Final confidence score: $current_confidence%${NC}"

    # Complete questionnaire
    COMPLETE_DATA="{\"chart_id\":\"$chart_id\",\"session_id\":\"$SESSION_ID\"}"
    COMPLETE_ENDPOINT="/api/v1/questionnaire/complete"
    COMPLETE_RESPONSE=$(test_endpoint "$COMPLETE_ENDPOINT" "POST" "$COMPLETE_DATA" "Complete Questionnaire")

    # Return the final confidence score
    echo $current_confidence
}

# Step 1: Check if servers are running
check_server "$API_URL" "API Gateway" || { echo -e "${RED}API Gateway must be running. Exiting.${NC}"; exit 1; }
check_server "$AI_SERVICE_URL" "AI Service" || { echo -e "${RED}AI Service must be running. Exiting.${NC}"; exit 1; }

# Step 2: Create session if not provided
if [ -z "$SESSION_ID" ]; then
    echo -e "\n${BLUE}=== Creating New Session ===${NC}"
    SESSION_RESPONSE=$(test_endpoint "/api/v1/session/init" "GET" "" "Session Initialization")
    SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

    if [ -n "$SESSION_ID" ]; then
        echo -e "${GREEN}Session created with ID: $SESSION_ID${NC}"
    else
        echo -e "${RED}Failed to create session${NC}"
        SESSION_ID="fallback-session-$(date +%s)"
        echo -e "${YELLOW}Using fallback session ID: $SESSION_ID${NC}"
    fi
else
    echo -e "\n${GREEN}Using provided Session ID: $SESSION_ID${NC}"
fi

# Step 3: Create or use provided chart
if [ -z "$CHART_ID" ]; then
    echo -e "\n${BLUE}=== Creating New Birth Chart ===${NC}"

    # Get user birth details
    echo -e "\n${BLUE}=== Enter Birth Details ===${NC}"
    read -p "Enter birth date (YYYY-MM-DD): " BIRTH_DATE
    read -p "Enter birth time (HH:MM:SS): " BIRTH_TIME
    read -p "Enter birth location (e.g., New York, USA): " LOCATION_QUERY

    # Get geocoding information
    echo -e "\n${BLUE}=== Getting Geocoding Information ===${NC}"
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

    # Generate chart with OpenAI verification
    echo -e "\n${BLUE}=== Generating Birth Chart with OpenAI Verification ===${NC}"
    # Create birth_details object for chart generation
    GENERATE_DATA="{\"birth_date\":\"$BIRTH_DATE\",\"birth_time\":\"$BIRTH_TIME\",\"latitude\":$LATITUDE,\"longitude\":$LONGITUDE,\"timezone\":\"$TIMEZONE\",\"session_id\":\"$SESSION_ID\",\"verify_with_openai\":true}"
    CHART_RESPONSE=$(test_endpoint "/api/v1/chart/generate" "POST" "$GENERATE_DATA" "Generate Birth Chart with OpenAI Verification")

    # Extract chart ID
    CHART_ID=$(echo "$CHART_RESPONSE" | grep -o '"chart_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

    if [ -n "$CHART_ID" ]; then
        echo -e "${GREEN}Chart generated with ID: $CHART_ID${NC}"
    else
        echo -e "${RED}Failed to generate chart${NC}"
        exit 1
    fi

    # Extract OpenAI verification information
    extract_verification_info "$CHART_RESPONSE"
else
    echo -e "\n${GREEN}Using provided Chart ID: $CHART_ID${NC}"

    # Retrieve chart details to verify it exists
    echo -e "\n${BLUE}=== Retrieving Chart Details ===${NC}"
    CHART_ENDPOINT="/api/v1/chart/$CHART_ID"
    CHART_RESPONSE=$(test_endpoint "$CHART_ENDPOINT" "GET" "" "Retrieve Chart Details")

    if [ -z "$CHART_RESPONSE" ]; then
        echo -e "${RED}Failed to retrieve chart with ID: $CHART_ID${NC}"
        exit 1
    fi

    # Extract OpenAI verification information
    extract_verification_info "$CHART_RESPONSE"
fi

# Step 4: Start WebSocket connection in background for real-time updates
WS_PID=$(start_websocket)

# Step 5: Run questionnaire until confidence threshold is reached
echo -e "\n${BLUE}=== Starting Questionnaire Process ===${NC}"
echo -e "${YELLOW}Will continue until confidence threshold of $CONFIDENCE_THRESHOLD% is reached${NC}"
echo -e "${YELLOW}Follow the prompts to answer questions...${NC}"

final_confidence=$(answer_questions_until_threshold "$CHART_ID" "$CONFIDENCE_THRESHOLD")

# Step 6: Request birth time rectification
echo -e "\n${BLUE}=== Requesting Birth Time Rectification ===${NC}"
echo -e "${YELLOW}Using final confidence score: $final_confidence%${NC}"

RECTIFY_DATA="{\"chart_id\":\"$CHART_ID\",\"session_id\":\"$SESSION_ID\"}"
RECTIFY_ENDPOINT="/api/v1/chart/rectify"
RECTIFY_RESPONSE=$(test_endpoint "$RECTIFY_ENDPOINT" "POST" "$RECTIFY_DATA" "Rectify Birth Time")

# Extract rectified chart ID
RECTIFIED_CHART_ID=$(echo "$RECTIFY_RESPONSE" | grep -o '"rectified_chart_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')
RECTIFIED_TIME=$(echo "$RECTIFY_RESPONSE" | grep -o '"rectified_time":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')
RECTIFICATION_CONFIDENCE=$(echo "$RECTIFY_RESPONSE" | grep -o '"confidence":[^,}]*' | head -1 | cut -d':' -f2 | tr -d ' ')

if [ -n "$RECTIFIED_CHART_ID" ]; then
    echo -e "\n${GREEN}====================================${NC}"
    echo -e "${GREEN}Birth Time Rectification Complete${NC}"
    echo -e "${GREEN}====================================${NC}"
    echo -e "${GREEN}Rectified Chart ID: $RECTIFIED_CHART_ID${NC}"
    echo -e "${GREEN}Rectified Birth Time: $RECTIFIED_TIME${NC}"
    echo -e "${GREEN}Rectification Confidence: $RECTIFICATION_CONFIDENCE%${NC}"
else
    echo -e "${RED}Failed to get rectified chart ID${NC}"
    RECTIFIED_CHART_ID="rectified-$CHART_ID"
    echo -e "${YELLOW}Using fallback rectified chart ID: $RECTIFIED_CHART_ID${NC}"
fi

# Step 7: Compare original and rectified charts
echo -e "\n${BLUE}=== Comparing Original and Rectified Charts ===${NC}"
COMPARE_ENDPOINT="/api/v1/chart/compare?chart1=$CHART_ID&chart2=$RECTIFIED_CHART_ID"
COMPARE_RESPONSE=$(test_endpoint "$COMPARE_ENDPOINT" "GET" "" "Compare Charts")

# Step 8: Clean up WebSocket connection
if [ -n "$WS_PID" ]; then
    echo -e "\n${BLUE}=== Stopping WebSocket Connection ===${NC}"
    kill $WS_PID 2>/dev/null
    echo -e "${GREEN}WebSocket connection stopped${NC}"

    # Display WebSocket output
    if [ -f "websocket_output.log" ]; then
        echo -e "\n${BLUE}=== WebSocket Messages Received ===${NC}"
        cat websocket_output.log
    fi
fi

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}    OPENAI INTEGRATION TESTING COMPLETE         ${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "\n${YELLOW}Test Summary:${NC}"
echo -e "Session ID: $SESSION_ID"
echo -e "Original Chart ID: $CHART_ID"
echo -e "Rectified Chart ID: $RECTIFIED_CHART_ID"
echo -e "Questionnaire Confidence: $final_confidence%"
echo -e "Rectification Confidence: $RECTIFICATION_CONFIDENCE%"
echo -e "Rectified Birth Time: $RECTIFIED_TIME"

echo -e "\n${GREEN}OpenAI integration testing complete!${NC}"
