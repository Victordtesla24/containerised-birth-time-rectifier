#!/bin/bash

# WebSocket client for communication with the server
# Dependencies: websocat, jq

WS_PORT=${WS_PORT:-8081}
WS_HOST=${WS_HOST:-localhost}
WS_URL="ws://$WS_HOST:$WS_PORT"
WS_PID=""
WS_DATA_FILE="/tmp/ws_data.$$"

# Establish WebSocket connection
establish_connection() {
  log_message "INFO" "Establishing WebSocket connection to $WS_URL"

  # Check if websocat is installed
  if ! command -v websocat >/dev/null 2>&1; then
    log_message "ERROR" "websocat is not installed, required for WebSocket connection"
    return 1
  fi

  # Start websocat in the background, redirecting output to a temporary file
  websocat --ping-interval 10 "$WS_URL" > "$WS_DATA_FILE" 2>/dev/null &
  WS_PID=$!

  # Check if the process started
  if ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "Failed to start WebSocket connection"
    WS_PID=""
    return 1
  fi

  # Wait a moment for the connection to establish
  sleep 2

  # Check if the process is still running (connection still active)
  if ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "WebSocket connection failed to establish"
    WS_PID=""
    rm -f "$WS_DATA_FILE" 2>/dev/null
    return 1
  fi

  log_message "INFO" "WebSocket connection established"
  return 0
}

# Send message through the WebSocket connection
send_message() {
  local message="$1"

  if [[ -z "$WS_PID" ]] || ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "No active WebSocket connection"
    return 1
  fi

  log_message "DEBUG" "Sending WebSocket message: $message"
  echo "$message" > /proc/$WS_PID/fd/0 2>/dev/null

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to send WebSocket message"
    return 1
  fi

  return 0
}

# Wait for message from the WebSocket connection
wait_for_message() {
  local timeout=${1:-5}
  local time_waited=0
  local interval=0.5
  local message=""

  if [[ -z "$WS_PID" ]] || ! ps -p $WS_PID > /dev/null; then
    log_message "ERROR" "No active WebSocket connection"
    return 1
  fi

  log_message "DEBUG" "Waiting for WebSocket message (timeout: ${timeout}s)"

  while [[ $time_waited -lt $timeout ]]; do
    # Check if there's data in the file
    if [[ -s "$WS_DATA_FILE" ]]; then
      message=$(cat "$WS_DATA_FILE")
      # Clear the file after reading
      > "$WS_DATA_FILE"

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

# Close the WebSocket connection
close_connection() {
  if [[ -n "$WS_PID" ]] && ps -p $WS_PID > /dev/null; then
    log_message "INFO" "Closing WebSocket connection"
    kill $WS_PID 2>/dev/null
    WS_PID=""
  fi

  # Remove the temporary file
  rm -f "$WS_DATA_FILE" 2>/dev/null
  return 0
}

# Cleanup on script exit
cleanup_websocket() {
  close_connection
}

# Register cleanup on exit
trap cleanup_websocket EXIT
