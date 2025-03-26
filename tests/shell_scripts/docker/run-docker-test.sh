#!/bin/bash
#
# Docker Test Orchestration Script
# Purpose: Run tests in Docker containers with user-friendly interface
# Author: AI-Assisted Development Team
# Date: $(date +%Y-%m-%d)
#

# Set strict error handling
set -eo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Source helper scripts
source "${SCRIPT_DIR}/helpers/ui_helpers.sh"
source "${SCRIPT_DIR}/helpers/docker_helpers.sh"

# Configuration
CONFIG_FILE="${PROJECT_ROOT}/.service_config.json"
TEST_LOG_FILE="${SCRIPT_DIR}/test_run.log"
CONTAINER_PREFIX=${CONTAINER_PREFIX:-"birth-rectifier"}
TEST_FILTER=""
TEST_OPTIONS=""
REBUILD_CONTAINERS=false
SHOW_LOGS=false
VERBOSE=false
CLEAN_UP=false
TEST_ENV="test"

# Check if required tools are installed
function check_requirements() {
    local requirements_met=true

    start_spinner "Checking required tools"

    # Check if Docker is installed
    if ! command -v docker >/dev/null 2>&1; then
        requirements_met=false
        stop_spinner "error" "Docker not found. Please install Docker."
    fi

    # Check if docker-compose is installed
    if ! command -v docker-compose >/dev/null 2>&1; then
        requirements_met=false
        stop_spinner "error" "docker-compose not found. Please install docker-compose."
    fi

    # Check if JQ is installed (for parsing JSON config)
    if ! command -v jq >/dev/null 2>&1; then
        print_warning "jq not found. Some configuration features may be limited."
    fi

    if [ "$requirements_met" = false ]; then
        exit 1
    fi

    stop_spinner "success" "All required tools found"
}

# Print usage information
function print_usage() {
    echo -e "\n${BOLD}Birth Time Rectifier - Docker Test Runner${RESET}"
    echo -e "${BOLD}Usage:${RESET} $0 [options] [test_path]"
    echo
    echo -e "${BOLD}Options:${RESET}"
    echo "  -r, --rebuild            Rebuild containers before testing"
    echo "  -e, --env ENV            Set test environment (test, dev, prod)"
    echo "  -f, --filter PATTERN     Only run tests matching pattern"
    echo "  -o, --options \"OPTS\"     Pass additional options to pytest"
    echo "  -l, --logs               Show container logs during tests"
    echo "  -v, --verbose            Enable verbose output"
    echo "  -c, --clean              Clean up containers after tests"
    echo "  -h, --help               Show this help message"
    echo
    echo -e "${BOLD}Examples:${RESET}"
    echo "  $0 tests/integration/birth_time_rectification/test_integration_birth_time_01_session_init.py"
    echo "  $0 --rebuild --filter \"session_init\" --clean"
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--rebuild)
            REBUILD_CONTAINERS=true
      shift
      ;;
        -e|--env)
            TEST_ENV="$2"
            shift 2
      ;;
        -f|--filter)
            TEST_FILTER="$2"
            shift 2
      ;;
        -o|--options)
            TEST_OPTIONS="$2"
      shift 2
      ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
      shift
      ;;
        -c|--clean)
            CLEAN_UP=true
      shift
      ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        -*)
      echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
        *)
            TEST_PATH="$1"
      shift
      ;;
  esac
done

# Initialize log file
> "$TEST_LOG_FILE"

