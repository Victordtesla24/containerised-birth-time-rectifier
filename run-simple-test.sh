#!/bin/bash

# Main entry point for the modular test script
# This script orchestrates the testing process following the sequence diagram

# Get the directory of this script
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Set API and WebSocket URLs
API_URL="http://localhost:9000/api/v1"
WS_URL="ws://localhost:9000/ws/v1"

# Source configuration
source "$SCRIPT_DIR/test_scripts/config/defaults.conf"

# Source library modules
source "$SCRIPT_DIR/test_scripts/lib/common.sh"
source "$SCRIPT_DIR/test_scripts/lib/api_client.sh"
source "$SCRIPT_DIR/test_scripts/lib/websocket_client.sh"
source "$SCRIPT_DIR/test_scripts/lib/chart_operations.sh"
source "$SCRIPT_DIR/test_scripts/lib/questionnaire_operations.sh"
source "$SCRIPT_DIR/test_scripts/lib/validation.sh"

# Global variables for interactive mode
LAST_CHART_ID=""
LAST_RECTIFIED_CHART_ID=""

# Print banner
print_banner() {
  echo -e "${BOLD}${CYAN}"
  echo -e "========================================================"
  echo -e "               Birth Time Rectifier Test Runner         "
  echo -e "========================================================"
  echo -e "${NC}"
  echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
  echo -e "API URL: ${BLUE}${API_URL}${NC}"
  echo -e "WebSocket URL: ${BLUE}${WS_URL}${NC}"
  echo -e "Log File: ${LOG_FILE}"
  echo -e ""
}

# Function to prompt for user input with validation
get_user_input() {
  local prompt="$1"
  local validation_func="$2"
  local validation_args="${@:3}"
  local input=""
  local valid=false

  while [[ "$valid" != "true" ]]; do
    read -p "$prompt" input

    if [[ -z "$input" ]]; then
      echo -e "${RED}Input cannot be empty. Please try again.${NC}"
      continue
    fi

    if [[ -n "$validation_func" ]]; then
      if $validation_func "$input" $validation_args; then
        valid=true
      else
        echo -e "${RED}Invalid input. Please try again.${NC}"
      fi
    else
      valid=true
    fi
  done

  echo "$input"
}

