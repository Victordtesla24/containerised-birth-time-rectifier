#!/bin/bash

# ===========================================
# View WebSocket API Gateway Details Script
# ===========================================
# This script displays WebSocket API Gateway endpoints and configuration details

# ANSI color codes
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
MAGENTA="\033[0;35m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# Print colored status messages
print_status() {
    local color=$1
    local symbol=$2
    local message=$3
    echo -e "${color}${symbol} ${message}${NC}"
}

# Display usage information
show_usage() {
    echo -e "${CYAN}${BOLD}WebSocket API Gateway Viewer${NC}"
    echo "This utility displays WebSocket endpoints and configuration from the API Gateway"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --port PORT     Specify API Gateway port (default: 9000)"
    echo "  -h, --host HOST     Specify API Gateway host (default: localhost)"
    echo "  -f, --fallback      Show fallback information even if API Gateway is not running"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  View WebSocket details on localhost:9000"
    echo "  $0 -p 8000          View WebSocket details on localhost:8000"
    echo "  $0 -f               Show fallback information if API Gateway is not running"
    echo ""
}

# Function to display fallback WebSocket information
display_fallback_websocket_info() {
    local host=$1
    local port=$2

    print_status "$YELLOW" "!" "Using fallback information since the API Gateway is not accessible"
    echo ""

    # Display basic API Gateway info
    echo -e "${CYAN}${BOLD}Birth Time Rectifier API Gateway (Fallback Info)${NC}"
    echo -e "${BLUE}API Gateway for the Birth Time Rectifier application${NC}"
    echo -e "${YELLOW}Server: ${NC}http://${host}:${port}"
    echo -e "${YELLOW}Documentation: ${NC}http://${host}:${port}/docs"
    echo ""

    # Display WebSocket endpoints
    echo -e "${CYAN}${BOLD}WebSocket Endpoints:${NC}"
    echo ""

    # Default WebSocket endpoints for API Gateway
    echo -e "${MAGENTA}${BOLD}/ws${NC}"
    echo -e "  ${BLUE}Description:${NC} Default WebSocket endpoint (generates new session ID)"
    echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}/ws"
    echo -e "  ${GREEN}Notes:${NC} Use this endpoint to create a new WebSocket connection without a session ID"
    echo ""

    echo -e "${MAGENTA}${BOLD}/ws/{session_id}${NC}"
    echo -e "  ${BLUE}Description:${NC} WebSocket endpoint with specific session ID"
    echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}/ws/{session_id}"
    echo -e "  ${YELLOW}Example Usage:${NC} ws://${host}:${port}/ws/your-session-id"
    echo -e "  ${GREEN}Notes:${NC} Use this endpoint when you have an existing session ID"
    echo ""

    echo -e "${MAGENTA}${BOLD}/api/v1/questionnaire/ws${NC}"
    echo -e "  ${BLUE}Description:${NC} WebSocket endpoint for questionnaire interaction"
    echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}/api/v1/questionnaire/ws"
    echo -e "  ${GREEN}Notes:${NC} Used for real-time questionnaire interactions"
    echo ""

    # Display WebSocket configuration information
    echo -e "${CYAN}${BOLD}WebSocket Configuration (Default):${NC}"
    echo -e "  ${YELLOW}Ping Interval:${NC} 20 seconds"
    echo -e "  ${YELLOW}Ping Timeout:${NC} 20 seconds"
    echo -e "  ${YELLOW}Max Message Size:${NC} 16777216 bytes (16MB)"
    echo -e "  ${YELLOW}Heartbeat Interval:${NC} 30 seconds"
    echo -e "  ${YELLOW}Connection Retries:${NC} 3 attempts"
    echo -e "  ${YELLOW}Retry Delay:${NC} 2 seconds"
    echo ""

    # Display connection examples
    echo -e "${CYAN}${BOLD}WebSocket Connection Examples:${NC}"
    echo -e "  ${BLUE}Browser JavaScript:${NC}"
    echo -e "    ${GREEN}// Connect to WebSocket endpoint${NC}"
    echo -e "    ${YELLOW}const ws = new WebSocket('ws://${host}:${port}/ws');${NC}"
    echo -e ""
    echo -e "    ${GREEN}// Listen for messages${NC}"
    echo -e "    ${YELLOW}ws.onmessage = (event) => {${NC}"
    echo -e "    ${YELLOW}  const data = JSON.parse(event.data);${NC}"
    echo -e "    ${YELLOW}  console.log('Received:', data);${NC}"
    echo -e "    ${YELLOW}};${NC}"
    echo -e ""
    echo -e "    ${GREEN}// Send a message${NC}"
    echo -e "    ${YELLOW}ws.send(JSON.stringify({ type: 'event', data: { key: 'value' } }));${NC}"
    echo -e ""
    echo -e "  ${BLUE}Python with websockets:${NC}"
    echo -e "    ${GREEN}# Connect to WebSocket endpoint${NC}"
    echo -e "    ${YELLOW}import asyncio${NC}"
    echo -e "    ${YELLOW}import websockets${NC}"
    echo -e "    ${YELLOW}import json${NC}"
    echo -e ""
    echo -e "    ${YELLOW}async def connect():${NC}"
    echo -e "    ${YELLOW}    uri = \"ws://${host}:${port}/ws\"${NC}"
    echo -e "    ${YELLOW}    async with websockets.connect(uri) as websocket:${NC}"
    echo -e "    ${YELLOW}        # Send a message${NC}"
    echo -e "    ${YELLOW}        await websocket.send(json.dumps({\"type\": \"event\", \"data\": {\"key\": \"value\"}}))${NC}"
    echo -e ""
    echo -e "    ${YELLOW}        # Receive messages${NC}"
    echo -e "    ${YELLOW}        while True:${NC}"
    echo -e "    ${YELLOW}            response = await websocket.recv()${NC}"
    echo -e "    ${YELLOW}            data = json.loads(response)${NC}"
    echo -e "    ${YELLOW}            print(f\"Received: {data}\")${NC}"
    echo -e ""

    print_status "$YELLOW" "!" "Note: This is fallback information. For actual details, please start the API Gateway."
}

