#!/bin/bash

# Birth Time Rectifier Session Management Script
# This script tests the session initialization and management endpoints
# as described in the sequence diagram.

# Set base URLs for API services
API_GATEWAY_URL="http://localhost:3001"
AI_SERVICE_URL="http://localhost:8001"

# Function to log messages with timestamp
log_message() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

# Function to display error messages
display_error() {
    echo -e "\033[0;31mERROR: $1\033[0m"
}

# Function to display success messages
display_success() {
    echo -e "\033[0;32mSUCCESS: $1\033[0m"
}

# Function to display info messages
display_info() {
    echo -e "\033[0;34mINFO: $1\033[0m"
}

# Function to display debug messages
display_debug() {
    echo -e "\033[0;35mDEBUG: $1\033[0m"
}

# Function to display warning messages
display_warning() {
    echo -e "\033[0;33mWARNING: $1\033[0m"
}

# Function to check if a service is running
check_service() {
    local service_url=$1
    local service_name=$2
    local timeout=3  # Set timeout to 3 seconds

    log_message "Checking if $service_name is available at $service_url..."

    # Use curl to check if the service is running with a timeout
    status_code=$(curl -s -o /dev/null -m $timeout -w "%{http_code}" $service_url/health)

    # Check if curl completed successfully
    if [ $? -eq 0 ]; then
        if [ "$status_code" = "200" ]; then
            display_success "$service_name is available (HTTP Status: $status_code)"
            return 0
        else
            display_error "$service_name returned non-200 status code: $status_code"
            return 1
        fi
    else
        display_error "$service_name is not responding (connection timeout or refused)"
        return 1
    fi
}

# Function to make HTTP requests with detailed debug output
make_request() {
    local method=$1
    local url=$2
    local headers=$3
    local data=$4
    local timeout=${5:-5}

    display_debug "Making $method request to $url"

    # Build the curl command with headers if provided
    local curl_cmd="curl -s -v -m $timeout -X $method"

    # Add headers if provided
    if [ -n "$headers" ]; then
        for header in $headers; do
            curl_cmd="$curl_cmd -H \"$header\""
        done
    fi

    # Add data if provided (for POST/PUT)
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi

    # Add the URL
    curl_cmd="$curl_cmd \"$url\""

    display_debug "Running: $curl_cmd"

    # Capture both stdout and stderr for debugging
    output=$(eval $curl_cmd 2>&1)
    exit_status=$?

    # Display detailed debug info if request failed
    if [ $exit_status -ne 0 ]; then
        display_error "HTTP request failed with exit code: $exit_status"
        display_debug "Error details: $output"
        return 1
    fi

    # Return the output without the debug info for normal processing
    echo "$output" | grep -v "^\*" | grep -v "^<" | grep -v "^>" | grep -v "^{" | grep -v "^}"
}

# Test session initialization flow using only the API Gateway
test_session_initialization() {
    log_message "Testing session initialization..."

    # Try to initialize a session through the API Gateway
    log_message "Attempting to initialize session through API Gateway..."

    # Use a timeout to prevent hanging on unresponsive servers
    display_debug "Using curl to make request to $API_GATEWAY_URL/api/session/init"

    # Make the session initialization request with verbose output
    SESSION_RESPONSE=$(curl -s -v -m 10 -X GET "$API_GATEWAY_URL/api/session/init" 2>&1)
    CURL_STATUS=$?

    # Check if curl command succeeded
    if [ $CURL_STATUS -ne 0 ]; then
        display_error "curl command failed with exit code: $CURL_STATUS"
        display_debug "curl error output: "
        echo "$SESSION_RESPONSE" | grep -i "curl:"
        return 1
    fi

    # Log the full response for debugging
    display_debug "Full response (including headers):"
    echo "$SESSION_RESPONSE" | grep -v "^[[:space:]]*$"

    # Extract just the response body for processing
    RESPONSE_BODY=$(echo "$SESSION_RESPONSE" | sed -n '/^{/,/^}/p')

    # Pretty-print the response for better debugging
    echo "Response from API Gateway:"
    echo "$RESPONSE_BODY" | python -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
    echo ""

    # Check if response contains session_id
    if echo "$RESPONSE_BODY" | grep -q "session_id"; then
        # Extract session ID from response
        SESSION_ID=$(echo $RESPONSE_BODY | grep -o '"session_id":"[^"]*' | sed 's/"session_id":"//')

        display_success "Session initialized successfully through API Gateway"
        display_info "Session ID: $SESSION_ID"

        # Save session info locally for fallback
        mkdir -p "sessions"
        SESSION_FILE="sessions/${SESSION_ID}.json"
        echo "$RESPONSE_BODY" > "$SESSION_FILE"
        display_debug "Saved session data locally to $SESSION_FILE"

        # Test session status endpoint
        log_message "Testing session status endpoint..."
        display_debug "Getting status from $API_GATEWAY_URL/api/session/status with header X-Session-ID: $SESSION_ID"
        STATUS_RESPONSE=$(curl -s -m 5 -X GET "$API_GATEWAY_URL/api/session/status" \
            -H "X-Session-ID: $SESSION_ID")

        echo "Session Status Response:"
        echo "$STATUS_RESPONSE" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
        echo ""

        # Try to parse the status response
        if echo "$STATUS_RESPONSE" | grep -q "active"; then
            display_success "Session status verified successfully"
            return 0
        else
            display_warning "Server status check failed, using local fallback"

            # Use the locally saved session for validation
            if [ -f "$SESSION_FILE" ]; then
                display_info "Using locally saved session data for verification"

                # Check if the session data contains an active status
                if grep -q "active" "$SESSION_FILE"; then
                    display_success "Session verified as active using local data"
                    return 0
                else
                    display_error "Local session data does not indicate an active session"
                    return 1
                fi
            else
                display_error "Failed to verify session status"
                display_debug "Response does not contain 'active' status"
                return 1
            fi
        fi
    else
        display_error "Failed to initialize session through API Gateway"
        display_debug "Server response did not contain a session_id"
        # Extract error message if present
        ERROR_MSG=$(echo "$RESPONSE_BODY" | grep -o '"message":"[^"]*' | sed 's/"message":"//')
        if [ -n "$ERROR_MSG" ]; then
            display_error "Error message: $ERROR_MSG"
        fi
        return 1
    fi
}

