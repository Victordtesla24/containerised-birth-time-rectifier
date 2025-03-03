#!/bin/bash

# Exit on any error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run GPU verification
check_gpu() {
    echo -e "\n${YELLOW}Running GPU verification...${NC}"
    if ! python3 scripts/verify_gpu.py; then
        echo -e "${RED}GPU verification failed${NC}"
        echo "Note: The system will continue with CPU mode if GPU is not available"
    fi
}

# Function to wait for a service
wait_for_service() {
    local service_name=$1
    local url=$2
    local is_redis=${3:-false}
    local max_attempts=60  # 60 seconds timeout
    local attempt=1

    echo -e "\n${YELLOW}Waiting for $service_name to be ready...${NC}"
    while [ $attempt -le $max_attempts ]; do
        echo -n "."
        if [ "$is_redis" = true ]; then
            if redis-cli ping > /dev/null 2>&1; then
                echo -e "\n${GREEN}$service_name is ready${NC}"
                echo "Response from $service_name:"
                redis-cli ping
                return 0
            fi
        else
            if curl -s "$url" > /dev/null 2>&1; then
                echo -e "\n${GREEN}$service_name is ready${NC}"
                echo "Response from $service_name:"
                curl -s "$url" | jq '.' || echo "Raw response: $(curl -s "$url")"
                return 0
            fi
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "\n${RED}$service_name did not become ready in time${NC}"
    if [ "$is_redis" = true ]; then
        echo "Last Redis connection attempt:"
        redis-cli ping || echo "Failed to connect to Redis"
    else
        echo "Last response from $service_name:"
        curl -v "$url" || echo "Failed to connect to $url"
    fi
    return 1
}

# Function to run integration tests
run_integration_tests() {
    echo -e "\n${YELLOW}Running integration tests...${NC}"
    
    # Install test dependencies if needed
    pip install pytest requests redis

    # Run the tests with increased verbosity
    if pytest tests/integration -v --log-cli-level=INFO; then
        echo -e "${GREEN}Integration tests passed${NC}"
        return 0
    else
        echo -e "${RED}Integration tests failed${NC}"
        return 1
    fi
}

# Function to check container logs
check_container_logs() {
    echo -e "\n${YELLOW}Checking container logs...${NC}"
    docker compose logs
}

# Main function
main() {
    local mode=${1:-"dev"}
    
    # Check requirements
    if ! command_exists docker; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    if ! command_exists python3; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi

    if ! command_exists jq; then
        echo -e "${YELLOW}Warning: jq is not installed. JSON output will not be formatted.${NC}"
    fi

    # Run GPU verification
    check_gpu

    # Start containers in the background
    echo -e "\n${YELLOW}Starting containers in $mode mode...${NC}"
    if [ "$mode" = "dev" ]; then
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    else
        docker compose up -d
    fi

    # Wait for services to be ready
    wait_for_service "Frontend" "http://localhost:3000" || exit 1
    wait_for_service "AI Service" "http://localhost:8000/health" || {
        check_container_logs
        exit 1
    }
    wait_for_service "Redis" "" true || {
        check_container_logs
        exit 1
    }

    # Run integration tests
    if ! run_integration_tests; then
        echo -e "${RED}Tests failed. Checking container logs...${NC}"
        check_container_logs
        echo -e "${RED}Stopping containers...${NC}"
        docker compose down
        exit 1
    fi

    # Show container status
    echo -e "\n${YELLOW}Container Status:${NC}"
    docker compose ps

    # Show logs if any container is not running
    if docker compose ps | grep -q "Exit"; then
        echo -e "\n${RED}Some containers are not running. Showing logs:${NC}"
        check_container_logs
        exit 1
    fi

    echo -e "\n${GREEN}All tests passed successfully!${NC}"
}

# Parse command line arguments
case "$1" in
    "dev"|"prod")
        main "$1"
        ;;
    *)
        echo "Usage: $0 [dev|prod]"
        echo "  dev  - Test development environment"
        echo "  prod - Test production environment (default)"
        exit 1
        ;;
esac 