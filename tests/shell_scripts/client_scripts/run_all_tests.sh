#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    BIRTH TIME RECTIFIER TESTING SUITE        ${NC}"
echo -e "${BLUE}===============================================${NC}"

# Create a directory for test results
RESULTS_DIR="test_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"
echo -e "${YELLOW}Test results will be saved to: $RESULTS_DIR${NC}"

# Default confidence threshold for OpenAI test
CONFIDENCE_THRESHOLD=90

# Parse command line arguments
for arg in "$@"
do
    case $arg in
        --threshold=*)
        CONFIDENCE_THRESHOLD="${arg#*=}"
        shift
        ;;
        *)
        # Unknown option
        ;;
    esac
done

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

# Improved extract_value function to reliably extract values from logs
extract_value() {
    local log_file=$1
    local key=$2
    local fallback=$3

    # Try direct extraction
    local value=$(grep -E "$key:" "$log_file" | head -1 | cut -d':' -f2 | tr -d ' ' | tr -d '\r')

    # If not found, try secondary extraction method
    if [ -z "$value" ]; then
        value=$(grep -o "$key=[a-zA-Z0-9_-]*" "$log_file" | cut -d'=' -f2 | head -1 | tr -d '\r')
    fi

    # If still not found, use fallback
    if [ -z "$value" ]; then
        echo -e "${RED}Failed to extract $key from log file. Using fallback.${NC}"
        value="$fallback-$(date +%s)"
    else
        echo -e "${GREEN}Successfully extracted $key: $value${NC}"
    fi

    echo "$value"
}

# Check if servers are running
check_server "http://localhost:3001" "API Gateway" || {
    echo -e "${RED}API Gateway must be running. Exiting.${NC}";
    exit 1;
}

check_server "http://localhost:8001" "AI Service" || {
    echo -e "${RED}AI Service must be running. Exiting.${NC}";
    exit 1;
}

# Make scripts executable (just to be sure)
chmod +x ./birth_time_rectifier_tester.sh
chmod +x ./advanced_api_tester.sh
chmod +x ./websocket_tester.sh
chmod +x ./openai_integration_tester.sh
chmod +x ./rectification_algorithm_tester.sh

# Display test options
echo -e "\n${BLUE}Available Tests:${NC}"
echo -e "1) Basic API Tests (session, geocoding, chart generation)"
echo -e "2) Advanced API Tests (questionnaire, rectification, comparison, export)"
echo -e "3) WebSocket Connection Test"
echo -e "4) OpenAI Integration & Questionnaire Flow Test (with confidence threshold ${CYAN}$CONFIDENCE_THRESHOLD%${NC})"
echo -e "5) Rectification Algorithm & Interpretation Analysis"
echo -e "6) Run All Tests"
echo -e "7) Exit"

read -p "Select a test to run (1-7): " TEST_CHOICE

SESSION_ID=""
CHART_ID=""
RECTIFIED_CHART_ID=""