# Display welcome banner and load configuration
function initialize() {
    clear
    print_header "Birth Time Rectifier - Docker Test Suite"

    # Load config from JSON file if it exists
    if [[ -f "$CONFIG_FILE" ]]; then
        if command -v jq >/dev/null 2>&1; then
            # Use jq to parse the JSON config
            CONTAINER_PREFIX=$(jq -r '.container_prefix // "birth-rectifier"' "$CONFIG_FILE")
            VERBOSE=$(jq -r '.verbose // false' "$CONFIG_FILE")
        else
            # Default values if jq is not available
            CONTAINER_PREFIX="birth-rectifier"
        fi
    fi

    echo -e "${BLUE}Test Environment: ${BOLD}${TEST_ENV}${RESET}"
    echo -e "${BLUE}Container Prefix: ${BOLD}${CONTAINER_PREFIX}${RESET}"

    if [[ -n "$TEST_PATH" ]]; then
        echo -e "${BLUE}Test Path: ${BOLD}${TEST_PATH}${RESET}"
    fi

    if [[ -n "$TEST_FILTER" ]]; then
        echo -e "${BLUE}Test Filter: ${BOLD}${TEST_FILTER}${RESET}"
    fi

    if $REBUILD_CONTAINERS; then
        echo -e "${YELLOW}Rebuilding containers: ${BOLD}Enabled${RESET}"
    fi

    if $SHOW_LOGS; then
        echo -e "${YELLOW}Show container logs: ${BOLD}Enabled${RESET}"
    fi

    if $VERBOSE; then
        echo -e "${YELLOW}Verbose output: ${BOLD}Enabled${RESET}"
    fi

    if $CLEAN_UP; then
        echo -e "${YELLOW}Clean up after tests: ${BOLD}Enabled${RESET}"
    fi

    echo -e "Log file: ${TEST_LOG_FILE}\n"
}

# Prepare containers for testing
function prepare_containers() {
    print_section "Preparing Test Environment"

    # Check if docker-compose file exists
    if [[ ! -f "${PROJECT_ROOT}/docker-compose.test.yml" ]]; then
        print_error "docker-compose.test.yml not found in project root"
        return 1
    fi

    # Set compose file and project name
    export COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.test.yml"
    export COMPOSE_PROJECT_NAME="${CONTAINER_PREFIX}-test"

    # Set environment variables for docker-compose
    export CONTAINER_PREFIX="${CONTAINER_PREFIX}"
    export TEST_ENV="${TEST_ENV}"

    # Check if need to rebuild containers
    if $REBUILD_CONTAINERS; then
        start_spinner "Rebuilding test containers"

        if docker-compose build --no-cache >>"$TEST_LOG_FILE" 2>&1; then
            stop_spinner "success" "Test containers rebuilt successfully"
        else
            stop_spinner "error" "Failed to rebuild test containers"
            echo -e "\n${RED}Build log (last 10 lines):${RESET}"
            tail -n 10 "$TEST_LOG_FILE"
            return 1
        fi
    fi

    # Start containers
    start_spinner "Starting test containers"

    if docker-compose up -d --remove-orphans >>"$TEST_LOG_FILE" 2>&1; then
        stop_spinner "success" "Test containers started successfully"
    else
        stop_spinner "error" "Failed to start test containers"
        echo -e "\n${RED}Startup log (last 10 lines):${RESET}"
        tail -n 10 "$TEST_LOG_FILE"
        return 1
    fi

    # Wait for containers to be ready
    start_spinner "Waiting for containers to be ready"

    # Wait for the ai-service to be healthy
    local max_attempts=30
    local attempt=0
    local ready=false

    while (( attempt < max_attempts )); do
        if docker-compose ps | grep ai-service | grep "(healthy)" >/dev/null 2>&1; then
            ready=true
            break
        fi
        sleep 2
        ((attempt++))
    done

    if $ready; then
        stop_spinner "success" "Test environment is ready"
    else
        stop_spinner "error" "Timed out waiting for containers to be ready"

        # Show container status
        echo -e "\n${YELLOW}Container status:${RESET}"
        docker-compose ps

        # Show ai-service logs if verbose
        if $VERBOSE; then
            echo -e "\n${YELLOW}AI Service logs:${RESET}"
            docker-compose logs ai-service | tail -n 20
        fi

    return 1
    fi
}

# Run the tests
function run_tests() {
    print_section "Running Tests"

    # Build the test command
    local test_cmd="pytest"

    # Add verbosity flag
    if $VERBOSE; then
        test_cmd+=" -vvs"
    else
        test_cmd+=" -xvs"
    fi

    # Add filter if specified
    if [[ -n "$TEST_FILTER" ]]; then
        test_cmd+=" -k \"$TEST_FILTER\""
    fi

    # Add additional options if specified
    if [[ -n "$TEST_OPTIONS" ]]; then
        test_cmd+=" $TEST_OPTIONS"
    fi

    # Add test path if specified
    if [[ -n "$TEST_PATH" ]]; then
        test_cmd+=" $TEST_PATH"
    else
        # Default to running all birth time rectification tests
        test_cmd+=" tests/integration/birth_time_rectification/"
    fi

    echo -e "${BLUE}Running test command:${RESET} $test_cmd"
    echo

    # Export required variables for test container
    export API_BASE_URL="http://ai-service:8000"
    export WS_BASE_URL="ws://ai-service:8000/ws"

    # Run the tests in the test-runner container
    local start_time=$(date +%s)

    if docker-compose run --rm test-runner bash -c "$test_cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        print_success "Tests completed successfully in ${duration}s!"
    return 0
    else
        local exit_code=$?
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        print_error "Tests failed with exit code $exit_code after ${duration}s"

        # Show logs if enabled
        if $SHOW_LOGS; then
            echo -e "\n${YELLOW}AI Service logs:${RESET}"
            docker-compose logs ai-service | tail -n 30
        fi

        return $exit_code
    fi
}

