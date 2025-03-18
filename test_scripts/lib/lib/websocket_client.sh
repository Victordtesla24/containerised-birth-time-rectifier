#!/bin/bash

# WebSocket Client
# Handles WebSocket connections and message exchange

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Source API client functions for session management
if [[ -z "$API_URL" ]]; then
  source "$(dirname "$0")/api_client.sh"
fi

# WebSocket process ID
WS_PID=""
# WebSocket log file
WS_LOG_FILE="/tmp/ws_log_$(date +%s).log"
# WebSocket connection status
WS_CONNECTED=false
# Retry count
WS_RETRY_COUNT=0
# Max retry count
WS_MAX_RETRY=5
# Base delay for exponential backoff (in seconds)
WS_BASE_DELAY=1

# Function to create WebSocket connection
connect_websocket() {
  local stream_name="${1:-userDataStream}"

  # Make sure we have a valid session
  if [[ -z "$SESSION_TOKEN" ]]; then
    log_message "ERROR" "No session token available. Run init_session first."
    return 1
  fi

  log_message "INFO" "Establishing WebSocket connection to stream: $stream_name"
  log_message "INFO" "WebSocket URL: $WS_URL/$stream_name?listenKey=$SESSION_TOKEN"

  # Check if websocat is installed
  if ! command -v websocat >/dev/null 2>&1; then
    log_message "ERROR" "websocat is required for WebSocket connections. Please install it."
    return 1
  fi

  # Create WebSocket connection in background
  websocat --no-close -t "$WS_URL/$stream_name?listenKey=$SESSION_TOKEN" > "$WS_LOG_FILE" 2>&1 &
  WS_PID=$!

  # Wait for connection to establish
  sleep 2

  # Check if connection succeeded
  if ! ps -p $WS_PID > /dev/null 2>&1; then
    log_message "ERROR" "Failed to establish WebSocket connection"
    return 1
  fi

  WS_CONNECTED=true
  WS_RETRY_COUNT=0
  log_message "INFO" "WebSocket connection established successfully with PID: $WS_PID"

  # Start monitoring the connection in the background
  monitor_websocket_connection &

  return 0
}

# Function to monitor WebSocket connection and reconnect if necessary
monitor_websocket_connection() {
  local monitor_pid=$$
  log_message "INFO" "Starting WebSocket connection monitor with PID: $monitor_pid"

  while true; do
    # Check if WebSocket process is still running
    if [[ "$WS_CONNECTED" = true ]] && ! ps -p $WS_PID > /dev/null 2>&1; then
      log_message "WARN" "WebSocket connection lost. Attempting to reconnect..."
      WS_CONNECTED=false

      # Calculate delay with exponential backoff
      local delay=$((WS_BASE_DELAY * 2**WS_RETRY_COUNT))
      if [[ $delay -gt 60 ]]; then
        delay=60
      fi

      log_message "INFO" "Waiting $delay seconds before reconnecting (attempt $((WS_RETRY_COUNT+1))/$WS_MAX_RETRY)"
      sleep $delay

      # Increment retry count
      WS_RETRY_COUNT=$((WS_RETRY_COUNT+1))

      # Attempt to reconnect
      if [[ $WS_RETRY_COUNT -le $WS_MAX_RETRY ]]; then
        if connect_websocket; then
          log_message "INFO" "Successfully reconnected to WebSocket"
          WS_RETRY_COUNT=0
        else
          log_message "ERROR" "Failed to reconnect to WebSocket"
        fi
      else
        log_message "FATAL" "Maximum reconnection attempts ($WS_MAX_RETRY) reached. Giving up."
        return 1
      fi
    fi

    # Check every 5 seconds
    sleep 5
  done
}

# Function to send message to WebSocket
send_websocket_message() {
  local message="$1"

  if [[ "$WS_CONNECTED" != true ]]; then
    log_message "ERROR" "WebSocket is not connected. Cannot send message."
    return 1
  fi

  log_message "INFO" "Sending WebSocket message: $message"

  # Use process substitution to send message to the WebSocket process
  echo "$message" > /proc/$WS_PID/fd/0

  log_message "INFO" "Message sent to WebSocket"
  return 0
}

