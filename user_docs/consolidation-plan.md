## RUN SIMPLE TEST SHELL SCRIPT ARCHITECTURE

1. Modular Script Architecture
 - Following best practices for shell script organization, I recommend refactoring the script into a modular structure:
 ```bash
 test_scripts/
 ├── run-simple-test.sh              # Main entry point
 ├── lib/
 │   ├── common.sh                   # Common functions, colors, formatting
 │   ├── api_client.sh               # API interaction functions
 │   ├── websocket_client.sh         # WebSocket handling functions
 │   ├── chart_operations.sh         # Chart-specific operations
 │   ├── questionnaire_operations.sh # Questionnaire-specific operations
 │   └── validation.sh               # Input and output validation functions
 ├── config/
 │   └── defaults.conf               # Configuration parameters
 └── tests/
     └── unit_tests.sh               # Tests for script components
 ```

2. Robust Error Handling Framework
 - Implement a consistent error handling framework:
 ```bash
 # Error handling framework
 ERROR_LEVELS=("INFO" "WARNING" "ERROR" "FATAL")

 log_message() {
  local level="$1"
  local message="$2"
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo -e "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"

  # Exit on fatal errors
  if [[ "$level" == "FATAL" ]]; then
    exit 1
  fi
 }

 # Usage
 log_message "ERROR" "WebSocket connection failed: $error_details"
 ```

3. Connection Management Best Practices
 - For containerized applications with WebSocket connections:

 1. Progressive Connection Strategy:
 ```bash
   establish_connection() {
     # Try direct connection first
     if direct_connection; then
       return 0
     fi

     # Try connection through proxy
     if proxy_connection; then
       return 0
     fi

     # Try alternative protocols
     if alternative_protocol_connection; then
       return 0
     fi

     return 1
   }
 ```

 2. State Management:
 ```bash
   # Define connection states
   CONNECTION_STATES=("DISCONNECTED" "CONNECTING" "CONNECTED" "RECONNECTING" "FAILED")
   current_state="DISCONNECTED"

   update_connection_state() {
     previous_state="$current_state"
     current_state="$1"
     log_message "INFO" "Connection state change: $previous_state -> $current_state"

     # Execute state transition hooks
     if type "on_${previous_state}_to_${current_state}" &>/dev/null; then
       "on_${previous_state}_to_${current_state}"
     fi
   }
 ```

4. API Client Architecture
 - Implement a robust API client pattern:
 ```bash
 # API Client with automatic retry
 api_request() {
  local method="$1"
  local endpoint="$2"
  local data="$3"
  local max_retries=3
  local retry_count=0

  while [[ $retry_count -lt $max_retries ]]; do
    response=$(curl -s -X "$method" "${API_URL}${endpoint}" \
      -H "Authorization: Bearer ${SESSION_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$data")

    if [[ $? -eq 0 && ! -z "$response" ]]; then
      echo "$response"
      return 0
    fi

    retry_count=$((retry_count + 1))
    log_message "WARNING" "API request failed, retrying ($retry_count/$max_retries)"
    sleep $((2 ** retry_count))  # Exponential backoff
  done

  log_message "ERROR" "API request failed after $max_retries attempts"
  return 1
 }
 ```

5. Test Session Management
 - Implement proper session lifecycle management:
 ```bash
 # Session management
 init_session() {
  # Create session
  local response=$(api_request "POST" "/session/init" "{}")
  SESSION_TOKEN=$(echo "$response" | jq -r '.session_id // empty')

  if [[ -z "$SESSION_TOKEN" ]]; then
    log_message "FATAL" "Failed to initialize session"
    return 1
  fi

  # Register cleanup on exit
  trap cleanup_session EXIT

  # Start token refresh timer
  start_token_refresh_timer

  return 0
 }

 cleanup_session() {
  if [[ ! -z "$SESSION_TOKEN" ]]; then
    api_request "POST" "/session/end" "{\"session_id\": \"$SESSION_TOKEN\"}"
    SESSION_TOKEN=""
  fi
 }
 ```

## Implementation Recommendations
 1. To implement these improvements while maintaining current functionality:
    - Gradual Refactoring Strategy:
    - Start by extracting common functions to a separate file
    - Implement the improved error handling framework
    - Refactor one endpoint interaction at a time
    - Add unit tests for each refactored component

 2. WebSocket Connection Improvement:
    - Add proper handshake diagnostic output
    - Implement connection health monitoring

 3. API Endpoint Validation:
    - Add a startup validation phase that tests each API endpoint
    - Implement schema validation for API responses
    - Create environment-specific configuration options

 4. Dockerized Test Environment:
    - Implement network simulation for testing connection issues
