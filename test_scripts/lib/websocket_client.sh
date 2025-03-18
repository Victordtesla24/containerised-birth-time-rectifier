#!/bin/bash

# WebSocket Client for Birth Time Rectifier API
# Handles WebSocket connections and real-time communication with enhanced interactive support

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Default WebSocket URL - Use WS_URL if set from main script, otherwise build default
WS_PORT=${WS_PORT:-8081}
WS_HOST=${WS_HOST:-localhost}
WS_URL=${WS_URL:-"ws://$WS_HOST:$WS_PORT/ws"}

# WebSocket connection state
CONNECTION_STATE="DISCONNECTED"

# WebSocket process ID
WS_PID=""

# WebSocket output file
WS_DATA_FILE="/tmp/ws_data_$$"

# WebSocket input pipe
WS_INPUT_PIPE="/tmp/ws_input_$$"

# Message queue for reliability
WS_MESSAGE_QUEUE=()

# Active subscriptions
WS_ACTIVE_SUBSCRIPTIONS=()

# Last received message timestamp
WS_LAST_MESSAGE_TIME=0

# Heartbeat interval in seconds
WS_HEARTBEAT_INTERVAL=30

# Reconnect settings
WS_MAX_RECONNECT_ATTEMPTS=5
WS_RECONNECT_DELAY=2

# Check if websocat is installed
check_websocat() {
  if ! command -v websocat &> /dev/null; then
    log_message "ERROR" "websocat is not installed. WebSocket functionality is required."
    echo -e "${RED}websocat is not installed. This tool is required for WebSocket tests.${NC}"
    echo -e "${YELLOW}Install websocat with: cargo install websocat${NC}"
    return 1
  fi

  log_message "INFO" "websocat is installed and available"
  return 0
}

# Connect to WebSocket
ws_connect() {
  local endpoint="$1"
  local payload="$2"
  local output_file="$3"
  local timeout=${4:-60}  # Connection timeout in seconds

  # Ensure websocat is installed
  if ! check_websocat; then
    return 1
  fi

  # Create full WebSocket URL
  local full_url="${WS_URL}${endpoint}"

  log_message "INFO" "Connecting to WebSocket: ${full_url}"

  # Set up signal handler for timeout
  trap 'log_message "ERROR" "WebSocket connection timed out after ${timeout} seconds"; kill -9 $WS_PID 2>/dev/null; CONNECTION_STATE="FAILED"; exit 1' ALRM

  # Start websocat in the background
  if [[ -z "$payload" ]]; then
    websocat "$full_url" > "$output_file" 2>/dev/null &
  else
    # Echo payload and pipe to websocat
    echo "$payload" | websocat --no-close -n1 "$full_url" > "$output_file" 2>/dev/null &
  fi

  WS_PID=$!

  # Start timeout countdown in background
  (sleep $timeout && kill -ALRM $$ 2>/dev/null) &
  TIMEOUT_PID=$!

  # Wait for websocat to exit or first message
  local start_time=$(date +%s)
  local first_message=false

  while true; do
    # Check if file has content (first message received)
    if [[ -s "$output_file" && "$first_message" == "false" ]]; then
      first_message=true
      log_message "INFO" "Received first message from WebSocket"

      # Disable timeout
      kill $TIMEOUT_PID 2>/dev/null
      trap - ALRM

      # Read first message
      local first_msg=$(head -n 1 "$output_file")

      # Check if it's an error message
      if echo "$first_msg" | jq -e 'has("error")' &>/dev/null; then
        local error=$(echo "$first_msg" | jq -r '.error')
        local detail=$(echo "$first_msg" | jq -r '.detail // "No details provided"')
        log_message "ERROR" "WebSocket error: $error - $detail"
        kill $WS_PID 2>/dev/null
        CONNECTION_STATE="FAILED"
        return 1
      fi

      CONNECTION_STATE="CONNECTED"
      return 0
    fi

    # Check if websocat is still running
    if ! kill -0 $WS_PID 2>/dev/null; then
      # Disable timeout
      kill $TIMEOUT_PID 2>/dev/null
      trap - ALRM

      # Check if we got any output before exit
      if [[ -s "$output_file" ]]; then
        log_message "INFO" "WebSocket connection closed after receiving data"
        CONNECTION_STATE="CLOSED"
        return 0
      else
        log_message "ERROR" "WebSocket connection failed or closed without data"
        CONNECTION_STATE="FAILED"
        return 1
      fi
    fi

    # Don't burn CPU
    sleep 0.1

    # Check for timeout manually as well
    local current_time=$(date +%s)
    if (( current_time - start_time > timeout )); then
      log_message "ERROR" "WebSocket operation timed out after ${timeout} seconds"
      kill $WS_PID 2>/dev/null
      kill $TIMEOUT_PID 2>/dev/null
      trap - ALRM
      CONNECTION_STATE="FAILED"
      return 1
    fi
  done
}

