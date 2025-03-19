#!/bin/bash

# ===========================================
# View API Endpoints Script
# ===========================================
# This script fetches and displays API endpoints from a FastAPI service
# with detailed information about request and response structures

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
    echo -e "${CYAN}${BOLD}API Endpoints Viewer${NC}"
    echo "This utility displays API endpoints from a FastAPI service"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --port PORT     Specify API port (default: 9000)"
    echo "  -h, --host HOST     Specify API host (default: localhost)"
    echo "  -d, --detailed      Show detailed endpoint information"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  View endpoints on localhost:9000"
    echo "  $0 -p 8000          View endpoints on localhost:8000"
    echo "  $0 -d               View detailed endpoint information"
    echo ""
}

# Function to fetch and display API endpoints
display_api_endpoints() {
    local host=$1
    local port=$2
    local detailed=$3
    local endpoint_url="http://${host}:${port}/openapi.json"

    print_status "$BLUE" "ℹ" "Fetching API endpoints from ${endpoint_url}..."

    # Try to fetch the OpenAPI specification
    if ! curl -s "${endpoint_url}" -o /tmp/openapi_spec.json 2>/dev/null; then
        print_status "$RED" "✗" "Failed to connect to API at ${host}:${port}"
        print_status "$YELLOW" "!" "Make sure the API service is running and accessible"
        return 1
    fi

    # Verify it's a valid JSON file
    if ! jq empty /tmp/openapi_spec.json 2>/dev/null; then
        print_status "$RED" "✗" "Invalid OpenAPI specification received"
        return 1
    fi

    # Extract API info
    local api_title=$(jq -r '.info.title // "API"' /tmp/openapi_spec.json)
    local api_version=$(jq -r '.info.version // "unknown"' /tmp/openapi_spec.json)
    local api_description=$(jq -r '.info.description // "No description available"' /tmp/openapi_spec.json)

    # Display API info
    echo -e "\n${CYAN}${BOLD}${api_title} (v${api_version})${NC}"
    echo -e "${BLUE}${api_description}${NC}"
    echo -e "${YELLOW}Server: ${NC}http://${host}:${port}"
    echo -e "${YELLOW}Documentation: ${NC}http://${host}:${port}/docs"
    echo ""

    # Display endpoints
    echo -e "${CYAN}${BOLD}Available Endpoints:${NC}"
    echo ""

    # Get all paths
    jq -r '.paths | keys[]' /tmp/openapi_spec.json | sort | while read -r path; do
        echo -e "${MAGENTA}${BOLD}${path}${NC}"

        # Get methods for this path
        jq -r --arg path "$path" '.paths[$path] | keys[]' /tmp/openapi_spec.json | while read -r method; do
            # Get summary and description
            local summary=$(jq -r --arg path "$path" --arg method "$method" '.paths[$path][$method].summary // "No summary"' /tmp/openapi_spec.json)
            local description=$(jq -r --arg path "$path" --arg method "$method" '.paths[$path][$method].description // ""' /tmp/openapi_spec.json)

            # Display method and summary
            echo -e "  ${GREEN}${method^^}${NC} - ${BLUE}${summary}${NC}"

            # Display description if available and not empty
            if [ -n "$description" ] && [ "$description" != "null" ]; then
                echo -e "    ${description}"
            fi

            # If detailed mode is enabled, show request and response info
            if [ "$detailed" = true ]; then
                # Display request body schema if available
                if jq -e --arg path "$path" --arg method "$method" '.paths[$path][$method].requestBody' /tmp/openapi_spec.json > /dev/null 2>&1; then
                    echo -e "    ${YELLOW}Request Body:${NC}"

                    # Check if the endpoint has requestBody with JSON content
                    if jq -e --arg path "$path" --arg method "$method" '.paths[$path][$method].requestBody.content["application/json"]' /tmp/openapi_spec.json > /dev/null 2>&1; then
                        # Get required fields
                        local required_fields=$(jq -r --arg path "$path" --arg method "$method" '.paths[$path][$method].requestBody.content["application/json"].schema.required // []' /tmp/openapi_spec.json)

                        # Display properties
                        jq -r --arg path "$path" --arg method "$method" '.paths[$path][$method].requestBody.content["application/json"].schema.properties | keys[] as $k | "\($k): \(.[$k] | .type) \(.[$k] | .description // "")"' /tmp/openapi_spec.json 2>/dev/null | while read -r line; do
                            local field_name=$(echo "$line" | cut -d':' -f1)
                            local is_required=$(echo "$required_fields" | grep -q "$field_name" && echo "true" || echo "false")

                            if [ "$is_required" = "true" ]; then
                                echo -e "      ${RED}*${NC} ${line}"
                            else
                                echo -e "        ${line}"
                            fi
                        done
                    else
                        echo -e "        (Non-JSON request body)"
                    fi
                fi

                # Display response schema if available
                echo -e "    ${YELLOW}Responses:${NC}"
                jq -r --arg path "$path" --arg method "$method" '.paths[$path][$method].responses | keys[]' /tmp/openapi_spec.json | while read -r status_code; do
                    local response_description=$(jq -r --arg path "$path" --arg method "$method" --arg status "$status_code" '.paths[$path][$method].responses[$status].description // "No description"' /tmp/openapi_spec.json)

                    echo -e "      ${GREEN}${status_code}${NC}: ${response_description}"

                    # Check if the response has JSON content
                    if jq -e --arg path "$path" --arg method "$method" --arg status "$status_code" '.paths[$path][$method].responses[$status].content["application/json"]' /tmp/openapi_spec.json > /dev/null 2>&1; then
                        # Display properties
                        jq -r --arg path "$path" --arg method "$method" --arg status "$status_code" '.paths[$path][$method].responses[$status].content["application/json"].schema.properties // {}' /tmp/openapi_spec.json | grep -v "^{" | grep -v "^}" | sed 's/^/        /'
                    fi
                done
            fi

            echo ""
        done
    done

    # Clean up temporary file
    rm -f /tmp/openapi_spec.json
}

# Main function
main() {
    # Default values
    local host="localhost"
    local port=9000
    local detailed=false

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
            -d|--detailed)
                detailed=true
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

    # Display API endpoints
    display_api_endpoints "$host" "$port" "$detailed"
}

# Call main function with all arguments
main "$@"