# Function to display WebSocket endpoints and configuration
display_websocket_details() {
    local host=$1
    local port=$2
    local use_fallback=$3
    local api_url="http://${host}:${port}"
    local endpoint_url="${api_url}/openapi.json"

    print_status "$BLUE" "ℹ" "Fetching API Gateway details from ${endpoint_url}..."

    # Try to fetch the OpenAPI specification to check if API Gateway is running
    if ! curl -s "${endpoint_url}" -o /tmp/openapi_spec.json 2>/dev/null; then
        print_status "$RED" "✗" "Failed to connect to API Gateway at ${host}:${port}"
        print_status "$YELLOW" "!" "Make sure the API Gateway service is running and accessible"

        # If fallback option is enabled, show fallback information
        if [ "$use_fallback" = true ]; then
            display_fallback_websocket_info "$host" "$port"
        else
            print_status "$BLUE" "ℹ" "Run with -f or --fallback option to see fallback information"
        fi
        return 1
    fi

    # Verify it's a valid JSON file
    if ! jq empty /tmp/openapi_spec.json 2>/dev/null; then
        print_status "$RED" "✗" "Invalid OpenAPI specification received"

        # If fallback option is enabled, show fallback information
        if [ "$use_fallback" = true ]; then
            display_fallback_websocket_info "$host" "$port"
        fi
        return 1
    fi

    # Check if this is actually an API Gateway (it has WebSocket endpoints or Gateway in the title)
    local is_api_gateway=false
    if jq -e '.paths | has("/ws")' /tmp/openapi_spec.json > /dev/null 2>&1 ||
       jq -e '.info.title | contains("Gateway")' /tmp/openapi_spec.json > /dev/null 2>&1; then
        is_api_gateway=true
    else
        print_status "$YELLOW" "!" "This appears to be a regular API service, not the API Gateway"
        print_status "$YELLOW" "!" "WebSocket endpoints are only available in the API Gateway"

        # If fallback option is enabled, show fallback information
        if [ "$use_fallback" = true ]; then
            display_fallback_websocket_info "$host" "$port"
        fi
        return 1
    fi

    # Extract API info
    local api_title=$(jq -r '.info.title // "API Gateway"' /tmp/openapi_spec.json)
    local api_version=$(jq -r '.info.version // "unknown"' /tmp/openapi_spec.json)
    local api_description=$(jq -r '.info.description // "No description available"' /tmp/openapi_spec.json)

    # Display API Gateway info
    echo -e "\n${CYAN}${BOLD}${api_title} (v${api_version})${NC}"
    echo -e "${BLUE}${api_description}${NC}"
    echo -e "${YELLOW}Server: ${NC}http://${host}:${port}"
    echo -e "${YELLOW}Documentation: ${NC}http://${host}:${port}/docs"
    echo ""

    # Display WebSocket endpoints
    echo -e "${CYAN}${BOLD}WebSocket Endpoints:${NC}"
    echo ""

    # Look for WebSocket endpoints in OpenAPI spec (they are marked as GET operations)
    local ws_paths=()

    # Find explicitly defined WebSocket paths
    if jq -e '.paths | has("/ws")' /tmp/openapi_spec.json > /dev/null 2>&1; then
        ws_paths+=("/ws")
    fi

    if jq -e '.paths | has("/ws/{session_id}")' /tmp/openapi_spec.json > /dev/null 2>&1; then
        ws_paths+=("/ws/{session_id}")
    fi

    # Also search for any paths that have "websocket" in their description
    jq -r '.paths | keys[]' /tmp/openapi_spec.json | while read -r path; do
        local descriptions=$(jq -r --arg path "$path" '.paths[$path] | .[] | .description // ""' /tmp/openapi_spec.json)
        if echo "$descriptions" | grep -i "websocket" > /dev/null; then
            ws_paths+=("$path")
        fi
    done

    # If we found WebSocket paths in the OpenAPI spec
    if [ ${#ws_paths[@]} -gt 0 ]; then
        for path in "${ws_paths[@]}"; do
            echo -e "${MAGENTA}${BOLD}${path}${NC}"

            # Get the method description
            local description=$(jq -r --arg path "$path" '.paths[$path].get.description // "No description"' /tmp/openapi_spec.json)
            echo -e "  ${BLUE}Description:${NC} ${description}"

            # Display WebSocket URL
            echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}${path}"

            # If path includes session_id param, show example usage
            if [[ "$path" == *"{session_id}"* ]]; then
                echo -e "  ${YELLOW}Example Usage:${NC} ws://${host}:${port}/ws/your-session-id"
            fi

            echo ""
        done
    else
        # Default WebSocket endpoints (from the API Gateway code)
        echo -e "${MAGENTA}${BOLD}/ws${NC}"
        echo -e "  ${BLUE}Description:${NC} Default WebSocket endpoint (generates new session ID)"
        echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}/ws"
        echo -e "  ${GREEN}Notes:${NC} Use this endpoint to create a new WebSocket connection without a session ID"
        echo ""
        echo -e "${MAGENTA}${BOLD}/ws/{session_id}${NC}"
        echo -e "  ${BLUE}Description:${NC} WebSocket endpoint with specific session ID"
        echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}/ws/{session_id}"
        echo -e "  ${YELLOW}Example Usage:${NC} ws://${host}:${port}/ws/your-session-id"
        echo -e "  ${GREEN}Notes:${NC} Use this endpoint when you have an existing session ID"
        echo ""
        echo -e "${MAGENTA}${BOLD}/api/v1/questionnaire/ws${NC}"
        echo -e "  ${BLUE}Description:${NC} WebSocket endpoint for questionnaire interaction"
        echo -e "  ${YELLOW}WebSocket URL:${NC} ws://${host}:${port}/api/v1/questionnaire/ws"
        echo -e "  ${GREEN}Notes:${NC} Used for real-time questionnaire interactions"
        echo ""
    fi

    # Display WebSocket configuration information
    echo -e "${CYAN}${BOLD}WebSocket Configuration:${NC}"
    echo -e "  ${YELLOW}Ping Interval:${NC} ${WS_PING_INTERVAL:-20} seconds"
    echo -e "  ${YELLOW}Ping Timeout:${NC} ${WS_PING_TIMEOUT:-20} seconds"
    echo -e "  ${YELLOW}Max Message Size:${NC} ${WS_MAX_SIZE:-16777216} bytes (16MB)"
    echo -e "  ${YELLOW}Heartbeat Interval:${NC} ${WS_HEARTBEAT_INTERVAL:-30} seconds"
    echo -e "  ${YELLOW}Connection Retries:${NC} ${WS_RETRY_ATTEMPTS:-3} attempts"
    echo -e "  ${YELLOW}Retry Delay:${NC} ${WS_RETRY_DELAY:-2} seconds"
    echo ""

    # Display connection examples
    echo -e "${CYAN}${BOLD}WebSocket Connection Examples:${NC}"
    echo -e "  ${BLUE}Browser JavaScript:${NC}"
    echo -e "    ${GREEN}// Connect to WebSocket endpoint${NC}"
    echo -e "    ${YELLOW}const ws = new WebSocket('ws://${host}:${port}/ws');${NC}"
    echo -e ""
    echo -e "    ${GREEN}// Listen for messages${NC}"
    echo -e "    ${YELLOW}ws.onmessage = (event) => {${NC}"
    echo -e "    ${YELLOW}  const data = JSON.parse(event.data);${NC}"
    echo -e "    ${YELLOW}  console.log('Received:', data);${NC}"
    echo -e "    ${YELLOW}};${NC}"
    echo -e ""
    echo -e "    ${GREEN}// Send a message${NC}"
    echo -e "    ${YELLOW}ws.send(JSON.stringify({ type: 'event', data: { key: 'value' } }));${NC}"
    echo -e ""
    echo -e "  ${BLUE}Python with websockets:${NC}"
    echo -e "    ${GREEN}# Connect to WebSocket endpoint${NC}"
    echo -e "    ${YELLOW}import asyncio${NC}"
    echo -e "    ${YELLOW}import websockets${NC}"
    echo -e "    ${YELLOW}import json${NC}"
    echo -e ""
    echo -e "    ${YELLOW}async def connect():${NC}"
    echo -e "    ${YELLOW}    uri = \"ws://${host}:${port}/ws\"${NC}"
    echo -e "    ${YELLOW}    async with websockets.connect(uri) as websocket:${NC}"
    echo -e "    ${YELLOW}        # Send a message${NC}"
    echo -e "    ${YELLOW}        await websocket.send(json.dumps({\"type\": \"event\", \"data\": {\"key\": \"value\"}}))${NC}"
    echo -e ""
    echo -e "    ${YELLOW}        # Receive messages${NC}"
    echo -e "    ${YELLOW}        while True:${NC}"
    echo -e "    ${YELLOW}            response = await websocket.recv()${NC}"
    echo -e "    ${YELLOW}            data = json.loads(response)${NC}"
    echo -e "    ${YELLOW}            print(f\"Received: {data}\")${NC}"
    echo -e ""

    # Clean up temporary file
    rm -f /tmp/openapi_spec.json
}