# Send message to active WebSocket connection
ws_send() {
  local message="$1"

  if [[ -z "$WS_PID" ]]; then
    log_message "ERROR" "No active WebSocket connection"
    return 1
  fi

  # Check if websocat is still running
  if ! kill -0 $WS_PID 2>/dev/null; then
    log_message "ERROR" "WebSocket connection is closed"
    CONNECTION_STATE="CLOSED"
    return 1
  fi

  # Send message to websocat
  log_message "INFO" "Sending message to WebSocket"
  echo "$message" > /proc/$WS_PID/fd/0 2>/dev/null

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to send message to WebSocket"
    return 1
  fi

  return 0
}

# Close WebSocket connection
ws_close() {
  if [[ -n "$WS_PID" ]]; then
    log_message "INFO" "Closing WebSocket connection"
    kill $WS_PID 2>/dev/null
    WS_PID=""
    CONNECTION_STATE="DISCONNECTED"
  fi

  # Remove data file if it exists
  if [[ -f "$WS_DATA_FILE" ]]; then
    rm -f "$WS_DATA_FILE" 2>/dev/null
  fi
}

# Create named pipe for input if it doesn't exist
create_input_pipe() {
  if [[ ! -p "$WS_INPUT_PIPE" ]]; then
    mkfifo "$WS_INPUT_PIPE" 2>/dev/null
    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Failed to create input pipe: $WS_INPUT_PIPE"
      return 1
    fi
    log_message "DEBUG" "Created input pipe: $WS_INPUT_PIPE"
  fi
  return 0
}

