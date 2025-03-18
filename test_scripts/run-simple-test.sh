#!/bin/bash

# Main entry point for the modular test script
# This script orchestrates the testing process for the Birth Time Rectifier API

# Get the directory of this script
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Set API and WebSocket URLs
API_URL="http://localhost:9000/api/v1"
WS_URL="ws://localhost:9000/ws/v1"

# Source configuration
source "$SCRIPT_DIR/config/defaults.conf"

# Source library modules
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/api_client.sh"
source "$SCRIPT_DIR/lib/websocket_client.sh"
source "$SCRIPT_DIR/lib/chart_operations.sh"
source "$SCRIPT_DIR/lib/validation.sh"

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

# Function to run the full sequence flow test according to the sequence diagram
run_sequence_test() {
  log_message "INFO" "Starting full sequence flow test according to sequence diagram"

  # Step 1: Session Initialization
  log_message "INFO" "Step 1: Session Initialization"

  if ! init_session; then
    log_message "FATAL" "Failed to initialize session, exiting"
    return 1
  fi

  log_message "INFO" "Session initialized successfully with token: ${SESSION_TOKEN:0:10}..."

  # Step 2: Location/Geocoding
  log_message "INFO" "Step 2: Testing geocoding with sample location"

  # Get location input from user
  echo -e "${YELLOW}Enter a location (e.g., New York, NY):${NC}"
  read location

  # Call API to geocode location
  local geocode_data=$(curl -s "$API_URL/geocode?query=$(urlencode "$location")" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}")

  if ! echo "$geocode_data" | jq -e '.results' > /dev/null; then
    log_message "ERROR" "Geocoding failed: $(echo "$geocode_data" | jq -r '.detail // "Unknown error"')"
    return 1
  fi

  log_message "INFO" "Geocoding successful:"
  log_message "INFO" "$geocode_data"

  # Extract coordinates for later use
  local latitude=$(echo "$geocode_data" | jq -r '.results[0].latitude')
  local longitude=$(echo "$geocode_data" | jq -r '.results[0].longitude')
  local formatted_location=$(echo "$geocode_data" | jq -r '.results[0].formatted_address')

  # Step 3: Birth details validation
  log_message "INFO" "Step 3: Testing birth details validation"

  # Get birth details from user
  echo -e "${YELLOW}Enter name:${NC}"
  read name

  echo -e "${YELLOW}Enter birth date (YYYY-MM-DD):${NC}"
  read birth_date

  echo -e "${YELLOW}Enter birth time (HH:MM):${NC}"
  read birth_time

  # Build validation request
  local validation_data=$(cat <<EOL
{
  "name": "$name",
  "birth_date": "$birth_date",
  "birth_time": "$birth_time",
  "latitude": $latitude,
  "longitude": $longitude,
  "location": "$formatted_location"
}
EOL
)

  # Call API to validate birth details
  local validation_response=$(curl -s -X POST "$API_URL/chart/validate" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}" -d "$validation_data")

  if ! echo "$validation_response" | jq -e '.valid' > /dev/null || [ "$(echo "$validation_response" | jq -r '.valid')" != "true" ]; then
    log_message "ERROR" "Birth details validation failed: $(echo "$validation_response" | jq -r '.message // "Unknown error"')"
    return 1
  fi

  log_message "INFO" "Birth details validation successful:"
  log_message "INFO" "$validation_response"

  # Step 4: Chart Generation
  log_message "INFO" "Step 4: Testing chart generation"

  # Call API to generate chart
  local chart_response=$(create_chart "$name" "$birth_date" "$birth_time" "$latitude" "$longitude" "$formatted_location")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Chart generation failed"
    return 1
  fi

  # Extract chart ID
  local chart_id=$(echo "$chart_response" | jq -r '.chart_id')

  if [[ -z "$chart_id" || "$chart_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing chart ID in response"
    return 1
  fi

  log_message "INFO" "Chart generated successfully with ID: $chart_id"
  log_message "INFO" "$chart_response"

  # Step 5: Chart Retrieval
  log_message "INFO" "Step 5: Testing chart retrieval"

  # Call API to get chart
  local get_chart_response=$(get_chart "$chart_id")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Chart retrieval failed"
    return 1
  fi

  log_message "INFO" "Chart retrieved successfully:"
  log_message "INFO" "$get_chart_response"

  # Step 6: Questionnaire
  log_message "INFO" "Step 6: Testing questionnaire creation"

  # Call API to create questionnaire
  local questionnaire_response=$(api_request "POST" "/questionnaire" "{\"chart_id\": \"$chart_id\"}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Questionnaire creation failed"
    return 1
  fi

  # Extract questionnaire ID
  local questionnaire_id=$(echo "$questionnaire_response" | jq -r '.id // .questionnaire_id')

  if [[ -z "$questionnaire_id" || "$questionnaire_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing questionnaire ID in response"
    return 1
  fi

  log_message "INFO" "Questionnaire created successfully with ID: $questionnaire_id"

  # Step 7: Interactive questionnaire
  log_message "INFO" "Step 7: Testing interactive questionnaire"

  # Establish WebSocket connection for real-time questionnaire
  if ! establish_connection; then
    log_message "ERROR" "Failed to establish WebSocket connection"
    echo -e "${RED}WebSocket connection failed. This is required for the questionnaire. Stopping test.${NC}"
    return 1
  fi

  echo -e "${GREEN}WebSocket connection established successfully${NC}"

  # Get initial questionnaire
  local current_question=$(echo "$questionnaire_response" | jq -r '.current_question')
  local complete=false

  while [[ "$complete" != "true" ]]; do
    echo -e "\n${YELLOW}Question: $(echo "$current_question" | jq -r '.text')${NC}"

    # Get answer options if available
    if [[ $(echo "$current_question" | jq 'has("options")') == "true" ]]; then
      echo "Options:"
      local options=$(echo "$current_question" | jq -r '.options[]')
      local i=1
      while read -r option; do
        echo "$i) $option"
        ((i++))
      done <<< "$options"

      echo -e "Enter option number:"
      read option_num
      local answer_value=$(echo "$current_question" | jq -r ".options[$(($option_num-1))]")
    else
      echo -e "Enter your answer:"
      read answer_value
    fi

    # Submit answer
    local question_id=$(echo "$current_question" | jq -r '.id')

    # Send answer via WebSocket
    send_message "{\"type\": \"answer\", \"questionnaire_id\": \"$questionnaire_id\", \"question_id\": \"$question_id\", \"answer\": \"$answer_value\"}"

    # Wait for next question via WebSocket
    local ws_response=$(wait_for_message 10)

    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "No response received from WebSocket"
      echo -e "${RED}WebSocket communication failed. Stopping test.${NC}"
      close_connection
      return 1
    fi

    if [[ $(echo "$ws_response" | jq 'has("complete")') == "true" ]]; then
      complete=true
    else
      current_question=$(echo "$ws_response" | jq '.current_question')
    fi
  done

  log_message "INFO" "Questionnaire completed successfully"

  # Close the WebSocket connection
  close_connection

  # Step 8: Birth Time Rectification
  log_message "INFO" "Step 8: Testing birth time rectification"

  # Call API to start rectification
  local rectification_response=$(rectify_chart "$chart_id" "$questionnaire_id")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Birth time rectification failed"
    return 1
  fi

  # Extract rectification ID
  local rectification_id=$(echo "$rectification_response" | jq -r '.rectification_id')

  if [[ -z "$rectification_id" || "$rectification_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing rectification ID in response"
    return 1
  fi

  log_message "INFO" "Birth time rectification initiated with ID: $rectification_id"

  # Poll for rectification status
  local rectification_complete=false
  local max_attempts=30
  local attempt=0

  while [[ "$rectification_complete" != "true" && $attempt -lt $max_attempts ]]; do
    log_message "INFO" "Checking rectification status (attempt $((attempt+1))/$max_attempts)..."

    local status_response=$(get_rectification_status "$rectification_id")

    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Failed to get rectification status"
      return 1
    fi

    local status=$(echo "$status_response" | jq -r '.status')

    if [[ "$status" == "completed" ]]; then
      rectification_complete=true
    elif [[ "$status" == "failed" ]]; then
      log_message "ERROR" "Rectification failed: $(echo "$status_response" | jq -r '.message // "Unknown error"')"
      return 1
    else
      # Wait before checking again
      sleep 2
      ((attempt++))
    fi
  done

  if [[ "$rectification_complete" != "true" ]]; then
    log_message "ERROR" "Rectification timed out after $max_attempts attempts"
    return 1
  fi

  # Get rectified chart ID
  local rectified_chart_id=$(echo "$status_response" | jq -r '.rectified_chart_id')
  local rectified_time=$(echo "$status_response" | jq -r '.rectified_time')

  log_message "INFO" "Birth time rectification completed with rectified chart ID: $rectified_chart_id"
  log_message "INFO" "Rectified birth time: $rectified_time"

  # Step 9: Chart Comparison
  log_message "INFO" "Step 9: Testing chart comparison with original and rectified charts"

  # Call API to compare charts
  local comparison_response=$(compare_charts "$chart_id" "$rectified_chart_id")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Chart comparison failed"
    return 1
  fi

  log_message "INFO" "Chart comparison completed successfully:"
  log_message "INFO" "$comparison_response"

  # Step 10: Chart Export
  log_message "INFO" "Step 10: Testing chart export"

  # Call API to export chart
  local export_response=$(export_chart "$rectified_chart_id" "pdf")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Chart export failed"
    return 1
  fi

  # Extract download URL
  local download_url=$(echo "$export_response" | jq -r '.download_url')

  log_message "INFO" "Chart export completed successfully with download URL: $download_url"

  # Step 11: Download exported chart
  log_message "INFO" "Step 11: Testing export download"

  # Download the exported chart
  local download_path="$TEST_OUTPUT_DIR/birth-chart-export.pdf"
  curl -s "$API_URL$download_url" -H "Authorization: Bearer ${SESSION_TOKEN}" -o "$download_path"

  if [[ ! -f "$download_path" || ! -s "$download_path" ]]; then
    log_message "ERROR" "Chart download failed"
    return 1
  fi

  log_message "INFO" "Chart downloaded successfully to: $download_path"

  # Step 12: Cleanup - delete charts
  log_message "INFO" "Step 12: Cleaning up - deleting charts"

  # Delete original chart
  if ! delete_chart "$chart_id"; then
    log_message "ERROR" "Failed to delete original chart"
    return 1
  fi

  # Delete rectified chart
  if ! delete_chart "$rectified_chart_id"; then
    log_message "ERROR" "Failed to delete rectified chart"
    return 1
  fi

  log_message "INFO" "Charts deleted successfully"

  # Test completed successfully
  log_message "INFO" "Full sequence flow test completed successfully"
  return 0
}

# URL encode function
urlencode() {
  local string="$1"
  local strlen=${#string}
  local encoded=""
  local pos c o

  for (( pos=0 ; pos<strlen ; pos++ )); do
    c=${string:$pos:1}
    case "$c" in
      [-_.~a-zA-Z0-9] ) o="${c}" ;;
      * )               printf -v o '%%%02x' "'$c"
    esac
    encoded+="${o}"
  done
  echo "${encoded}"
}

# Run chart test
run_chart_test() {
  log_message "INFO" "Running chart tests..."

  # Create a sample chart
  log_message "INFO" "Creating sample chart..."
  local chart_result=$(create_chart "Sample Test Chart" "1990-01-01" "12:00" 0 0 "Test Location")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create sample chart"
    return 1
  fi

  # Extract chart ID
  local chart_id=$(echo "$chart_result" | jq -r '.id')
  log_message "INFO" "Sample chart created with ID: $chart_id"

  # Get the chart
  log_message "INFO" "Retrieving chart..."
  local get_result=$(get_chart "$chart_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to retrieve chart"
    return 1
  fi
  log_message "INFO" "Chart retrieved successfully"

  # Update the chart
  log_message "INFO" "Updating chart..."
  local update_result=$(update_chart "$chart_id" "Updated Chart" "1990-01-01" "14:00" 10 10 "Updated Location")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to update chart"
    return 1
  fi
  log_message "INFO" "Chart updated successfully"

  # Create a second chart for comparison
  log_message "INFO" "Creating second chart for comparison..."
  local chart2_result=$(create_chart "Comparison Chart" "1995-05-05" "15:30" 20 20 "Another Location")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create second chart"
    return 1
  fi

  # Extract second chart ID
  local chart2_id=$(echo "$chart2_result" | jq -r '.id')
  log_message "INFO" "Second chart created with ID: $chart2_id"

  # Compare charts
  log_message "INFO" "Comparing charts..."
  local compare_result=$(compare_charts "$chart_id" "$chart2_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to compare charts"
    return 1
  fi
  log_message "INFO" "Charts compared successfully"

  # Delete charts
  log_message "INFO" "Deleting charts..."
  delete_chart "$chart_id"
  delete_chart "$chart2_id"
  log_message "INFO" "Charts deleted successfully"

  log_message "INFO" "Chart tests completed successfully"
  return 0
}

# Run WebSocket test
run_websocket_test() {
  log_message "INFO" "Running WebSocket tests..."

  # Create a temporary file for WebSocket output
  local ws_output=$(mktemp)

  # Connect to realtime endpoint
  log_message "INFO" "Connecting to realtime endpoint..."
  ws_connect "/realtime" "{}" "$ws_output" 10
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to connect to WebSocket"
    rm -f "$ws_output"
    return 1
  fi

  # Read initial response
  local response=$(cat "$ws_output")
  if [[ -z "$response" ]]; then
    log_message "ERROR" "No response received from WebSocket"
    ws_close
    rm -f "$ws_output"
    return 1
  fi

  log_message "INFO" "WebSocket connection established"

  # Send a ping message
  log_message "INFO" "Sending ping message..."
  ws_send "{\"type\":\"ping\",\"timestamp\":$(date +%s)}"

  # Wait for response
  sleep 2
  local response=$(cat "$ws_output")

  # Close connection
  ws_close
  rm -f "$ws_output"

  log_message "INFO" "WebSocket tests completed successfully"
  return 0
}

# Main execution
main() {
  # Print banner
  print_banner

  # Create the test output directory
  mkdir -p "$TEST_OUTPUT_DIR"

  # Parse command line arguments
  while getopts ":t:v" opt; do
    case ${opt} in
      t )
        TEST_TYPE=$OPTARG
        ;;
      v )
        VERBOSE=true
        export VERBOSE
        ;;
      \? )
        echo "Invalid option: -$OPTARG" 1>&2
        exit 1
        ;;
      : )
        echo "Option -$OPTARG requires an argument" 1>&2
        exit 1
        ;;
    esac
  done

  # Set default test type to sequence
  TEST_TYPE=${TEST_TYPE:-"sequence"}

  # Check dependencies
  if ! check_dependencies; then
    echo "Required dependencies missing. Please install them and try again."
    exit 1
  fi

  # Initialize API client
  log_message "INFO" "Initializing API client"
  if ! init_session; then
    log_message "FATAL" "Session initialization failed. API must be available to run tests."
    exit 1
  fi

  # Run tests based on type
  case "$TEST_TYPE" in
    "unit")
      log_message "INFO" "Running unit tests"
      run_unit_tests
      ;;
    "sequence")
      log_message "INFO" "Running sequence diagram test flow"
      run_sequence_test
      ;;
    *)
      log_message "ERROR" "Unknown test type: $TEST_TYPE"
      exit 1
      ;;
  esac

  log_message "INFO" "All tests completed successfully"
  exit 0
}

# Run main function
main "$@"