# Main function
main() {
    # Default values
    local host="localhost"
    local port=9000
    local use_fallback=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -p|--port)
                port="$2"
                shift 2
                ;;
            -h|--host)
                host="$2"
                shift 2
                ;;
            -f|--fallback)
                use_fallback=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Check if jq is installed
    if ! command -v jq >/dev/null 2>&1; then
        print_status "$RED" "✗" "jq is required but not installed"
        print_status "$YELLOW" "!" "Please install jq using your package manager:"
        echo "  - macOS: brew install jq"
        echo "  - Ubuntu/Debian: sudo apt install jq"
        echo "  - CentOS/RHEL: sudo yum install jq"
        exit 1
    fi

    # Extract WebSocket environment variables
    # Use default values if not set
    export WS_PING_INTERVAL=$(grep -o 'WS_PING_INTERVAL = [0-9]*' api_gateway/websocket_proxy.py 2>/dev/null | awk '{print $3}' || echo "20")
    export WS_PING_TIMEOUT=$(grep -o 'WS_PING_TIMEOUT = [0-9]*' api_gateway/websocket_proxy.py 2>/dev/null | awk '{print $3}' || echo "20")
    export WS_MAX_SIZE=$(grep -o 'WS_MAX_SIZE = [0-9]*' api_gateway/websocket_proxy.py 2>/dev/null | awk '{print $3}' || echo "16777216")
    export WS_HEARTBEAT_INTERVAL=$(grep -o 'WS_HEARTBEAT_INTERVAL = [0-9]*' api_gateway/websocket_proxy.py 2>/dev/null | awk '{print $3}' || echo "30")
    export WS_RETRY_ATTEMPTS=$(grep -o 'WS_RETRY_ATTEMPTS = [0-9]*' api_gateway/websocket_proxy.py 2>/dev/null | awk '{print $3}' || echo "3")
    export WS_RETRY_DELAY=$(grep -o 'WS_RETRY_DELAY = [0-9]*' api_gateway/websocket_proxy.py 2>/dev/null | awk '{print $3}' || echo "2")

    # Display WebSocket details
    display_websocket_details "$host" "$port" "$use_fallback"
}

# Call main function with all arguments
main "$@"