# Establish a WebSocket connection for the test script with enhanced reliability
establish_connection() {
  log_message "INFO" "Establishing WebSocket connection to $WS_URL"

  # Check if websocat is installed
  if ! check_websocat; then
    return 1
  fi

  # Create input pipe for bidirectional communication
  if ! create_input_pipe; then
    return 1
  fi

  # Clear any existing data file
  rm -f "$WS_DATA_FILE" 2>/dev/null

  # Try multiple approaches to verify server availability
  log_message "INFO" "Testing WebSocket endpoint availability"

  # First try: Direct WebSocket connection test
  if timeout 3 websocat --no-close "$WS_URL" > /dev/null 2>&1; then
    log_message "INFO" "WebSocket server is available via direct connection"
  else
    # Second try: HTTP health check with better URL construction
    log_message "INFO" "Direct WebSocket connection failed, trying HTTP health check"

    # Extract host and port from WS_URL
    local ws_host=$(echo "$WS_URL" | sed -E 's|^ws://([^:/]+)(:[0-9]+)?.*|\1|')
    local ws_port=$(echo "$WS_URL" | sed -E 's|^ws://[^:]+:([0-9]+).*|\1|')

    # If no port was found, use default HTTP port
    if [[ "$ws_port" == "$WS_URL" ]]; then
      ws_port="80"
    fi

    # Construct API URL for health check
    local api_url="http://${ws_host}:${ws_port}/api/v1/health"
    log_message "INFO" "Trying health check at: $api_url"

    local test_result=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$api_url" --connect-timeout 3)

    if [[ "$test_result" != "200" && "$test_result" != "101" ]]; then
      # Third try: Alternative health endpoint
      api_url="http://${ws_host}:${ws_port}/health"
      log_message "INFO" "Trying alternative health check at: $api_url"
      test_result=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$api_url" --connect-timeout 3)

      if [[ "$test_result" != "200" && "$test_result" != "101" ]]; then
        log_message "ERROR" "WebSocket server appears to be unavailable. HTTP status: $test_result"
        echo -e "${RED}WebSocket server not available (HTTP status: $test_result). Cannot proceed with WebSocket tests.${NC}"
        echo -e "${YELLOW}Verify that the WebSocket server is running at $WS_URL${NC}"
        return 1
      fi
    fi
  fi

  log_message "INFO" "WebSocket server appears to be available, attempting connection"

  # Start websocat in the background with bidirectional communication
  # Use the named pipe for input and redirect output to the data file
  cat "$WS_INPUT_PIPE" | websocat --ping-interval 10 "$WS_URL" > "$WS_DATA_FILE" 2>/dev/null &
  WS_PID=$!

  # Check if the process started
  if ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "Failed to start WebSocket connection"
    WS_PID=""
    CONNECTION_STATE="FAILED"
    return 1
  fi

  # Wait a moment for the connection to establish
  sleep 2

  # Check if the process is still running (connection still active)
  if ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "WebSocket connection failed to establish"
    WS_PID=""
    CONNECTION_STATE="FAILED"
    rm -f "$WS_DATA_FILE" 2>/dev/null
    return 1
  fi

  # Test the connection by sending a ping
  log_message "INFO" "Testing WebSocket connection with ping message"
  if ! send_message '{"type":"ping","timestamp":'$(date +%s)'}'; then
    log_message "ERROR" "WebSocket connection test failed"
    close_connection
    CONNECTION_STATE="FAILED"
    return 1
  fi

  # Wait for response to confirm connection is working
  local wait_result=$(wait_for_message 5)

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "No response to ping message, WebSocket connection not working properly"
    close_connection
    CONNECTION_STATE="FAILED"
    return 1
  fi

  # Set up heartbeat timer in background
  (
    while true; do
      sleep $WS_HEARTBEAT_INTERVAL
      if [[ "$CONNECTION_STATE" != "CONNECTED" ]]; then
        break
      fi

      # Check if we need to send a heartbeat
      local current_time=$(date +%s)
      local time_since_last_message=$((current_time - WS_LAST_MESSAGE_TIME))

      if [[ $time_since_last_message -gt $WS_HEARTBEAT_INTERVAL ]]; then
        log_message "DEBUG" "Sending heartbeat ping"
        echo '{"type":"ping","timestamp":'$current_time'}' > "$WS_INPUT_PIPE" 2>/dev/null
      fi
    done
  ) &
  WS_HEARTBEAT_PID=$!

  # Start message processor in background
  (
    while true; do
      if [[ "$CONNECTION_STATE" != "CONNECTED" ]]; then
        break
      fi

      # Process any new messages in the data file
      if [[ -s "$WS_DATA_FILE" ]]; then
        WS_LAST_MESSAGE_TIME=$(date +%s)
        cat "$WS_DATA_FILE" > "/tmp/ws_processed_$$"
        > "$WS_DATA_FILE"  # Clear the file after reading

        # Process each line as a separate message
        while read -r message; do
          process_incoming_message "$message"
        done < "/tmp/ws_processed_$$"

        rm -f "/tmp/ws_processed_$$" 2>/dev/null
      fi

      sleep 0.1
    done
  ) &
  WS_PROCESSOR_PID=$!

  CONNECTION_STATE="CONNECTED"
  log_message "INFO" "WebSocket connection established and verified"
  return 0
}

# Process incoming WebSocket messages
process_incoming_message() {
  local message="$1"

  # Skip empty messages
  if [[ -z "$message" ]]; then
    return 0
  fi

  log_message "DEBUG" "Processing incoming message: $message"

  # Try to parse as JSON
  if ! echo "$message" | jq empty &>/dev/null; then
    log_message "WARNING" "Received non-JSON message: $message"
    return 1
  fi

  # Extract message type
  local msg_type=$(echo "$message" | jq -r '.type // "unknown"')

  case "$msg_type" in
    "pong")
      # Heartbeat response, just log it
      log_message "DEBUG" "Received pong response"
      ;;
    "question")
      # Display question to user
      local question_text=$(echo "$message" | jq -r '.text // .question // empty')
      local question_id=$(echo "$message" | jq -r '.id // empty')

      if [[ -n "$question_text" && -n "$question_id" ]]; then
        echo -e "\n${CYAN}Question: $question_text${NC}"
        # Store the current question for later reference
        WS_CURRENT_QUESTION_ID="$question_id"
        WS_CURRENT_QUESTION_TEXT="$question_text"
      fi
      ;;
    "answer_received")
      # Confirmation that answer was received
      echo -e "${GREEN}Answer received and processed${NC}"
      ;;
    "complete")
      # Questionnaire is complete
      echo -e "\n${GREEN}Questionnaire completed successfully!${NC}"
      ;;
    "error")
      # Error message
      local error_msg=$(echo "$message" | jq -r '.message // "Unknown error"')
      echo -e "${RED}Error: $error_msg${NC}"
      ;;
    *)
      # Unknown message type, just log it
      log_message "DEBUG" "Received message of type: $msg_type"
      ;;
  esac

  return 0
}

