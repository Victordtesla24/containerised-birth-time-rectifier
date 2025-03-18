#!/bin/bash

# Birth Time Rectifier - Integrated API Test Runner
# This script runs the Python API tests and then the frontend tests

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="${PROJECT_ROOT}/tests"
RESULTS_DIR="${TEST_DIR}/results"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="${RESULTS_DIR}/logs_${TIMESTAMP}"
REPORT_FILE="${RESULTS_DIR}/api_test_report_${TIMESTAMP}.json"
BIRTH_DATA_FILE="${PROJECT_ROOT}/test_data/sample_birth_data.json"
SEQUENCE_DIAGRAM_FILE="${PROJECT_ROOT}/docs/architecture/sequence_diagram.md"
APPLICATION_FLOW_FILE="${PROJECT_ROOT}/docs/architecture/application_flow.md"

# Create directories
mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# Header
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  BIRTH TIME RECTIFIER INTEGRATED API TEST  ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Test Run: $(date)"
echo -e "Test Root: ${PROJECT_ROOT}"
echo -e "Results Directory: ${RESULTS_DIR}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Parse command line arguments
RANDOM_DATA=false
VALIDATE_SEQUENCE=false
CONFIDENCE_THRESHOLD=0.8
SKIP_FRONTEND=false
SKIP_BACKEND=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --random-data) RANDOM_DATA=true ;;
    --validate-sequence) VALIDATE_SEQUENCE=true ;;
    --confidence-threshold) CONFIDENCE_THRESHOLD="$2"; shift ;;
    --skip-frontend) SKIP_FRONTEND=true ;;
    --skip-backend) SKIP_BACKEND=true ;;
    --birth-data) BIRTH_DATA_FILE="$2"; shift ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --random-data             Use random birth data instead of sample data"
      echo "  --validate-sequence       Validate test steps against sequence diagram"
      echo "  --confidence-threshold N  Set confidence threshold for questionnaire (0.0-1.0)"
      echo "  --skip-frontend           Skip frontend tests"
      echo "  --skip-backend            Skip backend tests"
      echo "  --birth-data FILE         Path to birth data JSON file"
      echo "  --help                    Show this help message"
      exit 0
      ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# Function to run a test and check its result
run_test() {
  local category="$1"
  local test_name="$2"
  local command="$3"
  local log_file="${LOG_DIR}/${category}_${test_name// /_}.log"

  echo -e "\n${YELLOW}Running: ${BOLD}$category - $test_name${NC}"
  echo -e "${CYAN}Command: $command${NC}"

  # Create a timer
  local start_time=$(date +%s)

  # Execute the command and capture output
  set +e
  eval "$command" > "$log_file" 2>&1
  local exit_code=$?
  set -e

  # Calculate execution time
  local end_time=$(date +%s)
  local execution_time=$((end_time - start_time))

  # Display result
  if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC} (${execution_time}s)"
  else
    echo -e "${RED}❌ FAILED${NC} (${execution_time}s)"
    echo -e "${RED}Last 10 lines of log:${NC}"
    tail -n 10 "$log_file" | sed 's/^/  /'
    echo -e "${YELLOW}See log file for details: ${log_file}${NC}"
  fi

  # Return the exit code
  return $exit_code
}

# Function to check if services are running
check_services() {
  local frontend_port=${1:-3000}
  local api_port=${2:-8000}

  echo -e "${BLUE}Checking if services are running...${NC}"

  # Check if frontend is running
  if curl -s "http://localhost:${frontend_port}" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend service is running on port ${frontend_port}${NC}"
    frontend_running=true
  else
    echo -e "${RED}✗ Frontend service is not running on port ${frontend_port}${NC}"
    frontend_running=false
  fi

  # Check if AI service is running
  if curl -s "http://localhost:${api_port}/api/v1/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AI service is running on port ${api_port}${NC}"
    api_running=true
  else
    echo -e "${RED}✗ AI service is not running on port ${api_port}${NC}"
    api_running=false
  fi

  # Return true if both services are running
  if [ "$frontend_running" = true ] && [ "$api_running" = true ]; then
    return 0
  else
    return 1
  fi
}

