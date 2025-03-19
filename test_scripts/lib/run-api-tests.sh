#!/bin/bash

# Birth Time Rectifier - API Sequence Test Runner
# This script runs the Python API sequence flow tests

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${PROJECT_ROOT}/tests"
RESULTS_DIR="${TEST_DIR}/results"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="${RESULTS_DIR}/logs_${TIMESTAMP}"
SEQUENCE_DIAGRAM_FILE="${PROJECT_ROOT}/docs/architecture/sequence_diagram.md"

# Create directories
mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# Header
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  BIRTH TIME RECTIFIER API SEQUENCE TEST   ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Test Run: $(date)"
echo -e "Test Root: ${PROJECT_ROOT}"
echo -e "Results Directory: ${RESULTS_DIR}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Function to check if a port is in use
is_port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -i :"$1" >/dev/null 2>&1
    return $?
  elif command -v netstat >/dev/null 2>&1; then
    netstat -tuln | grep -q ":$1 "
    return $?
  else
    # Default to true if we can't check
    return 0
  fi
}

# Function to kill any process using the API port
kill_api_process() {
  local api_port=${1:-9000}

  if is_port_in_use "$api_port"; then
    echo -e "${YELLOW}Killing process using port ${api_port}...${NC}"

    if command -v lsof >/dev/null 2>&1; then
      local pid=$(lsof -t -i:"$api_port")
      if [ -n "$pid" ]; then
        kill -9 "$pid" 2>/dev/null
        echo -e "${GREEN}Killed process with PID ${pid}${NC}"
      fi
    elif command -v netstat >/dev/null 2>&1 && command -v grep >/dev/null 2>&1 && command -v awk >/dev/null 2>&1; then
      local pid=$(netstat -tuln | grep ":$api_port " | awk '{print $7}' | cut -d'/' -f1)
      if [ -n "$pid" ]; then
        kill -9 "$pid" 2>/dev/null
        echo -e "${GREEN}Killed process with PID ${pid}${NC}"
      fi
    else
      echo -e "${RED}Could not identify process using port ${api_port}${NC}"
    fi
  else
    echo -e "${GREEN}No process using port ${api_port}${NC}"
  fi
}

# Kill any process using the API port
API_PORT=9000
kill_api_process $API_PORT

# Create Python path setup script
cat > "${PROJECT_ROOT}/setup_pythonpath.py" << 'EOL'
import sys
import os

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add project root to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Print the updated Python path
print(f"Python path updated: {sys.path}")
EOL

# Start the API service
echo -e "${YELLOW}Starting AI service on port ${API_PORT}...${NC}"
cd "$PROJECT_ROOT"
python -c "import setup_pythonpath" && \
API_PORT=$API_PORT python -m ai_service.main > "${LOG_DIR}/ai_service.log" 2>&1 &
API_PID=$!

# Wait for service to initialize
echo -e "${YELLOW}Waiting for AI service to initialize...${NC}"
for i in {1..10}; do
  if curl -s "http://localhost:${API_PORT}/api/health" > /dev/null 2>&1 || \
     curl -s "http://localhost:${API_PORT}/api/v1/health" > /dev/null 2>&1; then
    echo -e "${GREEN}AI service is running on port ${API_PORT}${NC}"
    break
  fi

  if [ $i -eq 10 ]; then
    echo -e "${RED}AI service failed to start!${NC}"
    cat "${LOG_DIR}/ai_service.log"
    kill $API_PID 2>/dev/null
    exit 1
  fi

  echo -e "${YELLOW}Waiting... (${i}/10)${NC}"
  sleep 3
done

# Run API sequence flow tests
echo -e "\n${BOLD}${BLUE}=== Running API Sequence Flow Tests ===${NC}\n"

# Use Python's import resolution support
TEST_CMD="cd ${PROJECT_ROOT} && python -c 'import setup_pythonpath' && python -m pytest tests/integration/test_api_sequence_flow.py -v"

echo -e "${CYAN}Running: ${TEST_CMD}${NC}"
eval "$TEST_CMD" > "${LOG_DIR}/api_sequence_test.log" 2>&1
TEST_EXIT_CODE=$?

# Display test results
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✅ API Sequence Flow Tests PASSED${NC}"
else
  echo -e "${RED}❌ API Sequence Flow Tests FAILED${NC}"
  echo -e "${RED}Test log:${NC}"
  cat "${LOG_DIR}/api_sequence_test.log"
fi

# Cleanup
echo -e "${YELLOW}Shutting down AI service...${NC}"
kill $API_PID 2>/dev/null

# Final result
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}All tests completed successfully!${NC}"
  exit 0
else
  echo -e "\n${RED}Tests failed. See logs for details:${NC}"
  echo -e "${YELLOW}${LOG_DIR}/api_sequence_test.log${NC}"
  exit 1
fi