# Function to validate date format
validate_date_format() {
  local date="$1"
  if [[ ! "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo -e "${RED}Invalid date format. Please use YYYY-MM-DD format.${NC}"
    return 1
  fi
  return 0
}

# Function to validate time format
validate_time_format() {
  local time="$1"
  if [[ ! "$time" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
    echo -e "${RED}Invalid time format. Please use HH:MM:SS format.${NC}"
    return 1
  fi
  return 0
}

# Run the full sequence test following the sequence diagram
run_full_sequence_test() {
  echo -e "${BOLD}${CYAN}Running full sequence test following the sequence diagram...${NC}"

  # Step 1: Initialize session
  echo -e "\n${BOLD}${YELLOW}Step 1: Initialize Session${NC}"
  echo -e "Initializing session with the API..."

  if ! init_session; then
    log_message "FATAL" "Failed to initialize session, exiting"
    return 1
  fi

  echo -e "${GREEN}Session initialized successfully with token: ${SESSION_TOKEN}${NC}"

  # Step 2: Enter location (Geocode)
  echo -e "\n${BOLD}${YELLOW}Step 2: Location Entry${NC}"
  echo -e "Please enter the birth city:"
  local location=$(get_user_input "Birth City: ")

  echo -e "Sending geocode request for location: ${location}"
  local geocode_data="{\"query\": \"$location\"}"
  local geocode_response=$(api_request "POST" "/geocode" "$geocode_data")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Geocode request failed"
    return 1
  fi

  # Extract coordinates from response
  local latitude=$(echo "$geocode_response" | jq -r '.results[0].latitude')
  local longitude=$(echo "$geocode_response" | jq -r '.results[0].longitude')
  local formatted_location=$(echo "$geocode_response" | jq -r '.results[0].formatted_address')

  echo -e "${GREEN}Location found: $formatted_location${NC}"
  echo -e "${GREEN}Coordinates: Lat $latitude, Long $longitude${NC}"

  # Step 3: Enter birth details
  echo -e "\n${BOLD}${YELLOW}Step 3: Birth Details Entry${NC}"
  echo -e "Please enter the birth date and time:"

  local birth_date=$(get_user_input "Birth Date (YYYY-MM-DD): " validate_date_format)
  local birth_time=$(get_user_input "Birth Time (HH:MM:SS): " validate_time_format)
  local name=$(get_user_input "Name: ")

  # Validate birth details
  echo -e "Validating birth details..."

  # Extract timezone from geocode response or use a default
  local timezone=$(echo "$geocode_response" | jq -r '.results[0].timezone // "UTC"')

  local birth_data="{
    \"name\": \"$name\",
    \"birth_date\": \"$birth_date\",
    \"birth_time\": \"$birth_time\",
    \"latitude\": $latitude,
    \"longitude\": $longitude,
    \"location\": \"$formatted_location\",
    \"timezone\": \"$timezone\"
  }"

  local validation_response=$(api_request "POST" "/chart/validate" "$birth_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Birth details validation failed"
    return 1
  fi

  local is_valid=$(echo "$validation_response" | jq -r '.valid // false')
  if [[ "$is_valid" != "true" ]]; then
    local error_message=$(echo "$validation_response" | jq -r '.message // "Unknown validation error"')
    echo -e "${RED}Validation failed: $error_message${NC}"
    return 1
  fi

  echo -e "${GREEN}Birth details validated successfully${NC}"

  # Step 4: Generate chart
  echo -e "\n${BOLD}${YELLOW}Step 4: Generate Chart${NC}"
  echo -e "Generating chart with OpenAI verification..."

  # Add verify_with_openai flag to the request
  local chart_data="{
    \"name\": \"$name\",
    \"birth_date\": \"$birth_date\",
    \"birth_time\": \"$birth_time\",
    \"latitude\": $latitude,
    \"longitude\": $longitude,
    \"location\": \"$formatted_location\",
    \"timezone\": \"$timezone\",
    \"verify_with_openai\": true
  }"

  local chart_response=$(api_request "POST" "/chart/generate" "$chart_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Chart generation failed"
    return 1
  fi

  local chart_id=$(echo "$chart_response" | jq -r '.chart_id')
  local verification_status=$(echo "$chart_response" | jq -r '.verification.verified // false')
  local confidence=$(echo "$chart_response" | jq -r '.verification.confidence // 0')

  echo -e "${GREEN}Chart generated successfully with ID: $chart_id${NC}"
  echo -e "${GREEN}Verification status: $verification_status, Confidence: $confidence%${NC}"

  # Step 5: View chart
  echo -e "\n${BOLD}${YELLOW}Step 5: View Chart${NC}"
  echo -e "Retrieving chart data..."

  local chart_details=$(api_request "GET" "/chart/$chart_id" "{}")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to retrieve chart data"
    return 1
  fi

  echo -e "${GREEN}Chart retrieved successfully${NC}"
  echo -e "Chart details:"
  echo "$chart_details" | jq '.'

  # Step 6: Answer questionnaire
  echo -e "\n${BOLD}${YELLOW}Step 6: Answer Questionnaire${NC}"
  echo -e "Starting interactive questionnaire session..."

  # Initialize questionnaire
  echo -e "Creating questionnaire for chart ID: $chart_id"
  local questionnaire_data="{\"chart_id\": \"$chart_id\"}"
  local questionnaire_response=$(api_request "POST" "/questionnaire" "$questionnaire_data")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create questionnaire"
    echo -e "${RED}Failed to create questionnaire. Moving to rectification with mock data.${NC}"
    local questionnaire_id="mock_questionnaire_id"
    goto_rectification_step=true
  else
    local questionnaire_id=$(echo "$questionnaire_response" | jq -r '.id // empty')
    if [[ -z "$questionnaire_id" ]]; then
      log_message "ERROR" "Failed to extract questionnaire ID from response"
      echo -e "${RED}Failed to extract questionnaire ID. Moving to rectification with mock data.${NC}"
      local questionnaire_id="mock_questionnaire_id"
      goto_rectification_step=true
    else
      echo -e "${GREEN}Questionnaire created with ID: $questionnaire_id${NC}"
      goto_rectification_step=false
    fi
  fi

  # Try WebSocket connection for real-time questionnaire if websocat is available
  local use_websocket=false
  if [[ "$goto_rectification_step" != "true" && "$WS_SUPPORT" == "true" ]]; then
    echo -e "Establishing WebSocket connection for real-time interaction..."
    if establish_connection; then
      use_websocket=true
      echo -e "${GREEN}WebSocket connection established successfully. Using real-time mode.${NC}"
    else
      log_message "INFO" "WebSocket connection failed, falling back to REST API mode"
      echo -e "${YELLOW}WebSocket connection failed. Falling back to REST API mode.${NC}"
    fi
  elif [[ "$WS_SUPPORT" != "true" ]]; then
    echo -e "${YELLOW}WebSocket support not available. Using REST API mode for questionnaire.${NC}"
  fi

  # Skip the questionnaire if we're going directly to rectification
  if [[ "$goto_rectification_step" != "true" ]]; then

    echo -e "\n${BOLD}Interactive Birth Time Rectification Questionnaire${NC}"
    echo -e "Please answer the following questions to help rectify the birth time:"
    echo -e "-------------------------------------------------------------------"

    # WebSocket mode for real-time interaction
    if [[ "$use_websocket" == "true" ]]; then
      # Subscribe to questionnaire channel
      local subscribe_msg="{\"type\": \"subscribe\", \"channel\": \"questionnaire_$questionnaire_id\"}"
      if ! send_message "$subscribe_msg"; then
        log_message "ERROR" "Failed to subscribe to questionnaire channel"
        close_connection
        echo -e "${YELLOW}Failed to subscribe to WebSocket channel. Falling back to REST API mode.${NC}"
        use_websocket=false
      else
        # Wait for initial question via WebSocket
        local first_ws_message=$(wait_for_message 10)
        if [[ $? -ne 0 ]]; then
          log_message "ERROR" "Failed to receive initial question via WebSocket"
          close_connection
          echo -e "${YELLOW}Failed to receive initial question via WebSocket. Falling back to REST API mode.${NC}"
          use_websocket=false
        fi
      fi
    fi

    # REST API mode fallback if WebSocket failed or is not available
    if [[ "$use_websocket" != "true" ]]; then
      echo -e "${YELLOW}Using REST API for questionnaire (non-real-time mode)${NC}"

      # Get the first question via REST API
      local next_question_response=$(get_next_question "$questionnaire_id")
      if [[ $? -ne 0 ]]; then
        log_message "ERROR" "Failed to get first question via REST API"
        echo -e "${RED}Failed to get questions. Moving to rectification with mock data.${NC}"
        goto_rectification_step=true
      else
        local current_question=$(echo "$next_question_response" | jq -r '.question // empty')
        local current_question_id=$(echo "$next_question_response" | jq -r '.id // empty')
        local is_complete=$(echo "$next_question_response" | jq -r '.is_complete // false')

        if [[ -z "$current_question" || -z "$current_question_id" ]]; then
          log_message "ERROR" "Failed to extract question details from REST API response"
          echo -e "${RED}Failed to extract question details. Moving to rectification with mock data.${NC}"
          goto_rectification_step=true
        fi
      fi
    fi

    # Process questions in a loop until complete
    local is_complete=false
    local collected_answers=()

    while [[ "$is_complete" != "true" && "$goto_rectification_step" != "true" ]]; do
      # Display the current question
      echo -e "\nQuestion: ${CYAN}$current_question${NC}"
      read -p "Your answer: " user_answer

      # Store the answer for later use in rectification
      collected_answers+=("{\"question_id\": \"$current_question_id\", \"answer\": \"$user_answer\"}")

      if [[ "$use_websocket" == "true" ]]; then
        # Submit the answer via WebSocket
        local answer_msg="{\"type\": \"answer\", \"questionnaire_id\": \"$questionnaire_id\", \"question_id\": \"$current_question_id\", \"answer\": \"$user_answer\"}"

        if ! send_message "$answer_msg"; then
          log_message "ERROR" "Failed to send answer via WebSocket"
          close_connection
          echo -e "${YELLOW}Failed to send answer via WebSocket. Falling back to REST API.${NC}"
          use_websocket=false

          # Submit the answer via REST API instead
          local answer_response=$(submit_answer "$questionnaire_id" "$current_question_id" "$user_answer")
          if [[ $? -ne 0 ]]; then
            log_message "ERROR" "Failed to submit answer via REST API"
            echo -e "${RED}Failed to submit answer. Moving to rectification with collected answers.${NC}"
            break
          fi
        else
          # Wait for next question via WebSocket
          local next_ws_message=$(wait_for_message 10)
          if [[ $? -ne 0 ]]; then
            log_message "ERROR" "Failed to receive next question via WebSocket"
            close_connection
            echo -e "${YELLOW}Failed to receive next question via WebSocket. Falling back to REST API.${NC}"
            use_websocket=false

            # Get next question via REST API
            local next_question_response=$(get_next_question "$questionnaire_id")
            if [[ $? -ne 0 ]]; then
              log_message "ERROR" "Failed to get next question via REST API"
              echo -e "${RED}Failed to get next question. Moving to rectification with collected answers.${NC}"
              break
            else
              current_question=$(echo "$next_question_response" | jq -r '.question // empty')
              current_question_id=$(echo "$next_question_response" | jq -r '.id // empty')
              is_complete=$(echo "$next_question_response" | jq -r '.is_complete // false')
            fi
          else
            # Check if questionnaire is complete via WebSocket
            local complete_flag=$(echo "$next_ws_message" | jq -r '.complete // false')
            if [[ "$complete_flag" == "true" ]]; then
              is_complete=true
              echo -e "\n${GREEN}Questionnaire completed successfully!${NC}"
              break
            fi

            # Extract next question from WebSocket message
            current_question=$(echo "$next_ws_message" | jq -r '.question // empty')
            current_question_id=$(echo "$next_ws_message" | jq -r '.id // empty')
          fi
        fi
      else
        # Submit the answer via REST API
        local answer_response=$(submit_answer "$questionnaire_id" "$current_question_id" "$user_answer")
        if [[ $? -ne 0 ]]; then
          log_message "ERROR" "Failed to submit answer via REST API"
          echo -e "${RED}Failed to submit answer. Moving to rectification with collected answers.${NC}"
          break
        fi

        # Check if questionnaire is complete via REST API
        local status=$(echo "$answer_response" | jq -r '.status // ""')
        if [[ "$status" == "complete" ]]; then
          is_complete=true
          echo -e "\n${GREEN}Questionnaire completed successfully!${NC}"
          break
        fi

        # Get next question via REST API
        local next_question_response=$(get_next_question "$questionnaire_id")
        if [[ $? -ne 0 ]]; then
          log_message "ERROR" "Failed to get next question via REST API"
          echo -e "${RED}Failed to get next question. Moving to rectification with collected answers.${NC}"
          break
        fi

        current_question=$(echo "$next_question_response" | jq -r '.question // empty')
        current_question_id=$(echo "$next_question_response" | jq -r '.id // empty')
        is_complete=$(echo "$next_question_response" | jq -r '.is_complete // false')

        if [[ "$is_complete" == "true" ]]; then
          echo -e "\n${GREEN}Questionnaire completed successfully!${NC}"
          break
        fi
      fi
    done

    # Complete the questionnaire
    if [[ "$is_complete" != "true" && "$goto_rectification_step" != "true" ]]; then
      local completion_response=$(complete_questionnaire "$questionnaire_id")
      if [[ $? -ne 0 ]]; then
        log_message "ERROR" "Failed to complete questionnaire"
        echo -e "${YELLOW}Failed to complete questionnaire. Proceeding with collected answers.${NC}"
      else
        echo -e "${GREEN}Questionnaire completed and submitted successfully!${NC}"
      fi
    fi

    # Close WebSocket connection if it was used
    if [[ "$use_websocket" == "true" ]]; then
      # Unsubscribe and close WebSocket
      local unsubscribe_msg="{\"type\": \"unsubscribe\", \"channel\": \"questionnaire_$questionnaire_id\"}"
      send_message "$unsubscribe_msg"
      close_connection
    fi

    # Prepare answers for rectification
    if [[ ${#collected_answers[@]} -gt 0 ]]; then
      # Join the collected answers into a JSON array
      mock_answers='"answers": ['
      local first=true
      for answer in "${collected_answers[@]}"; do
        if [[ "$first" == "true" ]]; then
          mock_answers+="$answer"
          first=false
        else
          mock_answers+=",$answer"
        fi
      done
      mock_answers+='],'
    else
      # If no answers were collected, use empty array
      mock_answers='"answers": [],'
    fi
  fi

  # Step 7: Birth Time Rectification
  echo -e "\n${BOLD}${YELLOW}Step 7: Birth Time Rectification${NC}"
  echo -e "Starting birth time rectification process..."

  # Create mock answers if we skipped the questionnaire
  local mock_answers=""
  if [[ "$goto_rectification_step" == "true" ]]; then
    echo -e "${YELLOW}Creating mock answers for rectification since questionnaire was skipped${NC}"
    mock_answers='"answers": [
      {"question_id": "q1", "answer": "Yes"},
      {"question_id": "q2", "answer": "No"},
      {"question_id": "q3", "answer": "Maybe"}
    ],'
  else
    # In a real scenario, we would collect the answers from the questionnaire
    # For now, we'll use a simple placeholder
    mock_answers='"answers": [],'
  fi

  local rectify_data="{
    \"chart_id\": \"$chart_id\",
    \"questionnaire_id\": \"$questionnaire_id\",
    $mock_answers
    \"include_details\": true
  }"
  local rectify_response=$(api_request "POST" "/chart/rectify" "$rectify_data")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to start rectification process"
    return 1
  fi

  # Debug the response
  log_message "DEBUG" "Rectification response: $rectify_response"
  echo -e "Rectification API response: $rectify_response"

  # The API returns rectified_chart_id directly instead of a rectification_id
  local rectified_chart_id=$(echo "$rectify_response" | jq -r '.rectified_chart_id // empty')
  if [[ -z "$rectified_chart_id" ]]; then
    log_message "ERROR" "Failed to extract rectified chart ID from response"
    echo -e "${RED}Failed to extract rectified chart ID. API response: $rectify_response${NC}"
    return 1
  fi

  # Extract other rectification details
  local rectified_time=$(echo "$rectify_response" | jq -r '.rectified_time // empty')
  local confidence_score=$(echo "$rectify_response" | jq -r '.confidence_score // "0"')
  local explanation=$(echo "$rectify_response" | jq -r '.explanation // "No explanation provided"')

  echo -e "${GREEN}Rectification completed successfully!${NC}"
  echo -e "${GREEN}Rectified chart ID: $rectified_chart_id${NC}"
  echo -e "${GREEN}Rectified time: $rectified_time${NC}"
  echo -e "${GREEN}Confidence score: $confidence_score%${NC}"
  echo -e "${GREEN}Explanation: $explanation${NC}"

  # No need to poll for status since the API returns the completed result immediately
  if [[ -z "$rectified_chart_id" ]]; then
    log_message "ERROR" "Failed to extract rectified chart ID from response"
    return 1
  fi

  echo -e "${GREEN}Rectification completed successfully!${NC}"
  echo -e "Rectified chart ID: $rectified_chart_id"

  # Step 8: Compare charts
  echo -e "\n${BOLD}${YELLOW}Step 8: Compare Charts${NC}"
  echo -e "Comparing original and rectified charts..."

  local compare_response=$(api_request "GET" "/chart/compare?chart1_id=$chart_id&chart2_id=$rectified_chart_id" "{}")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to compare charts"
    return 1
  fi

  echo -e "${GREEN}Chart comparison completed successfully${NC}"
  echo -e "Comparison results:"
  echo "$compare_response" | jq '.'

  # Step 9: Export chart
  echo -e "\n${BOLD}${YELLOW}Step 9: Export Chart${NC}"
  echo -e "Exporting rectified chart..."

  local export_data="{\"chart_id\": \"$rectified_chart_id\", \"format\": \"pdf\"}"
  local export_response=$(api_request "POST" "/chart/export" "$export_data")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to export chart"
    return 1
  fi

  local download_url=$(echo "$export_response" | jq -r '.download_url // empty')
  if [[ -z "$download_url" ]]; then
    log_message "ERROR" "Failed to extract download URL from response"
    return 1
  fi

  echo -e "${GREEN}Chart exported successfully${NC}"
  echo -e "Download URL: $download_url"

  # Download the exported file
  echo -e "Downloading exported chart..."
  local download_response=$(curl -s -o "chart_export.pdf" "$API_URL$download_url")

  if [[ -f "chart_export.pdf" ]]; then
    echo -e "${GREEN}Chart downloaded successfully to chart_export.pdf${NC}"
  else
    echo -e "${RED}Failed to download chart export${NC}"
  fi

  echo -e "\n${BOLD}${GREEN}Full sequence test completed successfully!${NC}"
  return 0
}

# Main test orchestration function
run_tests() {
  local test_type="$1"

  log_message "INFO" "Starting tests of type: $test_type"

  # Initialize session
  if ! init_session; then
    log_message "FATAL" "Failed to initialize session, exiting"
    exit 1
  fi

  case "$test_type" in
    "sequence")
      run_full_sequence_test
      ;;
    "api")
      run_api_tests
      ;;
    "websocket")
      run_websocket_tests
      ;;
    "chart")
      run_chart_tests
      ;;
    "questionnaire")
      run_questionnaire_tests
      ;;
    "interactive")
      run_interactive_mode
      ;;
    "all")
      run_full_sequence_test
      ;;
    *)
      log_message "ERROR" "Unknown test type: $test_type"
      show_help
      exit 1
      ;;
  esac

  log_message "INFO" "Tests completed for type: $test_type"
}