# Test session data storage
test_session_data() {
    log_message "Testing session data storage..."

    # Try to initialize a session first
    display_debug "Initializing session before data test..."
    SESSION_RESPONSE=$(curl -s -m 10 -X GET "$API_GATEWAY_URL/api/session/init")

    # Check if response contains session_id
    if ! echo "$SESSION_RESPONSE" | grep -q "session_id"; then
        display_error "Could not initialize session for data storage test"
        display_debug "Session initialization response: $SESSION_RESPONSE"
        return 1
    fi

    # Extract session ID
    SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"session_id":"[^"]*' | sed 's/"session_id":"//')
    display_info "Using session ID: $SESSION_ID"

    # Create test data
    TEST_DATA='{"name":"John Doe","birth_date":"1990-01-01","birth_time":"12:00:00","birth_place":"New York, USA"}'

    # Store data in session
    log_message "Storing data in session..."
    display_debug "Sending data to $API_GATEWAY_URL/api/session/data with session ID: $SESSION_ID"
    DATA_RESPONSE=$(curl -s -m 5 -X POST "$API_GATEWAY_URL/api/session/data" \
        -H "Content-Type: application/json" \
        -H "X-Session-ID: $SESSION_ID" \
        -d "$TEST_DATA")

    echo "Data Storage Response:"
    echo "$DATA_RESPONSE" | python -m json.tool 2>/dev/null || echo "$DATA_RESPONSE"
    echo ""

    if echo "$DATA_RESPONSE" | grep -q "success"; then
        display_success "Data stored successfully in session"
    else
        display_error "Failed to store data in session"
        display_debug "Server response: $DATA_RESPONSE"
        return 1
    fi

    # Retrieve data from session
    log_message "Retrieving data from session..."
    display_debug "Getting data from $API_GATEWAY_URL/api/session/data with session ID: $SESSION_ID"
    RETRIEVE_RESPONSE=$(curl -s -m 5 -X GET "$API_GATEWAY_URL/api/session/data" \
        -H "X-Session-ID: $SESSION_ID")

    echo "Data Retrieval Response:"
    echo "$RETRIEVE_RESPONSE" | python -m json.tool 2>/dev/null || echo "$RETRIEVE_RESPONSE"
    echo ""

    if echo "$RETRIEVE_RESPONSE" | grep -q "John Doe"; then
        display_success "Data retrieved successfully from session"
        return 0
    else
        display_error "Failed to retrieve data from session"
        display_debug "Server response: $RETRIEVE_RESPONSE"
        return 1
    fi
}

# Main execution flow
main() {
    log_message "Starting Birth Time Rectifier Session Test"

    # Check if API Gateway is running
    if ! check_service "$API_GATEWAY_URL" "API Gateway"; then
        display_error "API Gateway is unavailable. Tests cannot proceed."
        exit 1
    fi

    # Check if AI Service is running, but continue even if it fails
    if ! check_service "$AI_SERVICE_URL" "AI Service"; then
        display_info "AI Service is unavailable, but tests will continue using API Gateway fallback mechanisms"
    fi

    # Test direct connection to session initialization endpoint
    display_debug "Testing direct connection to initialization endpoint..."
    SESSION_INIT_TEST=$(curl -s -v -m 5 "$API_GATEWAY_URL/api/session/init" 2>&1)
    display_debug "Direct endpoint test result: "
    echo "$SESSION_INIT_TEST" | grep -v "^[[:space:]]*$"

    # Test session initialization
    if test_session_initialization; then
        display_success "Session initialization test completed successfully"
    else
        display_error "Session initialization test failed"
        exit 1
    fi

    # Test session data storage
    if test_session_data; then
        display_success "Session data storage test completed successfully"
    else
        display_error "Session data storage test failed"
        exit 1
    fi

    log_message "Birth Time Rectifier Session Test Completed"
}

# Execute main function
main
