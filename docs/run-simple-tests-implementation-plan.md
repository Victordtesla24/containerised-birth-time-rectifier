## Current State Analysis

The existing script has a solid foundation:

- Well-structured with modular functions for each step in the sequence
- Uses cURL for API testing
- Handles user input and displays results
- Follows the sequence flow described in the documentation
- However, it lacks WebSocket integration for real-time features, particularly for the questionnaire and rectification processes.

## Implementation Plan

### 1. Add WebSocket Client Functionality

Implement a WebSocket client in bash using the websocat tool, which is a command-line WebSocket client that can be easily integrated into shell scripts.

```bash
# Function to establish WebSocket connection
establish_websocket_connection() {
  display_step "WS" "WebSocket Connection" "Establishing real-time connection to the API"

  # Check if we have a session token
  if [[ -z "$SESSION_TOKEN" ]]; then
    echo -e "${RED}Error: No session token available. Please initialize a session first.${NC}"
    return 1
  fi

  # Create a unique file for this connection
  WS_OUTPUT_FILE="/tmp/ws_output_${SESSION_TOKEN}.txt"
  touch "$WS_OUTPUT_FILE"

  # Start websocat in the background, with authentication header
  websocat -v "ws://${API_URL#http://}/ws/${SESSION_TOKEN}" \
    --header="Authorization: Bearer ${SESSION_TOKEN}" \
    > "$WS_OUTPUT_FILE" 2>/dev/null &

  WS_PID=$!

  # Check if connection was established
  sleep 2
  if ps -p $WS_PID > /dev/null; then
    echo -e "${GREEN}WebSocket connection established (PID: $WS_PID)${NC}"
    echo -e "Real-time updates will be displayed during the process"
    return 0
  else
    echo -e "${RED}Failed to establish WebSocket connection${NC}"
    echo -e "${YELLOW}Continuing with HTTP-only mode${NC}"
    return 1
  fi
}

# Function to close WebSocket connection
close_websocket_connection() {
  if [[ ! -z "$WS_PID" ]]; then
    echo -e "${YELLOW}Closing WebSocket connection...${NC}"
    kill $WS_PID 2>/dev/null || true
    rm -f "$WS_OUTPUT_FILE" 2>/dev/null || true
    echo -e "${GREEN}WebSocket connection closed${NC}"
  fi
}

# Function to read WebSocket messages
read_websocket_messages() {
  if [[ -z "$WS_OUTPUT_FILE" || ! -f "$WS_OUTPUT_FILE" ]]; then
    return 1
  fi

  # Read new messages from the WebSocket output file
  NEW_MESSAGES=$(cat "$WS_OUTPUT_FILE" 2>/dev/null)

  # Clear the file for new messages
  > "$WS_OUTPUT_FILE"

  # Return the messages
  echo "$NEW_MESSAGES"
}
```

### 2. Enhance Questionnaire Handling with WebSockets

Modify the handle_questionnaire function to use WebSockets for real-time updates:

```bash
handle_questionnaire() {
  display_step "6-9" "Questionnaire" "Answering birth time rectification questionnaire with real-time updates"

  # Check if we have a chart ID
  if [[ -z "$CHART_ID" ]]; then
    echo -e "${RED}Error: No chart ID available. Please generate a chart first.${NC}"
    return 1
  fi

  # Check if we have a session token
  if [[ -z "$SESSION_TOKEN" ]]; then
    echo -e "${RED}Error: No session token available. Please initialize a session first.${NC}"
    return 1
  fi

  # Establish WebSocket connection for real-time updates
  establish_websocket_connection
  WS_ENABLED=$?

  # Start questionnaire
  QUESTIONNAIRE_CMD="curl -s ${API_URL}/questionnaire -H 'Authorization: Bearer ${SESSION_TOKEN}' -H 'Content-Type: application/json' -d '{\"chart_id\": \"$CHART_ID\"}'"
  QUESTIONNAIRE_RESPONSE=$(execute_curl "$QUESTIONNAIRE_CMD")
  QUESTIONNAIRE_ID=$(echo "$QUESTIONNAIRE_RESPONSE" | jq -r '.questionnaire_id')

  # Check if we got a valid questionnaire ID
  if [[ -z "$QUESTIONNAIRE_ID" || "$QUESTIONNAIRE_ID" == "null" ]]; then
    echo -e "${RED}Error: Failed to get a valid questionnaire ID.${NC}"
    close_websocket_connection
    return 1
  fi

  CURRENT_QUESTION=$(echo "$QUESTIONNAIRE_RESPONSE" | jq -r '.questions[0].text')
  CURRENT_QUESTION_ID=$(echo "$QUESTIONNAIRE_RESPONSE" | jq -r '.questions[0].id')
  TOTAL_QUESTIONS=$(echo "$QUESTIONNAIRE_RESPONSE" | jq -r '.total_questions')

  echo -e "Questionnaire ID: ${YELLOW}$QUESTIONNAIRE_ID${NC}"
  echo -e "Total Questions: ${YELLOW}$TOTAL_QUESTIONS${NC}"

  # Answer questions
  QUESTION_NUMBER=1
  CURRENT_CONFIDENCE=$VERIFICATION_CONFIDENCE

  while [[ ! -z "$CURRENT_QUESTION" && "$CURRENT_QUESTION" != "null" ]]; do
    echo -e "\n${BLUE}==================================================${NC}"
    echo -e "${BLUE}     QUESTION $QUESTION_NUMBER OF $TOTAL_QUESTIONS     ${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${YELLOW}$CURRENT_QUESTION${NC}"
    echo -e "${CYAN}Current Confidence Score: ${CURRENT_CONFIDENCE}%${NC}"
    echo -e ""

    # Display question options dynamically based on question type
    QUESTION_TYPE=$(echo "$QUESTIONNAIRE_RESPONSE" | jq -r '.questions[0].type // "yes_no"')

    if [[ "$QUESTION_TYPE" == "yes_no" ]]; then
      echo -e "1. Yes"
      echo -e "2. No"
      echo -e "3. Not sure"
      echo -e "${YELLOW}Enter your answer (1-3):${NC}"

      while true; do
        read -r -p "> " answer_num
        case $answer_num in
          1) USER_ANSWER="yes"; break;;
          2) USER_ANSWER="no"; break;;
          3) USER_ANSWER="not sure"; break;;
          *) echo -e "${RED}Invalid option. Please enter 1, 2, or 3.${NC}";;
        esac
      done
    elif [[ "$QUESTION_TYPE" == "date" ]]; then
      echo -e "${YELLOW}Enter a date (YYYY-MM-DD):${NC}"
      while true; do
        read -r -p "> " USER_ANSWER
        if [[ "$USER_ANSWER" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
          break
        else
          echo -e "${RED}Invalid date format. Please use YYYY-MM-DD format.${NC}"
        fi
      done
    elif [[ "$QUESTION_TYPE" == "scale" ]]; then
      echo -e "1. Not at all"
      echo -e "2. Slightly"
      echo -e "3. Moderately"
      echo -e "4. Significantly"
      echo -e "5. Very strongly"
      echo -e "${YELLOW}Enter your answer (1-5):${NC}"

      while true; do
        read -r -p "> " answer_num
        if [[ "$answer_num" =~ ^[1-5]$ ]]; then
          USER_ANSWER="$answer_num"
          break
        else
          echo -e "${RED}Invalid option. Please enter a number between 1 and 5.${NC}"
        fi
      done
    else
      # Default to text input for other question types
      echo -e "${YELLOW}Enter your answer:${NC}"
      read -r -p "> " USER_ANSWER
    fi

    echo -e "${GREEN}You answered: $USER_ANSWER${NC}"

    # Submit answer
    ANSWER_CMD="curl -s -X POST ${API_URL}/questionnaire/${QUESTIONNAIRE_ID}/answer -H 'Content-Type: application/json' -H 'Authorization: Bearer ${SESSION_TOKEN}' -d '{\"question_id\": \"$CURRENT_QUESTION_ID\", \"answer\": \"$USER_ANSWER\"}'"
    ANSWER_RESPONSE=$(execute_curl "$ANSWER_CMD")

    # Check for WebSocket updates
    if [[ $WS_ENABLED -eq 0 ]]; then
      echo -e "${CYAN}Checking for real-time updates...${NC}"
      sleep 1
      WS_MESSAGES=$(read_websocket_messages)

      if [[ ! -z "$WS_MESSAGES" ]]; then
        echo -e "${MAGENTA}REAL-TIME UPDATES:${NC}"
        echo "$WS_MESSAGES" | jq -r '.type + ": " + (.data.message // "Update received")' 2>/dev/null || echo "$WS_MESSAGES"

        # Extract confidence from WebSocket message if available
        WS_CONFIDENCE=$(echo "$WS_MESSAGES" | jq -r '.data.confidence // empty' 2>/dev/null)
        if [[ ! -z "$WS_CONFIDENCE" && "$WS_CONFIDENCE" != "null" ]]; then
          CURRENT_CONFIDENCE=$WS_CONFIDENCE
          echo -e "${CYAN}Updated Confidence Score: ${CURRENT_CONFIDENCE}%${NC}"
        fi
      fi
    fi

    # Check if we have more questions
    NEXT_QUESTION=$(echo "$ANSWER_RESPONSE" | jq -r '.next_question.text')
    NEXT_QUESTION_ID=$(echo "$ANSWER_RESPONSE" | jq -r '.next_question.id')

    # Update confidence from HTTP response if available
    RESPONSE_CONFIDENCE=$(echo "$ANSWER_RESPONSE" | jq -r '.current_confidence')
    if [[ ! -z "$RESPONSE_CONFIDENCE" && "$RESPONSE_CONFIDENCE" != "null" ]]; then
      CURRENT_CONFIDENCE=$RESPONSE_CONFIDENCE
    fi

    # If no more questions, break the loop
    if [[ "$NEXT_QUESTION" == "null" || -z "$NEXT_QUESTION" ]]; then
      echo -e "${GREEN}Questionnaire completed!${NC}"
      break
    fi

    CURRENT_QUESTION="$NEXT_QUESTION"
    CURRENT_QUESTION_ID="$NEXT_QUESTION_ID"
    QUESTION_NUMBER=$((QUESTION_NUMBER + 1))
  done

  # Complete the questionnaire
  display_step "10" "Complete Questionnaire" "Finalizing questionnaire answers"
  COMPLETE_CMD="curl -s -X POST ${API_URL}/questionnaire/complete -H 'Content-Type: application/json' -H 'Authorization: Bearer ${SESSION_TOKEN}' -d '{\"questionnaire_id\": \"$QUESTIONNAIRE_ID\"}'"
  COMPLETE_RESPONSE=$(execute_curl "$COMPLETE_CMD")

  # Wait for final WebSocket updates
  if [[ $WS_ENABLED -eq 0 ]]; then
    echo -e "${CYAN}Waiting for final updates...${NC}"
    sleep 2
    WS_MESSAGES=$(read_websocket_messages)

    if [[ ! -z "$WS_MESSAGES" ]]; then
      echo -e "${MAGENTA}FINAL UPDATES:${NC}"
      echo "$WS_MESSAGES" | jq -r '.type + ": " + (.data.message // "Update received")' 2>/dev/null || echo "$WS_MESSAGES"
    fi
  fi

  # Close WebSocket connection
  close_websocket_connection

  return 0
}
```

