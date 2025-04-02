#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    WEBSOCKET CONNECTION TESTER               ${NC}"
echo -e "${BLUE}===============================================${NC}"
echo

# Parse command line arguments
SESSION_ID=""

for arg in "$@"
do
    case $arg in
        --session=*)
        SESSION_ID="${arg#*=}"
        shift
        ;;
        *)
        # Unknown option
        ;;
    esac
done

# If no session ID provided, create a random one
if [ -z "$SESSION_ID" ]; then
    SESSION_ID="ws-test-$(date +%s)"
    echo -e "${YELLOW}No session ID provided. Using generated ID: $SESSION_ID${NC}"
fi

# Use API Gateway WebSocket endpoint instead of AI Service directly
# Updated to use port 3001 (API Gateway) instead of 8001 (AI Service)
WS_URL="ws://localhost:3001/ws/${SESSION_ID}"

echo "=== WebSocket Connection Details ==="
echo -e "Session ID: ${CYAN}$SESSION_ID${NC}"
echo -e "WebSocket URL: ${CYAN}$WS_URL${NC}"
echo

echo "=== Testing WebSocket Connection ==="
echo -e "Connecting to WebSocket server..."
echo -e "Press Ctrl+C to terminate the connection"
echo -e "Any messages received from the server will be displayed below:"
echo -e "-----------------------------------------------"

# Check if websocat is installed
if ! command -v websocat &> /dev/null; then
    echo -e "${RED}websocat not found. Cannot test WebSocket connection.${NC}"
    echo -e "${YELLOW}Please install websocat using:${NC}"
    echo -e "brew install websocat (on macOS)"
    echo -e "or download from https://github.com/vi/websocat/releases"
else
    echo -e "${GREEN}websocat found, testing WebSocket connection${NC}"
    echo -e "Connecting to ${CYAN}$WS_URL${NC}..."
    echo -e "Press Ctrl+C after a few seconds to stop the WebSocket connection"

    # Connect to WebSocket endpoint and print received messages
    # Use a background process with sleep instead of timeout command for better cross-platform compatibility
    (
        # Run websocat in background
        websocat "$WS_URL" &
        WEBSOCAT_PID=$!

        # Sleep for 10 seconds then kill the process
        sleep 10
        kill $WEBSOCAT_PID 2>/dev/null || true
    )
fi

echo -e "-----------------------------------------------"
echo -e "WebSocket connection test completed."
echo

echo "=== Sending Test Event ==="
echo -e "Triggering an event that should send a WebSocket message..."

# Call test event endpoint to trigger a WebSocket message
curl -s -X POST -H "Content-Type: application/json" \
     -H "X-Session-ID: $SESSION_ID" \
     -d "{\"message\":\"Test event\",\"session_id\":\"$SESSION_ID\"}" \
     "http://localhost:3001/api/v1/test-event" > /dev/null

echo -e "Test event sent. You should see a message in the WebSocket connection if the server supports it."
echo -e "Note: If you didn't see any message, the server might not have implemented the test event endpoint."
echo

echo "=== Real-Time Progress Updates Test ==="
echo -e "To test real-time updates from an actual chart generation:"
echo -e "1. Keep this WebSocket connection open in one terminal"
echo -e "2. In another terminal, run:"
echo -e "   ./birth_time_rectifier_tester.sh"
echo -e "3. Enter your birth details when prompted"
echo -e "4. Watch for progress updates in this WebSocket window"
echo

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    WEBSOCKET TESTING COMPLETE                ${NC}"
echo -e "${BLUE}===============================================${NC}"
