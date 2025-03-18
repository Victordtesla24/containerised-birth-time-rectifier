#!/bin/bash

# Birth Time Rectifier - Integrated Test Runner
# This script combines standard tests with the interactive API flow test

# Ensure we're using bash, not sh
if [ -z "$BASH_VERSION" ]; then
  echo "This script requires bash to run. Please use bash directly:"
  echo "bash $0 $*"
  exit 1
fi

# Source the common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/run_all_tests_functions.sh"

# Additional configuration for integrated tests
INTERACTIVE_MODE=false
SEQUENCE_VALIDATION=false
BIRTH_DATA_FILE=""
SKIP_STANDARD_TESTS=false
OUTPUT_REPORT=""
SEQUENCE_DIAGRAM_FILE="${PROJECT_ROOT}/docs/architecture/sequence_diagram.md"
APPLICATION_FLOW_FILE="${PROJECT_ROOT}/docs/architecture/application_flow.md"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --interactive) INTERACTIVE_MODE=true ;;
    --validate-sequence) SEQUENCE_VALIDATION=true ;;
    --birth-data) BIRTH_DATA_FILE="$2"; shift ;;
    --skip-standard-tests) SKIP_STANDARD_TESTS=true ;;
    --output-report) OUTPUT_REPORT="$2"; shift ;;
    --sequence-diagram) SEQUENCE_DIAGRAM_FILE="$2"; shift ;;
    --application-flow) APPLICATION_FLOW_FILE="$2"; shift ;;
    --continue-on-error) CONTINUE_ON_ERROR=true ;;
    --cleanup) CLEANUP_TEMP=true ;;
    --docker) TEST_CONTAINERS=true ;;
    --docker-mode) DOCKER_MODE="$2"; shift ;;
    --remove-duplicates) REMOVE_DUPLICATES=true ;;
    --allow-skips) ALLOW_SKIPS=true ;;
    --allow-warnings) TREAT_WARNINGS_AS_ERRORS=false ;;
    --no-fail-fast) FAIL_FAST=false ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --interactive           Run the interactive API flow test"
      echo "  --validate-sequence     Validate test steps against sequence diagram"
      echo "  --birth-data <file>     Path to a JSON file containing birth data"
      echo "  --skip-standard-tests   Skip the standard test suite"
      echo "  --output-report <file>  Path to save the detailed test report"
      echo "  --sequence-diagram <file> Path to the sequence diagram file"
      echo "  --application-flow <file> Path to the application flow file"
      echo "  --continue-on-error     Continue running tests even if some fail"
      echo "  --cleanup               Run cleanup scripts after tests"
      echo "  --docker                Run docker container tests"
      echo "  --docker-mode <mode>    Docker mode: dev or prod (default: dev)"
      echo "  --remove-duplicates     Detect and remove duplicate files according to protocols"
      echo "  --allow-skips           Allow tests to be skipped without failing (not recommended)"
      echo "  --allow-warnings        Don't treat warnings as errors"
      echo "  --no-fail-fast          Don't stop on first test failure"
      echo "  --help                  Show this help message"
      exit 0
      ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# Create directories
mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# Header
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  BIRTH TIME RECTIFIER INTEGRATED TESTING   ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Test Run: $(date)"
echo -e "Test Root: ${PROJECT_ROOT}"
echo -e "Results Directory: ${RESULTS_DIR}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Run standard tests if not skipped
if [ "$SKIP_STANDARD_TESTS" != "true" ]; then
  echo -e "${BOLD}${BLUE}Running standard test suite...${NC}"
  run_standard_tests
else
  echo -e "${YELLOW}Skipping standard test suite as requested.${NC}"
fi

# Run the interactive API flow test if requested
if [ "$INTERACTIVE_MODE" = "true" ]; then
  start_test_section "Interactive API Flow Test"

  # Prepare command with appropriate options
  api_flow_cmd="python -m tests.test_consolidated_api_flow"

  # Add options based on user input
  if [ -n "$BIRTH_DATA_FILE" ]; then
    api_flow_cmd="$api_flow_cmd --birth-data-file $BIRTH_DATA_FILE"
  else
    # If no birth data file is provided, use random data
    api_flow_cmd="$api_flow_cmd --random-data"
  fi

  if [ "$SEQUENCE_VALIDATION" = "true" ]; then
    api_flow_cmd="$api_flow_cmd --validate-sequence --sequence-diagram-file $SEQUENCE_DIAGRAM_FILE --application-flow-file $APPLICATION_FLOW_FILE"
  fi

  if [ -n "$OUTPUT_REPORT" ]; then
    api_flow_cmd="$api_flow_cmd --output-report $OUTPUT_REPORT"
  else
    # Default output report location if not specified
    api_flow_cmd="$api_flow_cmd --output-report ${RESULTS_DIR}/api_flow_report_${TIMESTAMP}.json"
  fi

  # Run the test
  run_test "API Flow" "Interactive Test" "$api_flow_cmd"

  # Check if services are running for the test
  if ! check_services; then
    echo -e "${YELLOW}Note: Services are not running. The API flow test will use mock responses.${NC}"
    echo -e "${YELLOW}For full end-to-end testing, ensure both frontend and backend services are running.${NC}"
  fi
fi

# Run Docker container tests if requested
if [ "$TEST_CONTAINERS" = "true" ]; then
  start_test_section "Docker Container Tests"
  run_test "Docker" "Container Build & Run" "$PROJECT_ROOT/scripts/run_containers.sh $DOCKER_MODE"
  run_test "Docker" "Container Tests" "$PROJECT_ROOT/scripts/test_containers.sh $DOCKER_MODE"
fi

# Handle duplicate files if requested
if [ "$REMOVE_DUPLICATES" = "true" ]; then
  handle_duplicate_files
fi

# Run cleanup if requested
if [ "$CLEANUP_TEMP" = "true" ]; then
  start_test_section "Cleanup"
  if [ -f "${PROJECT_ROOT}/scripts/manage-directories.sh" ]; then
    run_test "Cleanup" "Temp Files" "$PROJECT_ROOT/scripts/manage-directories.sh --cleanup"
  else
    run_test "Cleanup" "Temp Files" "node $PROJECT_ROOT/scripts/cleanup-temp-files.js"
  fi
fi

# Generate comprehensive report
generate_report

# Calculate final result and exit
if [ $FAILED_TESTS -eq 0 ]; then
  echo -e "\n${GREEN}${BOLD}=== All tests passed! ===${NC}"
  exit 0
else
  echo -e "\n${RED}${BOLD}=== $FAILED_TESTS/$TOTAL_TESTS tests failed. Check the logs for details. ===${NC}"
  exit 1
fi