### 3. Enhance Birth Time Rectification with WebSockets

Modify the rectify_birth_time function to use WebSockets for real-time progress updates:

```bash
rectify_birth_time() {
  display_step "11" "Birth Time Rectification" "Processing birth time rectification with real-time updates"

  # Check if we have necessary data
  if [[ -z "$CHART_ID" || -z "$QUESTIONNAIRE_ID" ]]; then
    echo -e "${RED}Error: Missing chart ID or questionnaire ID. Please complete previous steps first.${NC}"
    return 1
  fi

  # Check if we have a session token
  if [[ -z "$SESSION_TOKEN" ]]; then
    echo -e "${RED}Error: No session token available. Please initialize a session first.${NC}"
    return 1
  fi

  # Establish WebSocket connection for real-time updates
  establish_websocket_connection
  WS_ENABLED=$?

  # Start rectification process
  echo -e "${YELLOW}Starting birth time rectification process...${NC}"
  echo -e "${YELLOW}This may take a few moments. Real-time updates will be displayed.${NC}"

  RECTIFY_CMD="curl -s -X POST ${API_URL}/chart/rectify -H 'Content-Type: application/json' -H 'Authorization: Bearer ${SESSION_TOKEN}' -d '{\"chart_id\": \"$CHART_ID\", \"questionnaire_id\": \"$QUESTIONNAIRE_ID\"}'"

  # Execute the command but don't wait for response yet
  $RECTIFY_CMD > /tmp/rectify_response_$$.txt &
  RECTIFY_PID=$!

  # Monitor WebSocket for progress updates while rectification is running
  if [[ $WS_ENABLED -eq 0 ]]; then
    echo -e "\n${BLUE}==================================================${NC}"
    echo -e "${BLUE}             RECTIFICATION PROGRESS              ${NC}"
    echo -e "${BLUE}==================================================${NC}"

    PROGRESS=0
    while ps -p $RECTIFY_PID > /dev/null && [[ $PROGRESS -lt 100 ]]; do
      sleep 1
      WS_MESSAGES=$(read_websocket_messages)

      if [[ ! -z "$WS_MESSAGES" ]]; then
        # Try to extract progress information
        EVENT_TYPE=$(echo "$WS_MESSAGES" | jq -r '.type // empty' 2>/dev/null)

        if [[ "$EVENT_TYPE" == "rectification_progress" ]]; then
          PROGRESS=$(echo "$WS_MESSAGES" | jq -r '.data.progress // 0' 2>/dev/null)
          MESSAGE=$(echo "$WS_MESSAGES" | jq -r '.data.message // "Processing..."' 2>/dev/null)

          # Display progress bar
          PROGRESS_BAR=""
          PROGRESS_INT=${PROGRESS%.*}
          BAR_WIDTH=50
          COMPLETED_WIDTH=$((PROGRESS_INT * BAR_WIDTH / 100))
          REMAINING_WIDTH=$((BAR_WIDTH - COMPLETED_WIDTH))

          for ((i=0; i<COMPLETED_WIDTH; i++)); do
            PROGRESS_BAR="${PROGRESS_BAR}█"
          done

          for ((i=0; i<REMAINING_WIDTH; i++)); do
            PROGRESS_BAR="${PROGRESS_BAR}░"
          done

          echo -ne "\r${CYAN}[${PROGRESS_BAR}] ${PROGRESS}% - ${MESSAGE}${NC}"
        fi
      fi
    done

    # Ensure we end with a newline
    echo ""
  else
    echo -e "${YELLOW}Waiting for rectification to complete...${NC}"
    wait $RECTIFY_PID
  fi

  # Get the response
  RECTIFY_RESPONSE=$(cat /tmp/rectify_response_$$.txt)
  rm -f /tmp/rectify_response_$$.txt

  # Process the response
  echo -e "${GREEN}RESPONSE:${NC}"
  echo "$RECTIFY_RESPONSE" | jq . 2>/dev/null || echo "$RECTIFY_RESPONSE"

  RECTIFIED_TIME=$(echo "$RECTIFY_RESPONSE" | jq -r '.rectified_time')
  RECTIFICATION_CONFIDENCE=$(echo "$RECTIFY_RESPONSE" | jq -r '.confidence')

  echo -e "\n${BLUE}==================================================${NC}"
  echo -e "${BLUE}             RECTIFICATION RESULTS               ${NC}"
  echo -e "${BLUE}==================================================${NC}"
  echo -e "Original Birth Time: ${YELLOW}$BIRTH_TIME${NC}"
  echo -e "Rectified Birth Time: ${YELLOW}$RECTIFIED_TIME${NC}"
  echo -e "Rectification Confidence: ${YELLOW}$RECTIFICATION_CONFIDENCE%${NC}"

  if (( $(echo "$RECTIFICATION_CONFIDENCE > $VERIFICATION_CONFIDENCE" | bc -l) )); then
    echo -e "${GREEN}The rectification process has IMPROVED confidence by $(echo "$RECTIFICATION_CONFIDENCE - $VERIFICATION_CONFIDENCE" | bc)%${NC}"
  else
    echo -e "${RED}The rectification process has NOT improved confidence.${NC}"
  fi

  # Close WebSocket connection
  close_websocket_connection

  return 0
}
```

