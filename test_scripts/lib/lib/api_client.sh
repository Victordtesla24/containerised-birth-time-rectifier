#!/bin/bash

# API Client functions
# Handles API interactions with error handling and retries

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Default API URL - updated to use v1 endpoint
API_URL=${API_URL:-"http://localhost:9000/api/v1"}
SESSION_TOKEN=""

# API Client with automatic retry
api_request() {
  local method="$1"
  local endpoint="$2"
  local data="$3"
  local max_retries=3
  local retry_count=0
  local timeout=10

  # Add auth header if we have a session token
  local auth_header=""
  if [[ ! -z "$SESSION_TOKEN" ]]; then
    auth_header="-H \"Authorization: Bearer ${SESSION_TOKEN}\""
  fi

  while [[ $retry_count -lt $max_retries ]]; do
    if [[ "$VERBOSE" == "true" ]]; then
      log_message "INFO" "Making ${method} request to ${endpoint}"
    fi

    # Construct and execute the curl command with timeout
    local curl_cmd="curl -s -X \"${method}\" \"${API_URL}${endpoint}\" \
      ${auth_header} \
      -H \"Content-Type: application/json\" \
      -m ${timeout} \
      -d '${data}'"

    response=$(eval ${curl_cmd})
    local curl_status=$?

    if [[ $curl_status -eq 0 ]]; then
      # Check for empty response
      if [[ -z "$response" ]]; then
        log_message "WARNING" "Empty response received from API"
        retry_count=$((retry_count + 1))
        sleep $((2 ** retry_count))  # Exponential backoff
        continue
      fi

      # Check if response is valid JSON
      if ! echo "$response" | jq empty &>/dev/null; then
        log_message "WARNING" "Invalid JSON response: $response"
        retry_count=$((retry_count + 1))
        sleep $((2 ** retry_count))  # Exponential backoff
        continue
      fi

      # Check for error in response
      local error=$(echo "$response" | jq -r '.error // empty')
      if [[ ! -z "$error" && "$error" != "null" ]]; then
        log_message "ERROR" "API error: $error"
        return 1
      fi

      # Return the response
      echo "$response"
      return 0
    fi

    retry_count=$((retry_count + 1))
    log_message "WARNING" "API request failed (status: $curl_status), retrying ($retry_count/$max_retries)"
    sleep $((2 ** retry_count))  # Exponential backoff
  done

  log_message "ERROR" "API request failed after $max_retries attempts"
  return 1
}

# Session management - simplified for testing
init_session() {
  log_message "INFO" "Initializing session..."

  # For testing without real session endpoints, we'll use a mock session token
  SESSION_TOKEN="test-session-$(date +%s)"

  log_message "INFO" "Session initialized successfully with mock ID: ${SESSION_TOKEN}"
  return 0
}

# Function to validate API endpoints
validate_api_endpoints() {
  log_message "INFO" "Validating API endpoints..."

  # List of critical endpoints to check
  local endpoints=(
    "GET /health"
  )

  local failed=0

  for endpoint in "${endpoints[@]}"; do
    local method=$(echo "$endpoint" | cut -d ' ' -f 1)
    local path=$(echo "$endpoint" | cut -d ' ' -f 2)

    log_message "INFO" "Checking endpoint: $method $path"

    local response=$(api_request "$method" "$path" "{}")
    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Endpoint validation failed: $method $path"
      failed=$((failed + 1))
    else
      log_message "INFO" "Endpoint validation succeeded: $method $path"
    fi
  done

  if [[ $failed -gt 0 ]]; then
    log_message "ERROR" "$failed endpoints failed validation"
    return 1
  fi

  log_message "INFO" "All endpoints validated successfully"
  return 0
}

# Export functions and variables
export API_URL SESSION_TOKEN