# Send a message through the established WebSocket connection with reliability
send_message() {
  local message="$1"
  local retry_count=0
  local max_retries=3

  if [[ -z "$WS_PID" ]] || ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "No active WebSocket connection"
    CONNECTION_STATE="DISCONNECTED"

    # Queue the message for later delivery if reconnection succeeds
    WS_MESSAGE_QUEUE+=("$message")
    log_message "INFO" "Message queued for later delivery"

    # Try to reconnect
    if attempt_reconnect; then
      # Process queued messages
      process_message_queue
    else
      return 1
    fi
  fi

  log_message "DEBUG" "Sending WebSocket message: $message"

  # Update last message time
  WS_LAST_MESSAGE_TIME=$(date +%s)

  # Send message through the input pipe
  while [[ $retry_count -lt $max_retries ]]; do
    echo "$message" > "$WS_INPUT_PIPE" 2>/dev/null

    if [[ $? -eq 0 ]]; then
      return 0
    fi

    log_message "WARNING" "Failed to send message, retrying (attempt $((retry_count+1))/$max_retries)"
    retry_count=$((retry_count+1))
    sleep 0.5
  done

  log_message "ERROR" "Failed to send WebSocket message after $max_retries attempts"
  CONNECTION_STATE="FAILED"

  # Queue the message for later delivery
  WS_MESSAGE_QUEUE+=("$message")
  log_message "INFO" "Message queued for later delivery"

  return 1
}

