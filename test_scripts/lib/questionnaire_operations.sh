#!/bin/bash

# Questionnaire Operations
# Handles questionnaire-specific API operations as specified in the sequence diagram

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Source API client functions if not already sourced
if [[ -z "$API_URL" ]]; then
  source "$(dirname "$0")/api_client.sh"
fi

# Source WebSocket client functions if not already sourced
if [[ -z "$WS_URL" ]]; then
  source "$(dirname "$0")/websocket_client.sh"
fi

# Function to create a new questionnaire
create_questionnaire() {
  local chart_id="$1"

  if [[ -z "$chart_id" ]]; then
    log_message "ERROR" "create_questionnaire: Missing chart_id parameter"
    return 1
  fi

  log_message "INFO" "Creating questionnaire for chart ID: $chart_id"

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      log_message "ERROR" "create_questionnaire: Failed to initialize session"
      return 1
    fi
  fi

  # Create questionnaire using the API
  local data="{\"chart_id\": \"$chart_id\"}"
  local response=$(api_request "POST" "/questionnaire" "$data")
  local status=$?

  if [[ $status -ne 0 || -z "$response" ]]; then
    log_message "ERROR" "create_questionnaire: API request failed"
    return 1
  fi

  # Check for error response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ -n "$error" ]]; then
    log_message "ERROR" "create_questionnaire: API returned error: $error"
    return 1
  fi

  # Debug the response
  log_message "DEBUG" "Questionnaire API response: $response"

  # Extract questionnaire ID - try different field names
  local questionnaire_id=$(echo "$response" | jq -r '.id // .questionnaire_id // empty')
  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "create_questionnaire: Failed to extract questionnaire ID from response"
    log_message "ERROR" "Response was: $response"
    return 1
  fi

  log_message "INFO" "Questionnaire created successfully with ID: $questionnaire_id"
  echo "$response"
  return 0
}

# Function to get a specific questionnaire
get_questionnaire() {
  local questionnaire_id="$1"

  log_message "INFO" "Retrieving questionnaire with ID: $questionnaire_id"

  # Make sure we have a valid session
  if [[ -z "$SESSION_TOKEN" ]]; then
    log_message "INFO" "No session token available. Initializing session."
    if ! init_session; then
      log_message "ERROR" "Failed to initialize session"
      return 1
    fi
  fi

  # API request to get questionnaire data
  local response=$(api_request "GET" "/questionnaire/$questionnaire_id" "{}")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to retrieve questionnaire with ID: $questionnaire_id"
    return 1
  fi

  log_message "INFO" "Questionnaire retrieved successfully"
  echo "$response"
  return 0
}

# Function to get the next question in a questionnaire
get_next_question() {
  local questionnaire_id="$1"

  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "get_next_question: Missing questionnaire_id parameter"
    return 1
  fi

  log_message "INFO" "Getting next question for questionnaire ID: $questionnaire_id"

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      log_message "ERROR" "get_next_question: Failed to initialize session"
      return 1
    fi
  fi

  # Get the next question using the API
  local response=$(api_request "GET" "/questionnaire/$questionnaire_id/next-question" "{}")
  local status=$?

  if [[ $status -ne 0 || -z "$response" ]]; then
    log_message "ERROR" "get_next_question: API request failed"
    return 1
  fi

  # Check for error response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ -n "$error" ]]; then
    log_message "ERROR" "get_next_question: API returned error: $error"
    return 1
  fi

  # Check if questionnaire is complete
  local is_complete=$(echo "$response" | jq -r '.is_complete // false')
  if [[ "$is_complete" == "true" ]]; then
    log_message "INFO" "Questionnaire is complete, no more questions available"
  else
    # Extract question details
    local question_id=$(echo "$response" | jq -r '.id // empty')
    local question_text=$(echo "$response" | jq -r '.question // empty')

    if [[ -z "$question_id" || -z "$question_text" ]]; then
      log_message "WARNING" "get_next_question: Received incomplete question data"
    else
      log_message "INFO" "Received question ID: $question_id, Text: $question_text"
    fi
  fi

  echo "$response"
  return 0
}

