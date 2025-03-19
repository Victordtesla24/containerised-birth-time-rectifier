#!/bin/bash

# Birth Time Rectifier - Full Test Suite Runner
# This script runs all tests and identifies errors for systematic fixing

set -e  # Exit on any error

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
RESULTS_DIR="${PROJECT_ROOT}/test_results"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="${RESULTS_DIR}/logs_${TIMESTAMP}"

# Create directories
mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# Header
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  BIRTH TIME RECTIFIER FULL TEST SUITE     ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Test Run: $(date)"
echo -e "Test Root: ${PROJECT_ROOT}"
echo -e "Results Directory: ${LOG_DIR}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Make sure python-dotenv is installed
pip install --quiet python-dotenv

# Function to run tests with detailed logging
run_test() {
    local test_path=$1
    local test_name=$2
    local log_file="${LOG_DIR}/${test_name// /_}.log"

    echo -e "\n${BOLD}${BLUE}=== Running ${test_name} ===${NC}\n"
    echo -e "${CYAN}Command: pytest ${test_path} -v${NC}"

    # Export OpenAI API key for testing
    export OPENAI_API_KEY=${OPENAI_API_KEY:-"sk-dummy-key-for-testing"}

    # Run the test with verbose output
    PYTHONPATH=$PROJECT_ROOT python -m pytest ${test_path} -v > "$log_file" 2>&1
    local result=$?

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ ${test_name} PASSED${NC}"
    else
        echo -e "${RED}❌ ${test_name} FAILED${NC}"
        echo -e "${YELLOW}=== Test Log ===${NC}"
        cat "$log_file" | grep -E "FAILED|ERROR|XPASS|XFAIL|SKIPPED" -A 10 -B 3
        echo -e "${YELLOW}=== End Test Log ===${NC}"
        echo -e "${YELLOW}Full log saved to: ${log_file}${NC}"
    fi

    return $result
}

# Create a .env file if it doesn't exist
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    echo -e "${YELLOW}Creating .env file with test settings...${NC}"
    cat > "${PROJECT_ROOT}/.env" << EOL
# Environment variables for Birth Time Rectifier tests
OPENAI_API_KEY=sk-dummy-key-for-testing
DEBUG=True
SECRET_KEY=test-secret-key
GPU_MEMORY_FRACTION=0.7
RATE_LIMIT_PER_MINUTE=60
EOL
fi

# Ensure Python path is set correctly
PYTHONPATH=$PROJECT_ROOT

# Run all tests
echo -e "\n${BOLD}${YELLOW}Running all tests to identify errors...${NC}\n"

# Define test categories
declare -a test_categories=(
    "tests/unit/:Unit Tests"
    "tests/integration/:Integration Tests"
    "tests/components/:Component Tests"
)

# Run tests by category
failed_tests=0
for category in "${test_categories[@]}"; do
    IFS=':' read -r test_path test_name <<< "$category"
    run_test "$test_path" "$test_name" || ((failed_tests++))
done

# Final summary
echo -e "\n${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  TEST SUMMARY                             ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Test Run Completed at: $(date)"
echo -e "Results Directory: ${LOG_DIR}"

if [ $failed_tests -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ ${failed_tests} test categories failed!${NC}"
    echo -e "${YELLOW}Review the logs and fix errors systematically as per the error-fixing protocols${NC}"
    exit 1
fi