# Function to read messages from WebSocket
read_websocket_messages() {
  local timeout="${1:-5}"

  if [[ "$WS_CONNECTED" != true ]]; then
    log_message "ERROR" "WebSocket is not connected. Cannot read messages."
    return 1
  fi

  log_message "INFO" "Reading WebSocket messages (timeout: ${timeout}s)"

  # Read the WebSocket log file
  if [[ -f "$WS_LOG_FILE" ]]; then
    local start_time=$(date +%s)
    local end_time=$((start_time + timeout))
    local current_time=$start_time

    while [[ $current_time -lt $end_time ]]; do
      # Check if any new messages are available
      if [[ -s "$WS_LOG_FILE" ]]; then
        cat "$WS_LOG_FILE"
        > "$WS_LOG_FILE"  # Clear the file after reading
        log_message "INFO" "WebSocket messages read successfully"
        return 0
      fi

      # Wait a bit before checking again
      sleep 1
      current_time=$(date +%s)
    done

    log_message "WARN" "No WebSocket messages received within timeout"
    return 0
  else
    log_message "ERROR" "WebSocket log file not found"
    return 1
  fi
}

# Function to subscribe to a specific channel
subscribe_to_channel() {
  local channel="$1"
  local params="${2:-{}}"

  log_message "INFO" "Subscribing to channel: $channel with params: $params"

  # Create subscription message
  local subscription_msg="{\"method\":\"SUBSCRIBE\",\"params\":[\"$channel\"],\"id\":$(date +%s)}"

  # Send subscription request
  if ! send_websocket_message "$subscription_msg"; then
    log_message "ERROR" "Failed to send subscription request"
    return 1
  fi

  log_message "INFO" "Subscription request sent for channel: $channel"
  return 0
}

# Function to unsubscribe from a specific channel
unsubscribe_from_channel() {
  local channel="$1"

  log_message "INFO" "Unsubscribing from channel: $channel"

  # Create unsubscription message
  local unsubscription_msg="{\"method\":\"UNSUBSCRIBE\",\"params\":[\"$channel\"],\"id\":$(date +%s)}"

  # Send unsubscription request
  if ! send_websocket_message "$unsubscription_msg"; then
    log_message "ERROR" "Failed to send unsubscription request"
    return 1
  fi

  log_message "INFO" "Unsubscription request sent for channel: $channel"
  return 0
}

# Function to close WebSocket connection
close_websocket() {
  log_message "INFO" "Closing WebSocket connection"

  if [[ -n "$WS_PID" ]] && ps -p $WS_PID > /dev/null 2>&1; then
    kill $WS_PID
    log_message "INFO" "WebSocket process killed"
  fi

  if [[ -f "$WS_LOG_FILE" ]]; then
    rm -f "$WS_LOG_FILE"
    log_message "INFO" "WebSocket log file removed"
  fi

  WS_CONNECTED=false
  WS_PID=""
  log_message "INFO" "WebSocket connection closed"
  return 0
}

# Function to run WebSocket tests
run_websocket_tests() {
  log_message "INFO" "Running WebSocket tests"

  # Make sure we have a valid session
  if [[ -z "$SESSION_TOKEN" ]]; then
    log_message "INFO" "No session token available. Initializing session."
    if ! init_session; then
      log_message "FATAL" "Failed to initialize session"
      return 1
    fi
  fi

  # Connect to WebSocket
  if ! connect_websocket "userDataStream"; then
    log_message "ERROR" "Failed to connect to WebSocket"
    return 1
  fi

  # Subscribe to kline updates for BTCUSDT
  if ! subscribe_to_channel "btcusdt@kline_1m"; then
    log_message "ERROR" "Failed to subscribe to kline updates"
    close_websocket
    return 1
  fi

  # Wait for some messages
  log_message "INFO" "Waiting for WebSocket messages..."
  sleep 5

  # Read and display received messages
  if ! read_websocket_messages 10; then
    log_message "ERROR" "Failed to read WebSocket messages"
    close_websocket
    return 1
  fi

  # Unsubscribe from kline updates
  if ! unsubscribe_from_channel "btcusdt@kline_1m"; then
    log_message "ERROR" "Failed to unsubscribe from kline updates"
    close_websocket
    return 1
  fi

  # Test user data updates by creating a mock order
  log_message "INFO" "Testing user data updates..."
  local order_data='{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "0.001",
    "price": "50000"
  }'

  # Create an order through the API
  local api_response=$(api_request "POST" "/order" "$order_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create test order"
    close_websocket
    return 1
  fi

  # Wait for order update in WebSocket
  log_message "INFO" "Waiting for order update in WebSocket..."
  sleep 5

  # Read and display received messages
  if ! read_websocket_messages 10; then
    log_message "ERROR" "Failed to read WebSocket messages"
    close_websocket
    return 1
  fi

  # Clean up by closing the WebSocket connection
  if ! close_websocket; then
    log_message "ERROR" "Failed to close WebSocket connection"
    return 1
  fi

  log_message "INFO" "WebSocket tests completed successfully"
  return 0
}

# Export functions
export -f connect_websocket close_websocket send_websocket_message read_websocket_messages subscribe_to_channel unsubscribe_from_channel monitor_websocket_connection run_websocket_tests