# Run interactive mode with real-time WebSocket communication
run_interactive_mode() {
  log_message "INFO" "Starting interactive mode with real-time WebSocket communication"

  # Check if WebSocket support is available
  if [[ "$WS_SUPPORT" != "true" ]]; then
    log_message "FATAL" "WebSocket support is required for interactive mode"
    echo -e "${RED}WebSocket support is required for interactive mode.${NC}"
    echo -e "${YELLOW}Please install websocat and try again.${NC}"
    exit 1
  fi

  # Display interactive menu
  echo -e "\n${BOLD}${CYAN}Birth Time Rectifier - Interactive Mode${NC}"
  echo -e "${CYAN}=======================================${NC}\n"

  # Main interactive loop
  while true; do
    echo -e "\n${BOLD}Select an option:${NC}"
    echo -e "1. ${CYAN}Create a new chart${NC}"
    echo -e "2. ${CYAN}Run interactive questionnaire${NC}"
    echo -e "3. ${CYAN}Rectify birth time${NC}"
    echo -e "4. ${CYAN}Compare charts${NC}"
    echo -e "5. ${CYAN}Export chart${NC}"
    echo -e "0. ${RED}Exit${NC}"

    read -p "Enter your choice (0-5): " choice

    case "$choice" in
      0)
        echo -e "\n${YELLOW}Exiting interactive mode...${NC}"
        return 0
        ;;
      1)
        run_interactive_chart_creation
        ;;
      2)
        run_interactive_questionnaire
        ;;
      3)
        run_interactive_rectification
        ;;
      4)
        run_interactive_chart_comparison
        ;;
      5)
        run_interactive_chart_export
        ;;
      *)
        echo -e "${RED}Invalid choice. Please try again.${NC}"
        ;;
    esac
  done
}