### 4. Add WebSocket Testing Function

Add a dedicated function to test WebSocket functionality:

```bash
test_websocket() {
  display_step "WS" "WebSocket Test" "Testing WebSocket connection and real-time updates"

  # Check if we have a session token
  if [[ -z "$SESSION_TOKEN" ]]; then
    echo -e "${RED}Error: No session token available. Please initialize a session first.${NC}"
    return 1
  fi

  # Check if websocat is installed
  if ! command -v websocat &> /dev/null; then
    echo -e "${RED}Error: websocat is not installed. Please install it to test WebSockets.${NC}"
    echo -e "${YELLOW}Installation instructions:${NC}"
    echo -e "  - On macOS: brew install websocat"
    echo -e "  - On Ubuntu/Debian: sudo apt install websocat"
    echo -e "  - Or download from: https://github.com/vi/websocat/releases"
    return 1
  }

  echo -e "${YELLOW}Establishing WebSocket connection to ${API_URL/http:/ws:}/ws/${SESSION_TOKEN}${NC}"
  echo -e "${YELLOW}Press Ctrl+C to exit the WebSocket test${NC}"

  # Connect to WebSocket and display messages in real-time
  websocat -v "${API_URL/http:/ws:}/ws/${SESSION_TOKEN}" \
    --header="Authorization: Bearer ${SESSION_TOKEN}" | \
    while read -r line; do
      echo -e "${MAGENTA}RECEIVED:${NC}"
      echo "$line" | jq . 2>/dev/null || echo "$line"
      echo ""
    done

  echo -e "${GREEN}WebSocket test completed${NC}"
  return 0
}
```