# Function to submit an answer to a questionnaire
submit_answer() {
  local questionnaire_id="$1"
  local question_id="$2"
  local answer="$3"

  if [[ -z "$questionnaire_id" || -z "$question_id" || -z "$answer" ]]; then
    log_message "ERROR" "submit_answer: Missing required parameters"
    return 1
  fi

  log_message "INFO" "Submitting answer '$answer' for question ID: $question_id in questionnaire ID: $questionnaire_id"

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      log_message "ERROR" "submit_answer: Failed to initialize session"
      return 1
    fi
  fi

  # Prepare data for API request
  local data="{
    \"questionnaire_id\": \"$questionnaire_id\",
    \"question_id\": \"$question_id\",
    \"answer\": \"$answer\"
  }"

  # Submit the answer using the API
  local response=$(api_request "POST" "/questionnaire/$questionnaire_id/answer" "$data")
  local status=$?

  if [[ $status -ne 0 || -z "$response" ]]; then
    log_message "ERROR" "submit_answer: API request failed"
    return 1
  fi

  # Check for error response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ -n "$error" ]]; then
    log_message "ERROR" "submit_answer: API returned error: $error"
    return 1
  fi

  # Check for questionnaire completion
  local status=$(echo "$response" | jq -r '.status // ""')
  if [[ "$status" == "complete" ]]; then
    log_message "INFO" "Questionnaire completed after submitting this answer"
  else
    log_message "INFO" "Answer submitted successfully, questionnaire continues"
  fi

  echo "$response"
  return 0
}

# Function to complete a questionnaire
complete_questionnaire() {
  local questionnaire_id="$1"

  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "complete_questionnaire: Missing questionnaire_id parameter"
    return 1
  fi

  log_message "INFO" "Completing questionnaire ID: $questionnaire_id"

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      log_message "ERROR" "complete_questionnaire: Failed to initialize session"
      return 1
    fi
  fi

  # Complete the questionnaire using the API
  local response=$(api_request "POST" "/questionnaire/$questionnaire_id/complete" "{}")
  local status=$?

  if [[ $status -ne 0 || -z "$response" ]]; then
    log_message "ERROR" "complete_questionnaire: API request failed"
    return 1
  fi

  # Check for error response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ -n "$error" ]]; then
    log_message "ERROR" "complete_questionnaire: API returned error: $error"
    return 1
  fi

  log_message "INFO" "Questionnaire completed successfully"
  echo "$response"
  return 0
}

# Function to get questionnaire status
get_questionnaire_status() {
  local questionnaire_id="$1"

  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "get_questionnaire_status: Missing questionnaire_id parameter"
    return 1
  fi

  log_message "INFO" "Getting status for questionnaire ID: $questionnaire_id"

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      log_message "ERROR" "get_questionnaire_status: Failed to initialize session"
      return 1
    fi
  fi

  # Get the questionnaire status using the API
  local response=$(api_request "GET" "/questionnaire/$questionnaire_id" "{}")
  local status=$?

  if [[ $status -ne 0 || -z "$response" ]]; then
    log_message "ERROR" "get_questionnaire_status: API request failed"
    return 1
  fi

  # Check for error response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ -n "$error" ]]; then
    log_message "ERROR" "get_questionnaire_status: API returned error: $error"
    return 1
  fi

  # Extract questionnaire status
  local questionnaire_status=$(echo "$response" | jq -r '.status // "unknown"')
  local completion_percentage=$(echo "$response" | jq -r '.completion_percentage // 0')

  log_message "INFO" "Questionnaire status: $questionnaire_status, Completion: $completion_percentage%"
  echo "$response"
  return 0
}