# Clean up the test environment
function cleanup() {
    if $CLEAN_UP; then
        print_section "Cleaning Up"

        start_spinner "Stopping test containers"

        if docker-compose down --volumes >>"$TEST_LOG_FILE" 2>&1; then
            stop_spinner "success" "Test containers stopped and removed"
        else
            stop_spinner "error" "Failed to clean up test containers"
            return 1
        fi
    else
        print_info "Skipping cleanup. Containers are still running."
        echo "To clean up manually, run: docker-compose -f ${PROJECT_ROOT}/docker-compose.test.yml down"
    fi
}

# Display an interactive menu
function display_menu() {
    clear
    print_header "Birth Time Rectifier - Docker Test Runner"

    echo -e "${BOLD}Please select an option:${RESET}\n"
    echo "1) Run all integration tests"
    echo "2) Run birth time rectification tests"
    echo "3) Run single test (sequence test)"
    echo "4) Run specific test file"
    echo "5) Rebuild and run tests"
    echo "6) Show container logs"
    echo "7) Clean up test environment"
    echo "8) Exit"
    echo

    read -p "Enter choice [1-8]: " choice

    case $choice in
        1)
            TEST_PATH="tests/integration/"
            ;;
        2)
            TEST_PATH="tests/integration/birth_time_rectification/"
            ;;
        3)
            # Show available tests and let user select one
            echo -e "\n${BOLD}Available sequence tests:${RESET}"
            FILES=($(find "${PROJECT_ROOT}/tests/integration/birth_time_rectification" -name "test_integration_birth_time_*.py" | sort))

            for i in "${!FILES[@]}"; do
                filename=$(basename "${FILES[$i]}")
                echo "$((i+1))) $filename"
            done

            read -p "Select test [1-${#FILES[@]}]: " test_num

            if [[ "$test_num" =~ ^[0-9]+$ ]] && [ "$test_num" -ge 1 ] && [ "$test_num" -le "${#FILES[@]}" ]; then
                TEST_PATH="${FILES[$((test_num-1))]}"
                echo -e "Selected: ${BLUE}${TEST_PATH}${RESET}"
            else
                echo -e "${RED}Invalid selection. Please try again.${RESET}"
                sleep 2
                display_menu
                return
            fi
            ;;
        4)
            # Let user specify a custom test path
            read -p "Enter test path (relative to project root): " custom_path
            TEST_PATH="${custom_path}"
            ;;
        5)
            REBUILD_CONTAINERS=true
            TEST_PATH="tests/integration/birth_time_rectification/"
            ;;
        6)
            SHOW_LOGS=true
            ;;
        7)
            CLEAN_UP=true
            ;;
        8)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${RESET}"
            sleep 2
            display_menu
            return
            ;;
    esac
}

# Main function
function main() {
    # Show menu if no command line arguments provided
    if [[ -z "$TEST_PATH" && -z "$TEST_FILTER" && "$REBUILD_CONTAINERS" == false && "$CLEAN_UP" == false ]]; then
        display_menu
    fi

    # Initialize
    initialize

    # Check requirements
    check_requirements

    # Prepare containers for testing
    prepare_containers || exit 1

    # Run the tests
    run_tests
    local test_exit_code=$?

    # Clean up
    cleanup

    # Show final message
    if [ $test_exit_code -eq 0 ]; then
        print_success "All tests completed successfully!"
    else
        print_error "Tests failed with exit code $test_exit_code"
    fi

    exit $test_exit_code
}

# Handle process interruption
function handle_interrupt() {
    echo
    print_error "Process interrupted!"
    cleanup
    exit 1
}

# Set trap for interrupt signal
trap handle_interrupt INT

# Run the main function
main