# Function to wait for services to start
wait_for_services() {
  local max_attempts=20
  local attempt=1
  local frontend_port=${1:-3000}
  local api_port=${2:-8000}

  echo -e "${BLUE}Waiting for services to start...${NC}"

  while [ $attempt -le $max_attempts ]; do
    if check_services "$frontend_port" "$api_port"; then
      echo -e "${GREEN}All services are running!${NC}"
      return 0
    fi

    echo -e "${YELLOW}Waiting for services... (Attempt $attempt/$max_attempts)${NC}"
    attempt=$((attempt + 1))
    sleep 5
  done

  echo -e "${RED}Timeout waiting for services to start.${NC}"
  return 1
}

# Check if services are running
if ! check_services; then
  echo -e "${YELLOW}Starting services in background...${NC}"

  # Start backend service if not running
  if [ "$frontend_running" = false ]; then
    echo -e "${YELLOW}Starting frontend service...${NC}"
    cd "$PROJECT_ROOT" && npm run dev > "${LOG_DIR}/frontend_service.log" 2>&1 &
    FRONTEND_PID=$!
  fi

  # Start backend service if not running
  if [ "$api_running" = false ]; then
    echo -e "${YELLOW}Starting backend service...${NC}"
    cd "$PROJECT_ROOT" && python -m ai_service.main > "${LOG_DIR}/backend_service.log" 2>&1 &
    BACKEND_PID=$!
  fi

  # Wait for services to start
  wait_for_services
fi

# Run backend tests if not skipped
if [ "$SKIP_BACKEND" = false ]; then
  echo -e "\n${BOLD}${BLUE}=== Running Backend Tests ===${NC}\n"

  # Prepare Python test command
  PYTHON_TEST_CMD="python -m pytest ${TEST_DIR} -v"

  # Run the test
  run_test "Backend" "Python Tests" "$PYTHON_TEST_CMD"
  BACKEND_EXIT_CODE=$?
else
  echo -e "\n${YELLOW}Skipping backend tests as requested.${NC}"
  BACKEND_EXIT_CODE=0
fi

# Run frontend tests if not skipped
if [ "$SKIP_FRONTEND" = false ]; then
  echo -e "\n${BOLD}${BLUE}=== Running Frontend Tests ===${NC}\n"

  # Run the test
  run_test "Frontend" "Jest Tests" "cd ${PROJECT_ROOT} && npm test"
  FRONTEND_EXIT_CODE=$?
else
  echo -e "\n${YELLOW}Skipping frontend tests as requested.${NC}"
  FRONTEND_EXIT_CODE=0
fi

# Run API flow test
echo -e "\n${BOLD}${BLUE}=== Running API Flow Test ===${NC}\n"

# Prepare API flow test command
API_FLOW_CMD="cd ${PROJECT_ROOT} && python ${TEST_DIR}/test_consolidated_api_flow.py"

# Add options based on user input
if [ "$RANDOM_DATA" = true ]; then
  API_FLOW_CMD="${API_FLOW_CMD} --random-data"
else
  API_FLOW_CMD="${API_FLOW_CMD} --birth-data-file ${BIRTH_DATA_FILE}"
fi

if [ "$VALIDATE_SEQUENCE" = true ]; then
  API_FLOW_CMD="${API_FLOW_CMD} --validate-sequence --sequence-diagram-file ${SEQUENCE_DIAGRAM_FILE} --application-flow-file ${APPLICATION_FLOW_FILE}"
fi

API_FLOW_CMD="${API_FLOW_CMD} --confidence-threshold ${CONFIDENCE_THRESHOLD} --output-report ${REPORT_FILE}"

# Run the test
run_test "API Flow" "End-to-End Test" "$API_FLOW_CMD"
API_FLOW_EXIT_CODE=$?

# Cleanup services started by this script
cleanup_services() {
  if [ -n "$FRONTEND_PID" ]; then
    echo -e "${YELLOW}Stopping frontend service (PID: $FRONTEND_PID)...${NC}"
    kill $FRONTEND_PID
  fi

  if [ -n "$BACKEND_PID" ]; then
    echo -e "${YELLOW}Stopping backend service (PID: $BACKEND_PID)...${NC}"
    kill $BACKEND_PID
  fi
}

# Register cleanup function to run on exit
trap cleanup_services EXIT

# Calculate final result and exit
if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ] && [ $API_FLOW_EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}${BOLD}=== All tests passed! ===${NC}"
  exit 0
else
  echo -e "\n${RED}${BOLD}=== Some tests failed. Check the logs for details. ===${NC}"
  exit 1
fi