# Function to run interactive questionnaire session with real-time WebSocket updates
run_interactive_questionnaire() {
  local chart_id="$1"

  log_message "INFO" "Starting interactive questionnaire for chart ID: $chart_id"

  # Make sure we have a valid session
  if [[ -z "$SESSION_TOKEN" ]]; then
    log_message "INFO" "No session token available. Initializing session."
    if ! init_session; then
      log_message "ERROR" "Failed to initialize session"
      return 1
    fi
  fi

  # Connect to the questionnaire WebSocket channel
  if ! establish_connection; then
    log_message "ERROR" "Failed to connect to questionnaire WebSocket channel"
    return 1
  fi

  # Initialize the questionnaire
  local questionnaire_data="{\"chart_id\": \"$chart_id\"}"
  local questionnaire_response=$(api_request "POST" "/questionnaire" "$questionnaire_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to initialize questionnaire"
    close_connection
    return 1
  fi

  # Extract questionnaire ID
  local questionnaire_id=$(echo "$questionnaire_response" | jq -r '.id // empty')
  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "Failed to extract questionnaire ID from response"
    close_connection
    return 1
  fi
  log_message "INFO" "Questionnaire initialized with ID: $questionnaire_id"

  # Subscribe to the questionnaire-specific channel for real-time updates
  local subscribe_msg="{\"type\": \"subscribe\", \"channel\": \"questionnaire_$questionnaire_id\"}"
  if ! send_message "$subscribe_msg"; then
    log_message "ERROR" "Failed to subscribe to questionnaire channel"
    close_connection
    return 1
  fi

  echo -e "\n${BOLD}Interactive Birth Time Rectification Questionnaire${NC}"
  echo "Please answer the following questions to help rectify the birth time:"
  echo "-------------------------------------------------------------------"

  # Wait for initial question from WebSocket
  log_message "INFO" "Waiting for initial question..."
  local first_ws_message=$(wait_for_message 10)
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to receive initial question via WebSocket"
    close_connection
    return 1
  fi

  # Extract first question
  local current_question=$(echo "$first_ws_message" | jq -r '.question // empty')
  local current_question_id=$(echo "$first_ws_message" | jq -r '.id // empty')

  if [[ -z "$current_question_id" ]]; then
    log_message "ERROR" "Failed to extract question ID from WebSocket message"
    close_connection
    return 1
  fi

  # Process questions in a loop until complete
  local is_complete=false
  while [[ "$is_complete" != "true" ]]; do
    # Display the current question
    echo -e "\nQuestion: ${CYAN}$current_question${NC}"
    read -p "Your answer: " user_answer

    # Submit the answer
    log_message "INFO" "Submitting answer: '$user_answer' for question ID: $current_question_id"
    local answer_msg="{\"type\": \"answer\", \"questionnaire_id\": \"$questionnaire_id\", \"question_id\": \"$current_question_id\", \"answer\": \"$user_answer\"}"

    if ! send_message "$answer_msg"; then
      log_message "ERROR" "Failed to send answer via WebSocket"
      close_connection
      return 1
    fi

    # Wait for next question from WebSocket
    log_message "INFO" "Waiting for next question via WebSocket..."
    local next_ws_message=$(wait_for_message 10)
    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Failed to receive next question via WebSocket"
      close_connection
      return 1
    fi

    # Check if questionnaire is complete
    local complete_flag=$(echo "$next_ws_message" | jq -r '.complete // false')
    if [[ "$complete_flag" == "true" ]]; then
      is_complete=true
      echo -e "\n${GREEN}Questionnaire completed successfully!${NC}"
      break
    fi

    # Extract next question
    local next_question=$(echo "$next_ws_message" | jq -r '.question // empty')
    local next_question_id=$(echo "$next_ws_message" | jq -r '.id // empty')

    if [[ -z "$next_question_id" ]]; then
      log_message "ERROR" "Failed to extract question ID from WebSocket message"
      close_connection
      return 1
    fi

    # Update current question for next iteration
    current_question="$next_question"
    current_question_id="$next_question_id"
  done

  # Complete the questionnaire
  log_message "INFO" "Completing questionnaire..."
  local completion_response=$(complete_questionnaire "$questionnaire_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to complete questionnaire"
    close_connection
    return 1
  fi

  # Send unsubscribe message
  local unsubscribe_msg="{\"type\": \"unsubscribe\", \"channel\": \"questionnaire_$questionnaire_id\"}"
  send_message "$unsubscribe_msg"

  # Close WebSocket
  close_connection

  log_message "INFO" "Interactive questionnaire completed successfully"
  echo "$questionnaire_id"
  return 0
}

# Function to create a sample questionnaire for testing
create_sample_questionnaire() {
  log_message "INFO" "Creating sample questionnaire for testing"

  # First create a sample chart
  local chart_id=$(create_sample_chart)
  if [[ $? -ne 0 || -z "$chart_id" ]]; then
    log_message "ERROR" "Failed to create sample chart for questionnaire"
    return 1
  fi

  # Validate chart ID format (should be chrt_XXXXXXXX)
  if [[ ! "$chart_id" =~ ^chrt_[a-zA-Z0-9]+$ ]]; then
    log_message "ERROR" "Invalid chart ID format: '$chart_id'"
    log_message "ERROR" "Chart ID should match pattern: chrt_XXXXXXXX"
    return 1
  fi

  log_message "INFO" "Created sample chart with ID: $chart_id for questionnaire"

  # Now create the questionnaire with validated chart_id
  local questionnaire_data="{\"chart_id\": \"$chart_id\"}"
  log_message "DEBUG" "Questionnaire request data: $questionnaire_data"

  # Make API request with detailed error handling
  local questionnaire_response=$(api_request "POST" "/questionnaire" "$questionnaire_data")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "Failed to create questionnaire via API"
    return 1
  fi

  # Debug the raw response
  log_message "DEBUG" "Questionnaire API raw response: $questionnaire_response"

  # Try to parse the response as JSON
  if ! echo "$questionnaire_response" | jq '.' > /dev/null 2>&1; then
    log_message "ERROR" "Invalid JSON response from questionnaire API"
    log_message "ERROR" "Raw response: $questionnaire_response"
    return 1
  fi

  # Check for error in response
  local error=$(echo "$questionnaire_response" | jq -r '.error // empty')
  if [[ -n "$error" && "$error" != "null" ]]; then
    local msg=$(echo "$questionnaire_response" | jq -r '.detail // .message // "Unknown error"')
    log_message "ERROR" "API error: $error - $msg"
    return 1
  fi

  # Dump all available fields for debugging
  log_message "DEBUG" "Response fields: $(echo "$questionnaire_response" | jq 'keys')"

  # Extract questionnaire ID - try different field names with detailed logging
  local questionnaire_id=""

  # First try the sessionId field (based on the actual API response format)
  local session_id=$(echo "$questionnaire_response" | jq -r '.sessionId // empty')
  if [[ -n "$session_id" ]]; then
    questionnaire_id="$session_id"
    log_message "DEBUG" "Found questionnaire ID in sessionId field: $session_id"
  else
    # Try standard field names as fallback
    for field in "id" "questionnaire_id" "questionnaireId"; do
      local value=$(echo "$questionnaire_response" | jq -r ".$field // empty")
      if [[ -n "$value" ]]; then
        questionnaire_id="$value"
        log_message "DEBUG" "Found questionnaire ID in field: $field"
        break
      fi
    done

    # If still empty, try to find any field that looks like an ID
    if [[ -z "$questionnaire_id" ]]; then
      log_message "WARNING" "Could not find questionnaire ID in standard fields, searching all fields"
      local all_fields=$(echo "$questionnaire_response" | jq -r 'keys[]')
      for field in $all_fields; do
        local value=$(echo "$questionnaire_response" | jq -r ".$field // empty")
        if [[ "$value" =~ ^[a-zA-Z0-9_-]+$ && "$field" != "isComplete" && "$field" != "confidence" ]]; then
          questionnaire_id="$value"
          log_message "DEBUG" "Found potential questionnaire ID in field: $field with value: $value"
          break
        fi
      done
    fi
  fi

  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "Failed to extract questionnaire ID from response"
    log_message "ERROR" "Response was: $questionnaire_response"
    log_message "ERROR" "Available fields: $(echo "$questionnaire_response" | jq 'keys')"
    return 1
  fi

  log_message "INFO" "Sample questionnaire created with ID: $questionnaire_id"
  echo "$questionnaire_id"
  return 0
}

# Function to submit questionnaire answers
submit_questionnaire_answers() {
  local questionnaire_id="$1"
  local answers_data="$2"

  log_message "INFO" "Submitting answers for questionnaire: $questionnaire_id"

  # Use API endpoint for submission
  local api_response=$(api_request "POST" "/questionnaire/$questionnaire_id/bulk-answers" "$answers_data")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to submit answers via API"
    return 1
  fi

  log_message "INFO" "Answers submitted successfully"
  echo "$api_response"
  return 0
}

# Function to run interactive questionnaire from main script
run_interactive_questionnaire_from_lib() {
  local chart_id="$1"

  log_message "INFO" "Starting interactive questionnaire from lib for chart ID: $chart_id"

  # Call the existing run_interactive_questionnaire function
  if ! run_interactive_questionnaire "$chart_id"; then
    log_message "ERROR" "Interactive questionnaire failed"
    return 1
  fi

  log_message "INFO" "Interactive questionnaire completed successfully"
  return 0
}

# Export functions
export -f create_questionnaire get_questionnaire get_next_question submit_answer complete_questionnaire
export -f run_interactive_questionnaire run_interactive_questionnaire_from_lib submit_questionnaire_answers
export -f create_sample_questionnaire get_questionnaire_status
