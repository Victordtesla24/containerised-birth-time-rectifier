#!/bin/bash

# Test WebSocket connections for Birth Time Rectifier API Gateway
# This script tests WebSocket connections to the API Gateway

# Set default values
WS_URL="ws://localhost:9000/ws"
SESSION_ID=""
NUM_MESSAGES=5
DELAY=1
TIMEOUT=10

# Print usage information
function print_usage {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -u, --url URL         WebSocket URL (default: $WS_URL)"
    echo "  -s, --session ID      Session ID (default: auto-generated)"
    echo "  -n, --num NUM         Number of messages to send (default: $NUM_MESSAGES)"
    echo "  -d, --delay SECONDS   Delay between messages in seconds (default: $DELAY)"
    echo "  -t, --timeout SECONDS Connection timeout in seconds (default: $TIMEOUT)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                  # Run test with default settings"
    echo "  $0 -s test-session-123              # Run with specific session ID"
    echo "  $0 -n 10 -d 0.5                     # Send 10 messages with 0.5s delay"
    echo "  $0 -u ws://localhost:9001/ws        # Use alternate WebSocket URL"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            WS_URL="$2"
            shift 2
            ;;
        -s|--session)
            SESSION_ID="$2"
            shift 2
            ;;
        -n|--num)
            NUM_MESSAGES="$2"
            shift 2
            ;;
        -d|--delay)
            DELAY="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Check if websocat is installed
if ! command -v websocat &> /dev/null; then
    echo "Error: websocat is not installed."
    echo "Please install it using one of the following methods:"
    echo "  - Homebrew (macOS): brew install websocat"
    echo "  - Cargo (Rust): cargo install websocat"
    echo "  - Download binary from: https://github.com/vi/websocat/releases"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Warning: jq is not installed. JSON formatting will be disabled."
    echo "Consider installing jq for better output formatting:"
    echo "  - Homebrew (macOS): brew install jq"
    echo "  - apt (Debian/Ubuntu): apt install jq"
    echo "  - yum (CentOS/RHEL): yum install jq"
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

# Construct the full WebSocket URL with session ID if provided
FULL_URL="$WS_URL"
if [[ -n "$SESSION_ID" ]]; then
    FULL_URL="${WS_URL}/${SESSION_ID}"
fi

echo "=== WebSocket Connection Test ==="
echo "URL: $FULL_URL"
echo "Number of messages: $NUM_MESSAGES"
echo "Delay between messages: $DELAY seconds"
echo "Connection timeout: $TIMEOUT seconds"
echo "==============================="

# Function to generate a timestamp
function timestamp {
    date +"%Y-%m-%d %H:%M:%S.%3N"
}

# Function to format JSON if jq is available
function format_json {
    if [[ "$JQ_AVAILABLE" == true ]]; then
        echo "$1" | jq '.'
    else
        echo "$1"
    fi
}

# Create a temporary file for the received messages
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Start websocat in the background to receive messages
websocat --no-close -t "$FULL_URL" > "$TEMP_FILE" &
WEBSOCAT_PID=$!

# Wait for the connection to establish
sleep 1

# Check if websocat is still running
if ! kill -0 $WEBSOCAT_PID 2>/dev/null; then
    echo "Error: Failed to connect to WebSocket server at $FULL_URL"
    exit 1
fi

echo "[$(timestamp)] Connected to $FULL_URL"
echo "[$(timestamp)] Sending $NUM_MESSAGES messages..."

# Send echo messages
for ((i=1; i<=$NUM_MESSAGES; i++)); do
    # Create a message with the current timestamp
    MESSAGE="{\"type\":\"echo\",\"data\":\"Test message $i\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")\"}"

    # Send the message
    echo "[$(timestamp)] Sending: $MESSAGE"
    echo "$MESSAGE" | websocat -n1 "$FULL_URL" > /dev/null

    # Wait for the specified delay
    sleep "$DELAY"
done

# Send a heartbeat message
HEARTBEAT="{\"type\":\"heartbeat\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")\"}"
echo "[$(timestamp)] Sending heartbeat: $HEARTBEAT"
echo "$HEARTBEAT" | websocat -n1 "$FULL_URL" > /dev/null

# Wait for responses
echo "[$(timestamp)] Waiting for responses..."
sleep 2

# Kill the background websocat process
kill $WEBSOCAT_PID 2>/dev/null

# Display received messages
echo "[$(timestamp)] Received messages:"
cat "$TEMP_FILE" | while read -r line; do
    echo "[$(timestamp)] Received: $(format_json "$line")"
done

echo "[$(timestamp)] Test completed successfully"
exit 0