### 5. Update Main Menu

Add WebSocket-specific options to the main menu:

```bash
# Main menu loop
while true; do
  # Clear screen for menu
  clear

  # Display menu
  echo -e "\n${BLUE}==================================================${NC}"
  echo -e "${BLUE}             BIRTH TIME RECTIFIER               ${NC}"
  echo -e "${BLUE}==================================================${NC}"
  echo -e "1. Run Full Test Sequence"
  echo -e "2. Session Initialization"
  echo -e "3. Geocode Location"
  echo -e "4. Validate Birth Details"
  echo -e "5. Generate Chart"
  echo -e "6. Retrieve Chart"
  echo -e "7. Start Questionnaire (with WebSocket)"
  echo -e "8. Rectify Birth Time (with WebSocket)"
  echo -e "9. Compare Charts"
  echo -e "10. Export Chart"
  echo -e "11. Check API Connectivity"
  echo -e "12. Test WebSocket Connection"
  echo -e "0. Exit"
  echo -e "${BLUE}==================================================${NC}"
  echo -e "${YELLOW}Enter your choice (0-12):${NC}"

  # Get user input
  read -r -p "> " choice

  # Check for empty input
  if [[ -z "$choice" ]]; then
    continue
  fi

  # Validate numeric input
  if [[ ! "$choice" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Invalid option. Please enter a numeric value between 0 and 12.${NC}"
    sleep 2
    continue
  fi

  # Process valid choice
  case $choice in
    0)
      echo -e "${GREEN}Exiting...${NC}"
      exit 0
      ;;
    1) run_full_sequence ;;
    2) initialize_session ;;
    3) geocode_location ;;
    4) validate_birth_details ;;
    5) generate_chart ;;
    6) retrieve_chart ;;
    7) handle_questionnaire ;;
    8) rectify_birth_time ;;
    9) compare_charts ;;
    10) export_chart ;;
    11) check_api_availability ;;
    12) test_websocket ;;
    *)
      echo -e "${RED}Invalid option. Please enter a number between 0 and 12.${NC}"
      sleep 2
      continue
      ;;
  esac

  # Wait before returning to menu
  echo -e "\n${YELLOW}Press Enter to return to main menu...${NC}"
  read -r
done
```