# Interactive chart creation
run_interactive_chart_creation() {
  echo -e "\n${BOLD}${CYAN}Create a New Chart${NC}"
  echo -e "${CYAN}===================${NC}\n"

  # Get user input for chart creation
  read -p "Enter name: " name
  read -p "Enter birth date (YYYY-MM-DD): " birth_date
  read -p "Enter birth time (HH:MM:SS): " birth_time
  read -p "Enter location (e.g., New York, NY, USA): " location

  # Geocode the location
  echo -e "\n${YELLOW}Geocoding location...${NC}"
  local geocode_data="{\"query\": \"$location\"}"
  local geocode_response=$(api_request "POST" "/geocode" "$geocode_data")

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to geocode location. Please try again.${NC}"
    return 1
  fi

  # Extract coordinates
  local latitude=$(echo "$geocode_response" | jq -r '.results[0].latitude // empty')
  local longitude=$(echo "$geocode_response" | jq -r '.results[0].longitude // empty')

  if [[ -z "$latitude" || -z "$longitude" ]]; then
    echo -e "${RED}Failed to extract coordinates from geocode response.${NC}"
    return 1
  fi

  echo -e "${GREEN}Location geocoded successfully:${NC}"
  echo -e "Latitude: $latitude"
  echo -e "Longitude: $longitude"

  # Create the chart
  echo -e "\n${YELLOW}Creating chart...${NC}"
  local chart_data="{
    \"name\": \"$name\",
    \"birth_date\": \"$birth_date\",
    \"birth_time\": \"$birth_time\",
    \"latitude\": $latitude,
    \"longitude\": $longitude,
    \"location\": \"$location\"
  }"

  local chart_response=$(api_request "POST" "/chart/generate" "$chart_data")

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to create chart. Please try again.${NC}"
    return 1
  fi

  # Extract chart ID
  local chart_id=$(echo "$chart_response" | jq -r '.chart_id // empty')

  if [[ -z "$chart_id" ]]; then
    echo -e "${RED}Failed to extract chart ID from response.${NC}"
    return 1
  fi

  echo -e "${GREEN}Chart created successfully with ID: $chart_id${NC}"

  # Store the chart ID for later use
  LAST_CHART_ID="$chart_id"

  return 0
}