case $TEST_CHOICE in
    1)
        echo -e "\n${BLUE}=== Running Basic API Tests ===${NC}"
        echo -e "${YELLOW}This will test session creation, geocoding, and chart generation${NC}"
        echo -e "${YELLOW}When prompted, enter your birth details${NC}"

        # Run the birth time rectifier tester and save output
        ./birth_time_rectifier_tester.sh | tee "$RESULTS_DIR/basic_tests.log"

        # Extract session ID and chart ID from the log file using improved extraction
        SESSION_ID=$(extract_value "$RESULTS_DIR/basic_tests.log" "Session ID" "fallback-session")
        CHART_ID=$(extract_value "$RESULTS_DIR/basic_tests.log" "Chart ID" "fallback-chart")

        echo -e "\n${GREEN}Test completed. Results saved to: $RESULTS_DIR/basic_tests.log${NC}"
        ;;
    2)
        # Get session and chart IDs for advanced tests
        read -p "Enter Session ID (leave blank to create new): " SESSION_ID
        read -p "Enter Chart ID (leave blank to create new): " CHART_ID

        if [ -z "$SESSION_ID" ] || [ -z "$CHART_ID" ]; then
            echo -e "\n${YELLOW}Running basic tests first to create session and chart...${NC}"
            ./birth_time_rectifier_tester.sh | tee "$RESULTS_DIR/basic_tests.log"

            # Extract session ID and chart ID
            SESSION_ID=$(extract_value "$RESULTS_DIR/basic_tests.log" "Session ID" "fallback-session")
            CHART_ID=$(extract_value "$RESULTS_DIR/basic_tests.log" "Chart ID" "fallback-chart")
        fi

        echo -e "\n${BLUE}=== Running Advanced API Tests ===${NC}"
        echo -e "${YELLOW}This will test questionnaire, rectification, chart comparison, and export${NC}"
        echo -e "${YELLOW}Using Session ID: $SESSION_ID${NC}"
        echo -e "${YELLOW}Using Chart ID: $CHART_ID${NC}"

        # Run the advanced API tester
        ./advanced_api_tester.sh --session="$SESSION_ID" --chart="$CHART_ID" | tee "$RESULTS_DIR/advanced_tests.log"

        # Extract rectified chart ID using improved extraction
        RECTIFIED_CHART_ID=$(extract_value "$RESULTS_DIR/advanced_tests.log" "Rectified Chart ID" "rectified-$CHART_ID")

        echo -e "\n${GREEN}Test completed. Results saved to: $RESULTS_DIR/advanced_tests.log${NC}"
        ;;
    3)
        # Get session ID for WebSocket test
        read -p "Enter Session ID (leave blank to create new): " SESSION_ID

        echo -e "\n${BLUE}=== Running WebSocket Connection Test ===${NC}"
        echo -e "${YELLOW}This will test real-time updates via WebSocket${NC}"
        echo -e "${YELLOW}Press Ctrl+C to exit the WebSocket test when done${NC}"

        # Run the WebSocket tester
        if [ -n "$SESSION_ID" ]; then
            ./websocket_tester.sh --session="$SESSION_ID" | tee "$RESULTS_DIR/websocket_tests.log"
        else
            ./websocket_tester.sh | tee "$RESULTS_DIR/websocket_tests.log"
        fi

        echo -e "\n${GREEN}Test completed. Results saved to: $RESULTS_DIR/websocket_tests.log${NC}"
        ;;
    4)
        # Get session and chart IDs for OpenAI integration test
        read -p "Enter Session ID (leave blank to create new): " SESSION_ID
        read -p "Enter Chart ID (leave blank to create new): " CHART_ID
        read -p "Enter confidence threshold (leave blank to use default $CONFIDENCE_THRESHOLD%): " CUSTOM_THRESHOLD

        if [ -n "$CUSTOM_THRESHOLD" ]; then
            CONFIDENCE_THRESHOLD=$CUSTOM_THRESHOLD
        fi

        echo -e "\n${BLUE}=== Running OpenAI Integration & Questionnaire Flow Test ===${NC}"
        echo -e "${YELLOW}This will test OpenAI verification and questionnaire flow until $CONFIDENCE_THRESHOLD% confidence${NC}"

        # Build command with available parameters
        CMD="./openai_integration_tester.sh --threshold=$CONFIDENCE_THRESHOLD"
        if [ -n "$SESSION_ID" ]; then
            CMD="$CMD --session=$SESSION_ID"
        fi
        if [ -n "$CHART_ID" ]; then
            CMD="$CMD --chart=$CHART_ID"
        fi

        # Run the OpenAI integration tester
        eval "$CMD" | tee "$RESULTS_DIR/openai_integration_tests.log"

        # Extract IDs for summary
        if [ -z "$SESSION_ID" ]; then
            SESSION_ID=$(extract_value "$RESULTS_DIR/openai_integration_tests.log" "Session ID" "session")
        fi
        if [ -z "$CHART_ID" ]; then
            CHART_ID=$(extract_value "$RESULTS_DIR/openai_integration_tests.log" "Original Chart ID" "chart")
        fi
        RECTIFIED_CHART_ID=$(extract_value "$RESULTS_DIR/openai_integration_tests.log" "Rectified Chart ID" "rectified")

        echo -e "\n${GREEN}Test completed. Results saved to: $RESULTS_DIR/openai_integration_tests.log${NC}"
        ;;
    5)
        # Get session, original chart and rectified chart IDs for detailed analysis
        read -p "Enter Session ID (leave blank to create new): " SESSION_ID
        read -p "Enter Original Chart ID (leave blank to create new): " CHART_ID
        read -p "Enter Rectified Chart ID (leave blank to create new): " RECTIFIED_CHART_ID

        echo -e "\n${BLUE}=== Running Rectification Algorithm & Interpretation Analysis ===${NC}"
        echo -e "${YELLOW}This will test detailed chart comparison, interpretation, and export functionality${NC}"

        # Build command with available parameters
        CMD="./rectification_algorithm_tester.sh --threshold=$CONFIDENCE_THRESHOLD"
        if [ -n "$SESSION_ID" ]; then
            CMD="$CMD --session=$SESSION_ID"
        fi
        if [ -n "$CHART_ID" ]; then
            CMD="$CMD --chart=$CHART_ID"
        fi
        if [ -n "$RECTIFIED_CHART_ID" ]; then
            CMD="$CMD --rectified=$RECTIFIED_CHART_ID"
        fi

        # Run the rectification algorithm tester
        eval "$CMD" | tee "$RESULTS_DIR/rectification_algorithm_tests.log"

        # Extract IDs for summary if not provided
        if [ -z "$SESSION_ID" ]; then
            SESSION_ID=$(extract_value "$RESULTS_DIR/rectification_algorithm_tests.log" "Session ID" "session")
        fi
        if [ -z "$CHART_ID" ]; then
            CHART_ID=$(extract_value "$RESULTS_DIR/rectification_algorithm_tests.log" "Original Chart ID" "chart")
        fi
        if [ -z "$RECTIFIED_CHART_ID" ]; then
            RECTIFIED_CHART_ID=$(extract_value "$RESULTS_DIR/rectification_algorithm_tests.log" "Rectified Chart ID" "rectified")
        fi

        echo -e "\n${GREEN}Test completed. Results saved to: $RESULTS_DIR/rectification_algorithm_tests.log${NC}"
        ;;
    6)
        echo -e "\n${BLUE}=== Running All Tests in Sequence According to Original Sequence Diagram ===${NC}"
        echo -e "${YELLOW}Following the full implementation flow defined in docs/architecture/sequence_diagram.md${NC}"

        # Step 1: Session Initialization (User visits app -> Frontend requests session initialization)
        echo -e "\n${BLUE}Step 1: Session Initialization${NC}"
        echo -e "${YELLOW}This corresponds to sequence diagram: User visits app -> GET /session/init${NC}"
        ./birth_time_rectifier_tester.sh | tee "$RESULTS_DIR/basic_tests.log"

        # Extract session ID
        SESSION_ID=$(extract_value "$RESULTS_DIR/basic_tests.log" "Session ID" "fallback-session")
        CHART_ID=$(extract_value "$RESULTS_DIR/basic_tests.log" "Chart ID" "fallback-chart")

        echo -e "\n${GREEN}Session initialized with ID: $SESSION_ID${NC}"

        # Step 2: WebSocket Connection for Real-time Updates
        echo -e "\n${BLUE}Step 2: Establishing WebSocket Connection for Real-time Updates${NC}"
        echo -e "${YELLOW}This enables real-time progress tracking throughout the application flow${NC}"
        # Run websocket in background for 30 seconds max - this will show updates during other operations
        timeout 30 ./websocket_tester.sh --session="$SESSION_ID" > "$RESULTS_DIR/websocket_background.log" 2>&1 &
        WS_PID=$!
        echo -e "${GREEN}WebSocket connection started in background with PID $WS_PID${NC}"
        sleep 2 # Give websocket time to connect

        # Step 3: OpenAI Integration with Chart Verification
        echo -e "\n${BLUE}Step 3: OpenAI Integration with Chart Verification${NC}"
        echo -e "${YELLOW}This corresponds to sequence diagram: Chart verification with OpenAI${NC}"
        ./openai_integration_tester.sh --threshold=$CONFIDENCE_THRESHOLD --session="$SESSION_ID" | tee "$RESULTS_DIR/openai_integration_tests.log"

        # Extract chart IDs from OpenAI test
        NEW_CHART_ID=$(extract_value "$RESULTS_DIR/openai_integration_tests.log" "Original Chart ID" "")
        if [ -n "$NEW_CHART_ID" ]; then
            CHART_ID=$NEW_CHART_ID
        fi

        RECTIFIED_CHART_ID=$(extract_value "$RESULTS_DIR/openai_integration_tests.log" "Rectified Chart ID" "")
        if [ -z "$RECTIFIED_CHART_ID" ]; then
            # If no rectified chart was created by OpenAI test, run advanced tests to get one
            echo -e "\n${BLUE}Step 4: Questionnaire Flow and Rectification${NC}"
            echo -e "${YELLOW}This corresponds to sequence diagram: Answer questionnaire -> Request rectification${NC}"
            ./advanced_api_tester.sh --session="$SESSION_ID" --chart="$CHART_ID" | tee "$RESULTS_DIR/advanced_tests.log"

            # Extract rectified chart ID
            RECTIFIED_CHART_ID=$(extract_value "$RESULTS_DIR/advanced_tests.log" "Rectified Chart ID" "rectified-$CHART_ID")
        else
            echo -e "\n${GREEN}Step 4: Questionnaire and Rectification already completed by OpenAI test${NC}"
        fi

        # Step 5: Detailed Chart Analysis and Interpretation
        echo -e "\n${BLUE}Step 5: Detailed Chart Analysis and Interpretation${NC}"
        echo -e "${YELLOW}This corresponds to sequence diagram: Compare charts -> Chart interpretation${NC}"
        ./rectification_algorithm_tester.sh --session="$SESSION_ID" --chart="$CHART_ID" --rectified="$RECTIFIED_CHART_ID" --threshold=$CONFIDENCE_THRESHOLD | tee "$RESULTS_DIR/rectification_algorithm_tests.log"

        # Stop WebSocket if still running
        if ps -p $WS_PID > /dev/null; then
            echo -e "\n${BLUE}Stopping background WebSocket connection${NC}"
            kill $WS_PID 2>/dev/null || true
            echo -e "${GREEN}WebSocket connection stopped${NC}"
            echo -e "${YELLOW}WebSocket log saved to: $RESULTS_DIR/websocket_background.log${NC}"
        fi

        echo -e "\n${GREEN}All tests completed according to sequence diagram flow. Results saved to: $RESULTS_DIR/${NC}"
        ;;
    7)
        echo -e "\n${YELLOW}Exiting without running tests.${NC}"
        exit 0
        ;;
    *)
        echo -e "\n${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}    TESTING COMPLETE                          ${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "\n${YELLOW}Test Summary:${NC}"
echo -e "Session ID: $SESSION_ID"
echo -e "Chart ID: $CHART_ID"
if [ -n "$RECTIFIED_CHART_ID" ]; then
    echo -e "Rectified Chart ID: $RECTIFIED_CHART_ID"
fi
echo -e "Test results saved to: $RESULTS_DIR/"

echo -e "\n${GREEN}To view all test results: cat $RESULTS_DIR/*.log${NC}"