# Process queued messages after reconnection
process_message_queue() {
  if [[ ${#WS_MESSAGE_QUEUE[@]} -eq 0 ]]; then
    return 0
  fi

  log_message "INFO" "Processing ${#WS_MESSAGE_QUEUE[@]} queued messages"

  local success=true
  for message in "${WS_MESSAGE_QUEUE[@]}"; do
    echo "$message" > "$WS_INPUT_PIPE" 2>/dev/null

    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Failed to send queued message: $message"
      success=false
    fi

    sleep 0.1
  done

  if [[ "$success" == "true" ]]; then
    # Clear the queue if all messages were sent successfully
    WS_MESSAGE_QUEUE=()
    return 0
  else
    return 1
  fi
}

# Attempt to reconnect to the WebSocket server
attempt_reconnect() {
  local attempt=1

  log_message "INFO" "Attempting to reconnect to WebSocket server"

  while [[ $attempt -le $WS_MAX_RECONNECT_ATTEMPTS ]]; do
    log_message "INFO" "Reconnection attempt $attempt/$WS_MAX_RECONNECT_ATTEMPTS"

    # Close any existing connection
    close_connection

    # Try to establish a new connection
    if establish_connection; then
      log_message "INFO" "Reconnection successful"

      # Resubscribe to active channels
      for subscription in "${WS_ACTIVE_SUBSCRIPTIONS[@]}"; do
        local subscribe_msg="{\"type\": \"subscribe\", \"channel\": \"$subscription\"}"
        echo "$subscribe_msg" > "$WS_INPUT_PIPE" 2>/dev/null
        log_message "INFO" "Resubscribed to channel: $subscription"
      done

      return 0
    fi

    log_message "WARNING" "Reconnection attempt $attempt failed, retrying in $WS_RECONNECT_DELAY seconds"
    sleep $WS_RECONNECT_DELAY
    attempt=$((attempt+1))
  done

  log_message "ERROR" "Failed to reconnect after $WS_MAX_RECONNECT_ATTEMPTS attempts"
  return 1
}

# Subscribe to a WebSocket channel
subscribe_to_channel() {
  local channel="$1"

  log_message "INFO" "Subscribing to channel: $channel"

  # Check if already subscribed
  for subscription in "${WS_ACTIVE_SUBSCRIPTIONS[@]}"; do
    if [[ "$subscription" == "$channel" ]]; then
      log_message "INFO" "Already subscribed to channel: $channel"
      return 0
    fi
  done

  # Send subscription message
  local subscribe_msg="{\"type\": \"subscribe\", \"channel\": \"$channel\"}"
  if send_message "$subscribe_msg"; then
    # Add to active subscriptions
    WS_ACTIVE_SUBSCRIPTIONS+=("$channel")
    log_message "INFO" "Successfully subscribed to channel: $channel"
    return 0
  else
    log_message "ERROR" "Failed to subscribe to channel: $channel"
    return 1
  fi
}

# Unsubscribe from a WebSocket channel
unsubscribe_from_channel() {
  local channel="$1"

  log_message "INFO" "Unsubscribing from channel: $channel"

  # Send unsubscription message
  local unsubscribe_msg="{\"type\": \"unsubscribe\", \"channel\": \"$channel\"}"
  if send_message "$unsubscribe_msg"; then
    # Remove from active subscriptions
    local new_subscriptions=()
    for subscription in "${WS_ACTIVE_SUBSCRIPTIONS[@]}"; do
      if [[ "$subscription" != "$channel" ]]; then
        new_subscriptions+=("$subscription")
      fi
    done
    WS_ACTIVE_SUBSCRIPTIONS=("${new_subscriptions[@]}")

    log_message "INFO" "Successfully unsubscribed from channel: $channel"
    return 0
  else
    log_message "ERROR" "Failed to unsubscribe from channel: $channel"
    return 1
  fi
}

# Wait for message from the WebSocket connection with enhanced reliability
wait_for_message() {
  local timeout=${1:-5}
  local time_waited=0
  local interval=0.5
  local message=""

  if [[ -z "$WS_PID" ]] || ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "No active WebSocket connection"
    CONNECTION_STATE="DISCONNECTED"

    # Try to reconnect
    if ! attempt_reconnect; then
      return 1
    fi
  fi

  log_message "DEBUG" "Waiting for WebSocket message (timeout: ${timeout}s)"

  while [[ $time_waited -lt $timeout ]]; do
    # Check if the connection is still alive
    if ! ps -p $WS_PID > /dev/null; then
      log_message "ERROR" "WebSocket connection lost while waiting for message"
      CONNECTION_STATE="CLOSED"

      # Try to reconnect
      if ! attempt_reconnect; then
        return 1
      fi
    fi

    # Check if there's data in the file
    if [[ -s "$WS_DATA_FILE" ]]; then
      message=$(cat "$WS_DATA_FILE")
      # Clear the file after reading
      > "$WS_DATA_FILE"

      # Update last message time
      WS_LAST_MESSAGE_TIME=$(date +%s)

      log_message "DEBUG" "Received WebSocket message: $message"
      echo "$message"
      return 0
    fi

    sleep $interval
    time_waited=$(echo "$time_waited + $interval" | bc)
  done

  log_message "ERROR" "Timeout waiting for WebSocket message"
  return 1
}

# Get user input and send it via WebSocket
get_and_send_user_input() {
  local prompt="$1"
  local message_template="$2"
  local additional_params="$3"

  # Display prompt and get user input
  read -p "$prompt" user_input

  # Format the message using the template and user input
  local formatted_message=$(echo "$message_template" | sed "s/USER_INPUT/$user_input/g")

  # Add additional parameters if provided
  if [[ -n "$additional_params" ]]; then
    # Remove the trailing closing brace
    formatted_message=${formatted_message%\}}
    # Add the additional parameters and closing brace
    formatted_message="$formatted_message, $additional_params}"
  fi

  # Send the message
  if send_message "$formatted_message"; then
    return 0
  else
    return 1
  fi
}

# Interactive questionnaire session using WebSocket
run_interactive_questionnaire_ws() {
  local chart_id="$1"

  log_message "INFO" "Starting interactive WebSocket questionnaire for chart ID: $chart_id"

  # Make sure we have a valid session
  if [[ -z "$SESSION_TOKEN" ]]; then
    log_message "INFO" "No session token available. Initializing session."
    if ! init_session; then
      log_message "ERROR" "Failed to initialize session"
      return 1
    fi
  fi

  # Establish WebSocket connection if not already connected
  if [[ "$CONNECTION_STATE" != "CONNECTED" ]]; then
    if ! establish_connection; then
      log_message "ERROR" "Failed to establish WebSocket connection"
      return 1
    fi
  fi

  # Initialize the questionnaire via REST API
  echo -e "${CYAN}Creating questionnaire for chart ID: $chart_id${NC}"
  local questionnaire_data="{\"chart_id\": \"$chart_id\"}"
  local questionnaire_response=$(api_request "POST" "/questionnaire" "$questionnaire_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to initialize questionnaire"
    return 1
  fi

  # Extract questionnaire ID (sessionId)
  local questionnaire_id=$(echo "$questionnaire_response" | jq -r '.sessionId // empty')
  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "Failed to extract questionnaire ID from response"
    return 1
  fi

  echo -e "${GREEN}Questionnaire created with ID: $questionnaire_id${NC}"

  # Subscribe to the questionnaire-specific channel
  local channel="questionnaire_$questionnaire_id"
  if ! subscribe_to_channel "$channel"; then
    log_message "ERROR" "Failed to subscribe to questionnaire channel"
    return 1
  fi

  echo -e "\n${BOLD}Interactive Birth Time Rectification Questionnaire${NC}"
  echo -e "Please answer the following questions to help rectify the birth time:"
  echo -e "-------------------------------------------------------------------"

  # Extract first question from the initial response
  local question_id=$(echo "$questionnaire_response" | jq -r '.question.id // empty')
  local question_text=$(echo "$questionnaire_response" | jq -r '.question.text // .question.question // empty')

  if [[ -z "$question_id" || -z "$question_text" ]]; then
    log_message "ERROR" "Failed to extract question details from initial response"
    return 1
  fi

  # Process questions in a loop until complete
  local is_complete=false
  while [[ "$is_complete" != "true" ]]; do
    # Display the current question
    echo -e "\n${CYAN}Question: $question_text${NC}"

    # Get user input and send answer
    read -p "Your answer: " user_answer

    # Format and send the answer
    local answer_msg="{\"type\": \"answer\", \"questionnaire_id\": \"$questionnaire_id\", \"question_id\": \"$question_id\", \"answer\": \"$user_answer\"}"
    if ! send_message "$answer_msg"; then
      log_message "ERROR" "Failed to send answer"
      return 1
    fi

    # Wait for next question or completion message
    local next_message=$(wait_for_message 10)
    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Failed to receive response after submitting answer"
      return 1
    fi

    # Check if questionnaire is complete
    local complete_flag=$(echo "$next_message" | jq -r '.complete // false')
    if [[ "$complete_flag" == "true" ]]; then
      is_complete=true
      echo -e "\n${GREEN}Questionnaire completed successfully!${NC}"
      break
    fi

    # Extract next question
    question_id=$(echo "$next_message" | jq -r '.question.id // .id // empty')
    question_text=$(echo "$next_message" | jq -r '.question.text // .question // empty')

    if [[ -z "$question_id" || -z "$question_text" ]]; then
      log_message "ERROR" "Failed to extract next question details"
      return 1
    fi
  done

  # Unsubscribe from the channel
  if ! unsubscribe_from_channel "$channel"; then
    log_message "WARNING" "Failed to unsubscribe from questionnaire channel"
  fi

  log_message "INFO" "Interactive questionnaire completed successfully"
  return 0
}

# Close the established WebSocket connection and clean up resources
close_connection() {
  if [[ -n "$WS_PID" ]] && ps -p $WS_PID > /dev/null; then
    log_message "INFO" "Closing WebSocket connection"
    kill $WS_PID 2>/dev/null
    WS_PID=""
    CONNECTION_STATE="DISCONNECTED"
  fi

  # Kill background processes
  if [[ -n "$WS_HEARTBEAT_PID" ]] && ps -p $WS_HEARTBEAT_PID > /dev/null; then
    kill $WS_HEARTBEAT_PID 2>/dev/null
    WS_HEARTBEAT_PID=""
  fi

  if [[ -n "$WS_PROCESSOR_PID" ]] && ps -p $WS_PROCESSOR_PID > /dev/null; then
    kill $WS_PROCESSOR_PID 2>/dev/null
    WS_PROCESSOR_PID=""
  fi

  # Remove temporary files
  rm -f "$WS_DATA_FILE" 2>/dev/null

  # Don't remove the input pipe as it might be reused
  # but make sure it's empty
  if [[ -p "$WS_INPUT_PIPE" ]]; then
    > "$WS_INPUT_PIPE" 2>/dev/null
  fi

  return 0
}

# Cleanup on script exit
cleanup_websocket() {
  close_connection
}

# Register cleanup on exit
trap cleanup_websocket EXIT

# Export functions and variables
export WS_URL WS_PID CONNECTION_STATE
export -f check_websocat ws_connect ws_send ws_close
export -f establish_connection send_message wait_for_message close_connection
export -f run_interactive_questionnaire_ws