# Interactive questionnaire with WebSocket
run_interactive_questionnaire() {
  echo -e "\n${BOLD}${CYAN}Interactive Questionnaire${NC}"
  echo -e "${CYAN}=======================${NC}\n"

  # Check if we have a chart ID
  if [[ -z "$LAST_CHART_ID" ]]; then
    echo -e "${YELLOW}No chart has been created yet.${NC}"
    read -p "Enter chart ID or create a new chart first (c): " input

    if [[ "$input" == "c" ]]; then
      run_interactive_chart_creation
    else
      LAST_CHART_ID="$input"
    fi
  fi

  # Confirm chart ID
  echo -e "\n${YELLOW}Using chart ID: $LAST_CHART_ID${NC}"
  read -p "Continue with this chart? (y/n): " confirm

  if [[ "$confirm" != "y" ]]; then
    echo -e "${YELLOW}Questionnaire cancelled.${NC}"
    return 0
  fi

  # Run the interactive questionnaire with WebSocket
  echo -e "\n${YELLOW}Starting interactive questionnaire...${NC}"

  # Use the WebSocket-based questionnaire function from questionnaire_operations.sh
  if ! run_interactive_questionnaire_from_lib "$LAST_CHART_ID"; then
    echo -e "${RED}Questionnaire failed or was cancelled.${NC}"
    return 1
  fi

  echo -e "${GREEN}Questionnaire completed successfully.${NC}"
  return 0
}

