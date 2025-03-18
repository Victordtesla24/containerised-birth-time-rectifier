#!/bin/bash

# API Client functions
# Handles API interactions with error handling and retries

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Default API URL - use Birth Time Rectifier API v1 endpoints
API_URL=${API_URL:-"http://localhost:9000/api/v1"}
SESSION_TOKEN=""
AUTH_HEADER=""

# API Client - direct, no retries
api_request() {
  local method="$1"
  local endpoint="$2"
  local data="$3"
  local timeout=10

  # Add auth header if we have a session token (optional)
  local auth_header=""
  if [[ ! -z "$SESSION_TOKEN" ]]; then
    auth_header="-H \"Authorization: Bearer ${SESSION_TOKEN}\""
  fi

  log_message "INFO" "Making ${method} request to ${endpoint}"
  log_message "DEBUG" "Request data: ${data}"

  # Construct and execute the curl command with timeout
  local curl_cmd="curl -s -X \"${method}\" \"${API_URL}${endpoint}\" \
    ${auth_header} \
    -H \"Content-Type: application/json\" \
    -m ${timeout} \
    -d '${data}'"

  # For debugging, show the full curl command
  log_message "DEBUG" "Executing curl command: ${curl_cmd}"

  # Add -v flag for verbose output if this is a questionnaire endpoint
  if [[ "$endpoint" == *"/questionnaire"* ]]; then
    curl_cmd=${curl_cmd/curl -s/curl -s -v}
    log_message "DEBUG" "Using verbose mode for questionnaire endpoint"
  fi

  response=$(eval ${curl_cmd} 2> /tmp/curl_error.log)
  local curl_status=$?

  # Log the error output if any
  if [[ -s /tmp/curl_error.log ]]; then
    log_message "DEBUG" "Curl verbose output: $(cat /tmp/curl_error.log)"
  fi

  if [[ $curl_status -ne 0 ]]; then
    log_message "ERROR" "API request failed with curl status: $curl_status"
    return 1
  fi

  # Check for empty response
  if [[ -z "$response" ]]; then
    log_message "ERROR" "Empty response received from API"
    return 1
  fi

  # Check if response is valid JSON
  if ! echo "$response" | jq empty &>/dev/null; then
    log_message "ERROR" "Invalid JSON response: $response"
    return 1
  fi

  # Check for error in response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ ! -z "$error" && "$error" != "null" ]]; then
    local msg=$(echo "$response" | jq -r '.detail // .message // "Unknown error"')
    log_message "ERROR" "API error: $error - $msg"
    return 1
  fi

  # Check for HTTP error status
  local status=$(echo "$response" | jq -r '.status // empty')
  if [[ ! -z "$status" && "$status" != "null" && "$status" -ge 400 ]]; then
    local msg=$(echo "$response" | jq -r '.detail // .message // "Unknown error"')
    log_message "ERROR" "API HTTP status $status: $msg"
    return 1
  fi

  # Return the response
  echo "$response"
  return 0
}

# Session management
init_session() {
  log_message "INFO" "Initializing session..."

  # Try to get a health check first to verify API connectivity
  local health_response=$(curl -s "$API_URL/health" -H "Content-Type: application/json")
  if [[ -z "$health_response" ]]; then
    log_message "ERROR" "Health check failed, API is unavailable"
    return 1
  fi

  # Make session initialization API call
  local session_response=$(curl -s "$API_URL/session/init" -H "Content-Type: application/json")
  log_message "DEBUG" "Session response: $session_response"

  # Extract session token from session_id field
  SESSION_TOKEN=$(echo "$session_response" | jq -r '.session_id // empty')
  log_message "DEBUG" "Extracted token: $SESSION_TOKEN"

  if [[ -z "$SESSION_TOKEN" || "$SESSION_TOKEN" == "null" ]]; then
    log_message "ERROR" "Failed to extract session token from response"
    return 1
  fi

  log_message "INFO" "Session initialized successfully with token: ${SESSION_TOKEN}"
  return 0
}

# Function to validate API endpoints
validate_api_endpoints() {
  log_message "INFO" "Validating API endpoints..."

  # List of critical endpoints from OpenAPI docs
  local endpoints=(
    "GET /health"
    "GET /chart/compare"
    "GET /chart/{chart_id}"
  )

  local failed=0

  for endpoint in "${endpoints[@]}"; do
    local method=$(echo "$endpoint" | cut -d ' ' -f 1)
    local path=$(echo "$endpoint" | cut -d ' ' -f 2)

    # Skip endpoints with path parameters
    if [[ "$path" == *"{chart_id}"* || "$path" == *"{id}"* ]]; then
      log_message "INFO" "Skipping endpoint with parameters: $path"
      continue
    fi

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

# Function to validate birth details with the API
validate_birth_details() {
  local birth_data="$1"

  log_message "INFO" "Validating birth details with API..."

  # Call the API to validate birth details
  local response=$(api_request "POST" "/chart/validate" "$birth_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API validation failed"
    return 1
  fi

  # Check validation result
  local is_valid=$(echo "$response" | jq -r '.valid // false')
  if [[ "$is_valid" != "true" ]]; then
    local error_message=$(echo "$response" | jq -r '.message // "Unknown validation error"')
    log_message "ERROR" "Validation failed: $error_message"
    return 1
  fi

  log_message "INFO" "Birth details validated successfully"
  return 0
}

# Export functions and variables
export API_URL SESSION_TOKEN
export -f api_request init_session validate_api_endpoints validate_birth_details