### 6. Add Dependencies Check

Add a check for the required WebSocket client tool:

```bash
# Check for required dependencies
check_dependencies() {
  MISSING_DEPS=0

  # Check for jq
  if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed. Please install jq before running this script.${NC}"
    echo -e "Install instructions: https://stedolan.github.io/jq/download/"
    MISSING_DEPS=1
  fi

  # Check for bc
  if ! command -v bc &> /dev/null; then
    echo -e "${RED}Error: bc is not installed. Please install bc before running this script.${NC}"
    echo -e "Install instructions: Run 'sudo apt-get install bc' on Debian/Ubuntu or 'brew install bc' on macOS."
    MISSING_DEPS=1
  fi

  # Check for websocat (for WebSocket support)
  if ! command -v websocat &> /dev/null; then
    echo -e "${YELLOW}Warning: websocat is not installed. WebSocket features will be disabled.${NC}"
    echo -e "Install instructions:"
    echo -e "  - On macOS: brew install websocat"
    echo -e "  - On Ubuntu/Debian: sudo apt install websocat"
    echo -e "  - Or download from: https://github.com/vi/websocat/releases"
    echo -e "${YELLOW}The script will continue with limited functionality.${NC}"
    WS_SUPPORT=false
  else
    WS_SUPPORT=true
    echo -e "${GREEN}WebSocket support is enabled.${NC}"
  fi

  if [[ $MISSING_DEPS -eq 1 ]]; then
    exit 1
  fi
}
```

### 7. Update Script Initialization

Update the script initialization to include the new dependencies check:

```bash
# Main program
clear
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  BIRTH TIME RECTIFIER API TEST SEQUENCE RUNNER   ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "${YELLOW}Testing against API URL: ${API_URL}${NC}"

# Check dependencies
check_dependencies

# Check API availability before starting
check_api_availability
if [ $? -ne 0 ]; then
  echo -e "${RED}WARNING: API may not be available. Some functions may not work.${NC}"
fi

echo -e "${GREEN}Press Enter to continue...${NC}"
read -r
```

## Implementation Approach

### Incremental Development:

- First, add the WebSocket client functionality and test it independently
- Then integrate it with the questionnaire and rectification functions
- Finally, update the main menu and add the dependencies check

### Testing Strategy:

- Test each WebSocket-enhanced function individually
- Verify real-time updates are displayed correctly
- Ensure the script handles connection failures gracefully

## Benefits of This Implementation

- **Real-Time Progress Monitoring**: Users can see progress updates as they happen, providing a better testing experience.

- **Comprehensive Testing**: The enhanced script tests both HTTP endpoints and WebSocket functionality, ensuring complete coverage of the application's features.

- **Improved Debugging**: Real-time updates make it easier to identify issues in the application's WebSocket implementation.

- **Sequence Flow Verification**: The script follows the exact sequence described in the sequence diagram, ensuring all steps are tested properly.