# Interactive birth time rectification
run_interactive_rectification() {
  echo -e "\n${BOLD}${CYAN}Birth Time Rectification${NC}"
  echo -e "${CYAN}=======================${NC}\n"

  # Check if we have a chart ID
  if [[ -z "$LAST_CHART_ID" ]]; then
    echo -e "${YELLOW}No chart has been created yet.${NC}"
    read -p "Enter chart ID or create a new chart first (c): " input

    if [[ "$input" == "c" ]]; then
      run_interactive_chart_creation
    else
      LAST_CHART_ID="$input"
    fi
  fi

  # Confirm chart ID
  echo -e "\n${YELLOW}Using chart ID: $LAST_CHART_ID${NC}"
  read -p "Continue with this chart? (y/n): " confirm

  if [[ "$confirm" != "y" ]]; then
    echo -e "${YELLOW}Rectification cancelled.${NC}"
    return 0
  fi

  # Start the rectification process
  echo -e "\n${YELLOW}Starting birth time rectification...${NC}"

  # First, we need a questionnaire ID
  echo -e "${YELLOW}Creating questionnaire for chart...${NC}"
  local questionnaire_data="{\"chart_id\": \"$LAST_CHART_ID\"}"
  local questionnaire_response=$(api_request "POST" "/questionnaire" "$questionnaire_data")

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to create questionnaire. Rectification cancelled.${NC}"
    return 1
  fi

  # Extract questionnaire ID
  local questionnaire_id=$(echo "$questionnaire_response" | jq -r '.sessionId // empty')

  if [[ -z "$questionnaire_id" ]]; then
    echo -e "${RED}Failed to extract questionnaire ID from response.${NC}"
    return 1
  fi

  echo -e "${GREEN}Questionnaire created with ID: $questionnaire_id${NC}"

  # Run the interactive questionnaire with WebSocket
  echo -e "\n${YELLOW}Starting interactive questionnaire...${NC}"

  # Use the WebSocket-based questionnaire function from questionnaire_operations.sh
  if ! run_interactive_questionnaire_from_lib "$LAST_CHART_ID"; then
    echo -e "${RED}Questionnaire failed or was cancelled. Rectification cancelled.${NC}"
    return 1
  fi

  # Start the rectification process
  echo -e "\n${YELLOW}Initiating birth time rectification...${NC}"

  # Establish WebSocket connection for real-time updates
  if [[ "$CONNECTION_STATE" != "CONNECTED" ]]; then
    if ! establish_connection; then
      echo -e "${RED}Failed to establish WebSocket connection for rectification updates.${NC}"
      return 1
    fi
  fi

  # Subscribe to the rectification channel
  local rectification_channel="rectification_$LAST_CHART_ID"
  if ! subscribe_to_channel "$rectification_channel"; then
    echo -e "${RED}Failed to subscribe to rectification channel.${NC}"
    return 1
  fi

  # Send rectification request
  local rectify_data="{
    \"chart_id\": \"$LAST_CHART_ID\",
    \"questionnaire_id\": \"$questionnaire_id\"
  }"

  local rectify_response=$(api_request "POST" "/chart/rectify" "$rectify_data")

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to initiate rectification process.${NC}"
    unsubscribe_from_channel "$rectification_channel"
    return 1
  fi

  # Extract rectification ID or rectified chart ID
  local rectification_id=$(echo "$rectify_response" | jq -r '.rectification_id // empty')
  local rectified_chart_id=$(echo "$rectify_response" | jq -r '.rectified_chart_id // empty')

  if [[ -z "$rectification_id" && -z "$rectified_chart_id" ]]; then
    echo -e "${RED}Failed to extract rectification details from response.${NC}"
    unsubscribe_from_channel "$rectification_channel"
    return 1
  fi

  # If we got a rectified chart ID immediately, we're done
  if [[ -n "$rectified_chart_id" ]]; then
    echo -e "${GREEN}Rectification completed immediately!${NC}"
    echo -e "${GREEN}Rectified chart ID: $rectified_chart_id${NC}"
    LAST_RECTIFIED_CHART_ID="$rectified_chart_id"
    unsubscribe_from_channel "$rectification_channel"
    return 0
  fi

  # Otherwise, we need to wait for the rectification to complete
  echo -e "${YELLOW}Rectification in progress (ID: $rectification_id)...${NC}"
  echo -e "${YELLOW}Waiting for real-time updates via WebSocket...${NC}"

  # Display a spinner while waiting
  local spinner=('-' '\\' '|' '/')
  local i=0
  local is_complete=false
  local timeout=300  # 5 minutes timeout
  local elapsed=0

  while [[ "$is_complete" != "true" && $elapsed -lt $timeout ]]; do
    echo -ne "\r${YELLOW}Processing${NC} ${spinner[$i]} "
    i=$(( (i+1) % 4 ))

    # Check for messages
    if [[ -s "$WS_DATA_FILE" ]]; then
      local message=$(cat "$WS_DATA_FILE")
      > "$WS_DATA_FILE"  # Clear the file after reading

      # Check if it's a completion message
      if echo "$message" | jq -e '.complete // false' &>/dev/null; then
        is_complete=true
        rectified_chart_id=$(echo "$message" | jq -r '.rectified_chart_id // empty')
        echo -e "\n${GREEN}Rectification completed successfully!${NC}"
        echo -e "${GREEN}Rectified chart ID: $rectified_chart_id${NC}"
        LAST_RECTIFIED_CHART_ID="$rectified_chart_id"
        break
      fi

      # Check if it's a progress update
      local progress=$(echo "$message" | jq -r '.progress // empty')
      if [[ -n "$progress" ]]; then
        echo -e "\r${YELLOW}Rectification progress: $progress%${NC}                    "
      fi
    fi

    sleep 1
    elapsed=$((elapsed+1))
  done

  # Unsubscribe from the channel
  unsubscribe_from_channel "$rectification_channel"

  if [[ "$is_complete" != "true" ]]; then
    echo -e "\n${RED}Rectification timed out after $timeout seconds.${NC}"
    return 1
  fi

  return 0
}

