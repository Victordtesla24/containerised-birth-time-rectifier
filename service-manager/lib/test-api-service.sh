#!/bin/bash

# ===========================================
# Test API Service Script
# ===========================================
# This script kills any processes on ports 8000, 3000, and 9000,
# then starts the AI service on port 9000 specifically for testing

# ANSI color codes
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# Print colored status messages
print_status() {
    local color=$1
    local symbol=$2
    local message=$3
    echo -e "${color}${symbol} ${message}${NC}"
}

echo "🧪 Starting Test API Service setup..."

# Kill any existing processes on the service ports
echo "🔄 Killing processes on service ports..."
sudo lsof -ti:8000,3000,9000 -sTCP:LISTEN | xargs -r sudo kill -9
sleep 1

# Create logs directory if it doesn't exist
mkdir -p logs

# Set environment variables for testing
export TEST_MODE=true
export API_PORT=9000

# Start the API service in the background
echo "🚀 Starting API service on port 9000 in the background..."
cd "$(dirname "$0")"
source .venv/bin/activate
# Run from the project root to ensure correct module paths
python -m uvicorn ai_service.api.main:app --host 0.0.0.0 --port 9000 --reload &
API_PID=$!

# Function to display API endpoints
display_api_endpoints() {
    local api_port=9000
    local endpoint_url="http://localhost:${api_port}/openapi.json"

    echo "📡 Retrieving API endpoints..."

    # Wait for API to start up
    echo "⏳ Waiting for API service to initialize..."
    sleep 5

    # Try to fetch the OpenAPI specification
    if ! curl -s "${endpoint_url}" -o /tmp/openapi_spec.json 2>/dev/null; then
        echo "❌ Failed to retrieve API endpoints. API may still be starting."
        echo "📝 You can view API documentation at http://localhost:${api_port}/docs once the service is running."
        return 1
    fi

    # Parse and display the OpenAPI specification
    if command -v jq >/dev/null 2>&1; then
        # Use jq for better formatting if available
        echo -e "\n${CYAN}${BOLD}=== API ENDPOINTS ===${NC}"

        # Extract and display paths
        while read -r path; do
            # Get HTTP methods for this path
            while read -r method; do
                # Get summary if available
                summary=$(jq -r --arg path "$path" --arg method "$method" '.paths[$path][$method].summary // "No description"' /tmp/openapi_spec.json)
                echo -e "${GREEN}$(echo $method | tr 'a-z' 'A-Z')${NC} ${path} - ${BLUE}${summary}${NC}"
            done < <(jq -r --arg path "$path" '.paths[$path] | keys[]' /tmp/openapi_spec.json)
        done < <(jq -r '.paths | keys[]' /tmp/openapi_spec.json | sort)
    else
        # Basic info without jq
        echo "✅ API service is running on port $api_port"
        echo "📝 API documentation available at http://localhost:${api_port}/docs"
    fi

    # Clean up temporary file
    rm -f /tmp/openapi_spec.json
}

# Display API endpoints
display_api_endpoints

# Display WebSocket API Gateway details if running API Gateway
display_websocket_api_gateway() {
    local api_port=9000
    local endpoint_url="http://localhost:${api_port}/openapi.json"

    echo "📡 Retrieving WebSocket API Gateway details..."

    # Check if this is the API Gateway by looking for WebSocket endpoints in the OpenAPI spec
    if curl -s "${endpoint_url}" -o /tmp/openapi_spec.json 2>/dev/null; then
        # Check if API Gateway running by looking for WebSocket endpoints
        if jq -e '.info.title | contains("Gateway")' /tmp/openapi_spec.json > /dev/null 2>&1 ||
           jq -e '.paths | has("/ws")' /tmp/openapi_spec.json > /dev/null 2>&1; then

            # API Gateway detected, display WebSocket endpoints
            echo -e "\n${CYAN}${BOLD}=== WEBSOCKET API ENDPOINTS ===${NC}"

            # Display default WebSocket endpoints
            echo -e "${MAGENTA}${BOLD}/ws${NC}"
            echo -e "  ${BLUE}Description:${NC} Default WebSocket endpoint (generates new session ID)"
            echo -e "  ${YELLOW}WebSocket URL:${NC} ws://localhost:${api_port}/ws"
            echo -e "  ${GREEN}Notes:${NC} Use this endpoint to create a new WebSocket connection without a session ID"
            echo ""

            echo -e "${MAGENTA}${BOLD}/ws/{session_id}${NC}"
            echo -e "  ${BLUE}Description:${NC} WebSocket endpoint with specific session ID"
            echo -e "  ${YELLOW}WebSocket URL:${NC} ws://localhost:${api_port}/ws/{session_id}"
            echo -e "  ${YELLOW}Example Usage:${NC} ws://localhost:${api_port}/ws/your-session-id"
            echo -e "  ${GREEN}Notes:${NC} Use this endpoint when you have an existing session ID"
            echo ""

            # Check for questionnaire WebSocket endpoint
            if jq -e '.paths | has("/api/v1/questionnaire/ws")' /tmp/openapi_spec.json > /dev/null 2>&1; then
                echo -e "${MAGENTA}${BOLD}/api/v1/questionnaire/ws${NC}"
                echo -e "  ${BLUE}Description:${NC} WebSocket endpoint for questionnaire interaction"
                echo -e "  ${YELLOW}WebSocket URL:${NC} ws://localhost:${api_port}/api/v1/questionnaire/ws"
                echo -e "  ${GREEN}Notes:${NC} Used for real-time questionnaire interactions"
                echo ""
            fi

            # For more details message
            echo -e "${YELLOW}For more detailed WebSocket information, run:${NC}"
            echo -e "  ./view-websocket-endpoints.sh"
            echo ""
        fi

        # Clean up temporary file
        rm -f /tmp/openapi_spec.json
    fi
}

# Display WebSocket API Gateway details if running API Gateway
display_websocket_api_gateway

echo -e "\n✅ API service is running on port 9000"
echo "📝 Interactive API documentation: http://localhost:9000/docs"
echo "📊 ReDoc API documentation: http://localhost:9000/redoc"
echo "🛑 To stop the server, press Ctrl+C"

# Wait for the API service process
wait $API_PID