# Interactive chart comparison
run_interactive_chart_comparison() {
  echo -e "\n${BOLD}${CYAN}Chart Comparison${NC}"
  echo -e "${CYAN}================${NC}\n"

  # Check if we have chart IDs
  if [[ -z "$LAST_CHART_ID" ]]; then
    echo -e "${YELLOW}No original chart has been created yet.${NC}"
    read -p "Enter original chart ID or create a new chart first (c): " input

    if [[ "$input" == "c" ]]; then
      run_interactive_chart_creation
    else
      LAST_CHART_ID="$input"
    fi
  fi

  if [[ -z "$LAST_RECTIFIED_CHART_ID" ]]; then
    echo -e "${YELLOW}No rectified chart is available.${NC}"
    read -p "Enter rectified chart ID or run rectification first (r): " input

    if [[ "$input" == "r" ]]; then
      run_interactive_rectification
    else
      LAST_RECTIFIED_CHART_ID="$input"
    fi
  fi

  # Confirm chart IDs
  echo -e "\n${YELLOW}Comparing charts:${NC}"
  echo -e "Original chart ID: $LAST_CHART_ID"
  echo -e "Rectified chart ID: $LAST_RECTIFIED_CHART_ID"
  read -p "Continue with these charts? (y/n): " confirm

  if [[ "$confirm" != "y" ]]; then
    echo -e "${YELLOW}Comparison cancelled.${NC}"
    return 0
  fi

  # Start the comparison process
  echo -e "\n${YELLOW}Comparing charts...${NC}"

  local compare_response=$(api_request "GET" "/chart/compare?chart1_id=$LAST_CHART_ID&chart2_id=$LAST_RECTIFIED_CHART_ID" "{}")

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to compare charts.${NC}"
    return 1
  fi

  # Display comparison results
  echo -e "\n${GREEN}Chart comparison completed successfully!${NC}"

  # Extract and display key differences
  local differences=$(echo "$compare_response" | jq -r '.differences // empty')

  if [[ -n "$differences" ]]; then
    echo -e "\n${CYAN}Key Differences:${NC}"

    # Display birth time difference
    local original_time=$(echo "$compare_response" | jq -r '.chart1.birth_time // "Unknown"')
    local rectified_time=$(echo "$compare_response" | jq -r '.chart2.birth_time // "Unknown"')
    echo -e "Original birth time: ${YELLOW}$original_time${NC}"
    echo -e "Rectified birth time: ${GREEN}$rectified_time${NC}"

    # Display house position differences
    echo -e "\n${CYAN}Planet House Position Changes:${NC}"
    echo "$compare_response" | jq -r '.planet_house_changes[] | "  " + .planet + ": House " + (.original_house|tostring) + " → House " + (.new_house|tostring)' 2>/dev/null || echo "  No house position changes"

    # Display sign position differences
    echo -e "\n${CYAN}Planet Sign Position Changes:${NC}"
    echo "$compare_response" | jq -r '.planet_sign_changes[] | "  " + .planet + ": " + .original_sign + " → " + .new_sign' 2>/dev/null || echo "  No sign position changes"
  else
    echo -e "\n${YELLOW}No significant differences found between the charts.${NC}"
  fi

  return 0
}

# Interactive chart export
run_interactive_chart_export() {
  echo -e "\n${BOLD}${CYAN}Chart Export${NC}"
  echo -e "${CYAN}=============${NC}\n"

  # Check if we have a chart ID
  if [[ -z "$LAST_CHART_ID" && -z "$LAST_RECTIFIED_CHART_ID" ]]; then
    echo -e "${YELLOW}No charts have been created yet.${NC}"
    read -p "Enter chart ID or create a new chart first (c): " input

    if [[ "$input" == "c" ]]; then
      run_interactive_chart_creation
    else
      LAST_CHART_ID="$input"
    fi
  fi

  # Ask which chart to export
  echo -e "\n${YELLOW}Available charts:${NC}"
  if [[ -n "$LAST_CHART_ID" ]]; then
    echo -e "1. Original chart (ID: $LAST_CHART_ID)"
  fi
  if [[ -n "$LAST_RECTIFIED_CHART_ID" ]]; then
    echo -e "2. Rectified chart (ID: $LAST_RECTIFIED_CHART_ID)"
  fi

  read -p "Which chart would you like to export? (1/2): " chart_choice

  local chart_id=""
  if [[ "$chart_choice" == "1" && -n "$LAST_CHART_ID" ]]; then
    chart_id="$LAST_CHART_ID"
  elif [[ "$chart_choice" == "2" && -n "$LAST_RECTIFIED_CHART_ID" ]]; then
    chart_id="$LAST_RECTIFIED_CHART_ID"
  else
    echo -e "${RED}Invalid choice or chart not available.${NC}"
    return 1
  fi

  # Ask for export format
  echo -e "\n${YELLOW}Available export formats:${NC}"
  echo -e "1. PDF"
  echo -e "2. PNG"
  echo -e "3. SVG"

  read -p "Select export format (1-3): " format_choice

  local format=""
  case "$format_choice" in
    1) format="pdf" ;;
    2) format="png" ;;
    3) format="svg" ;;
    *)
      echo -e "${RED}Invalid format choice. Defaulting to PDF.${NC}"
      format="pdf"
      ;;
  esac

  # Start the export process
  echo -e "\n${YELLOW}Exporting chart in $format format...${NC}"

  local export_data="{\"chart_id\": \"$chart_id\", \"format\": \"$format\"}"
  local export_response=$(api_request "POST" "/chart/export" "$export_data")

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to export chart.${NC}"
    return 1
  fi

  # Extract download URL
  local download_url=$(echo "$export_response" | jq -r '.download_url // empty')

  if [[ -z "$download_url" ]]; then
    echo -e "${RED}Failed to extract download URL from response.${NC}"
    return 1
  fi

  echo -e "${GREEN}Chart exported successfully!${NC}"
  echo -e "${GREEN}Download URL: $download_url${NC}"

  # Download the file
  echo -e "\n${YELLOW}Downloading exported file...${NC}"

  local output_file="chart_export.$format"
  curl -s -o "$output_file" "$API_URL$download_url"

  if [[ $? -ne 0 ]]; then
    echo -e "${RED}Failed to download exported file.${NC}"
    return 1
  fi

  echo -e "${GREEN}Chart downloaded successfully to: $output_file${NC}"
  return 0
}

# Function to display help message
show_help() {
  cat << EOF
Usage: run-simple-test.sh [OPTIONS]

A modular testing script for API and WebSocket testing.

Options:
  -h          Show this help message and exit
  -v          Enable verbose output
  -t TYPE     Specify test type (api, websocket, chart, questionnaire, interactive, sequence, all)

Examples:
  run-simple-test.sh -t api         Run API tests only
  run-simple-test.sh -t websocket   Run WebSocket tests only
  run-simple-test.sh -t interactive Run interactive mode with WebSocket
  run-simple-test.sh -t sequence    Run full sequence test
  run-simple-test.sh -t all         Run all tests
  run-simple-test.sh -v             Run with verbose output

EOF
}

# Parse command line arguments
parse_arguments() {
  # Default values
  VERBOSE=false
  TEST_TYPE="all"

  # Parse options
  while getopts ":hvt:" opt; do
    case $opt in
      h)
        show_help
        exit 0
        ;;
      v)
        VERBOSE=true
        log_message "INFO" "Verbose mode enabled"
        ;;
      t)
        TEST_TYPE="$OPTARG"
        log_message "INFO" "Test type set to: $TEST_TYPE"
        ;;
      \?)
        log_message "ERROR" "Invalid option: -$OPTARG"
        show_help
        exit 1
        ;;
      :)
        log_message "ERROR" "Option -$OPTARG requires an argument"
        show_help
        exit 1
        ;;
    esac
  done

  # Validate test type
  case "$TEST_TYPE" in
    "api"|"websocket"|"chart"|"questionnaire"|"interactive"|"sequence"|"all")
      # Valid test type
      ;;
    *)
      log_message "ERROR" "Invalid test type: $TEST_TYPE"
      show_help
      exit 1
      ;;
  esac

  # Export variables
  export VERBOSE
  export TEST_TYPE
}

# Main execution
main() {
  # Print banner
  print_banner

  # Create the test output directory
  mkdir -p "$TEST_OUTPUT_DIR"

  # Parse command line arguments
  parse_arguments "$@"

  # Check dependencies
  if ! check_dependencies; then
    log_message "FATAL" "Dependency check failed, exiting"
    exit 1
  fi

  # Validate environment
  if ! validate_environment; then
    log_message "FATAL" "Environment validation failed, exiting"
    exit 1
  fi

  # Run tests
  run_tests "$TEST_TYPE"

  # Return success
  exit 0
}

# Run main function with all arguments
main "$@"
