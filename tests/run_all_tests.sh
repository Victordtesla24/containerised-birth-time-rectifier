#!/bin/bash

# Birth Time Rectifier - Comprehensive Test Runner
# This script runs all tests and health checks for the Birth Time Rectifier application
# Following best practices for test organization and execution

# Ensure we're using bash, not sh
if [ -z "$BASH_VERSION" ]; then
  echo "This script requires bash to run. Please use bash directly:"
  echo "bash $0 $*"
  exit 1
fi

# Exit on error by default (can be overridden with --continue-on-error)
set -e

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_DIR="${PROJECT_ROOT}/tests"
RESULTS_DIR="${TEST_DIR}/results"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
REPORT_FILE="${RESULTS_DIR}/test_report_${TIMESTAMP}.md"
SUMMARY_REPORT="${PROJECT_ROOT}/test_summary_report.md"
LOG_DIR="${RESULTS_DIR}/logs_${TIMESTAMP}"
CONTINUE_ON_ERROR=false
CLEANUP_TEMP=false
TEST_CONTAINERS=false
DOCKER_MODE="dev"
REMOVE_DUPLICATES=false
DUPLICATES_LOG="${LOG_DIR}/duplicate_files.log"
BACKUP_DIR="${PROJECT_ROOT}/.backups/duplicate_removal_${TIMESTAMP}"

# Track test results
# Use an associative array if supported, otherwise use a simple approach
if [[ "$(bash --version | head -n1)" > "GNU bash, version 4" ]]; then
  # Modern bash with associative arrays
  declare -A TEST_RESULTS
else
  # Fallback for older bash versions without associative arrays
  TEST_RESULTS_KEYS=()
  TEST_RESULTS_VALUES=()
fi
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --continue-on-error) CONTINUE_ON_ERROR=true ;;
    --cleanup) CLEANUP_TEMP=true ;;
    --docker) TEST_CONTAINERS=true ;;
    --docker-mode) DOCKER_MODE="$2"; shift ;;
    --remove-duplicates) REMOVE_DUPLICATES=true ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --continue-on-error    Continue running tests even if some fail"
      echo "  --cleanup              Run cleanup scripts after tests"
      echo "  --docker               Run docker container tests"
      echo "  --docker-mode <mode>   Docker mode: dev or prod (default: dev)"
      echo "  --remove-duplicates    Detect and remove duplicate files according to protocols"
      echo "  --help                 Show this help message"
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
echo -e "${BOLD}${BLUE}      BIRTH TIME RECTIFIER TEST SUITE      ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Test Run: $(date)"
echo -e "Test Root: ${PROJECT_ROOT}"
echo -e "Results Directory: ${RESULTS_DIR}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Function to set a test result
set_test_result() {
  local test_key="$1"
  local result="$2"

  if [[ "$(bash --version | head -n1)" > "GNU bash, version 4" ]]; then
    # Modern bash with associative arrays
    TEST_RESULTS["$test_key"]="$result"
  else
    # Fallback approach for older bash versions
    # Check if key already exists
    local index=-1
    for i in "${!TEST_RESULTS_KEYS[@]}"; do
      if [[ "${TEST_RESULTS_KEYS[$i]}" == "$test_key" ]]; then
        index=$i
        break
      fi
    done

    if [[ $index -ge 0 ]]; then
      TEST_RESULTS_VALUES[$index]="$result"
    else
      TEST_RESULTS_KEYS+=("$test_key")
      TEST_RESULTS_VALUES+=("$result")
    fi
  fi
}

# Function to get a test result
get_test_result() {
  local test_key="$1"

  if [[ "$(bash --version | head -n1)" > "GNU bash, version 4" ]]; then
    # Modern bash with associative arrays
    echo "${TEST_RESULTS[$test_key]}"
  else
    # Fallback approach for older bash versions
    for i in "${!TEST_RESULTS_KEYS[@]}"; do
      if [[ "${TEST_RESULTS_KEYS[$i]}" == "$test_key" ]]; then
        echo "${TEST_RESULTS_VALUES[$i]}"
        return
      fi
    done
    echo ""
  fi
}

# Function to run a test and check its result
run_test() {
  local category="$1"
  local test_name="$2"
  local command="$3"
  local log_file="${LOG_DIR}/${category}_${test_name// /_}.log"
  local test_key="${category}::${test_name}"

  ((TOTAL_TESTS++))

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
    set_test_result "$test_key" "pass"
    ((PASSED_TESTS++))
  else
    echo -e "${RED}❌ FAILED${NC} (${execution_time}s)"
    set_test_result "$test_key" "fail"
    ((FAILED_TESTS++))

    # Display last few lines of log for failed tests
    echo -e "${RED}Last 5 lines of log:${NC}"
    tail -n 5 "$log_file" | sed 's/^/  /'

    # Exit if continue on error is not enabled
    if ! $CONTINUE_ON_ERROR; then
      echo -e "${RED}Exiting due to test failure.${NC}"
      echo -e "${YELLOW}See log file for details: ${log_file}${NC}"
      exit 1
    fi
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
  if curl -s "http://localhost:${api_port}/health" > /dev/null 2>&1; then
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

# Function to start test header section
start_test_section() {
  local section_name="$1"
  echo -e "\n${BOLD}${BLUE}=== $section_name ===${NC}\n"
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

# Function to run a group of tests with header
run_test_group() {
  local group_name="$1"
  shift

  start_test_section "$group_name"

  # Run all tests in the group
  while [[ "$#" -gt 0 ]]; do
    if [[ "$#" -ge 3 ]]; then
      run_test "$1" "$2" "$3"
      shift 3
    else
      echo -e "${RED}Error: Invalid test definition for $1.${NC}"
      shift
    fi
  done
}

# Function to generate test report
generate_report() {
  echo -e "\n${YELLOW}Generating test report...${NC}"

  # Write the report header
  cat > "$REPORT_FILE" << EOF
# Birth Time Rectifier - Comprehensive Test Results

Test run on: $(date)

## Test Results Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS
- **Failed:** $FAILED_TESTS
- **Success Rate:** $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%

## Test Details

| Category | Test | Result |
|----------|------|--------|
EOF

  # Add test results to the report
  if [[ "$(bash --version | head -n1)" > "GNU bash, version 4" ]]; then
    # Modern bash with associative arrays
    for test_key in "${!TEST_RESULTS[@]}"; do
      IFS='::' read -r category test_name <<< "$test_key"
      result=${TEST_RESULTS[$test_key]}

      if [[ "$result" == "pass" ]]; then
        echo "| $category | $test_name | ✅ PASS |" >> "$REPORT_FILE"
      else
        echo "| $category | $test_name | ❌ FAIL |" >> "$REPORT_FILE"
      fi
    done
  else
    # Fallback for older bash versions
    for i in "${!TEST_RESULTS_KEYS[@]}"; do
      test_key="${TEST_RESULTS_KEYS[$i]}"
      result="${TEST_RESULTS_VALUES[$i]}"
      IFS='::' read -r category test_name <<< "$test_key"

      if [[ "$result" == "pass" ]]; then
        echo "| $category | $test_name | ✅ PASS |" >> "$REPORT_FILE"
      else
        echo "| $category | $test_name | ❌ FAIL |" >> "$REPORT_FILE"
      fi
    done
  fi

  # Add detailed logs section
  cat >> "$REPORT_FILE" << EOF

## Detailed Logs

Detailed logs for each test are available in the \`${LOG_DIR}\` directory.

EOF

  # Copy the report to the summary location
  cp "$REPORT_FILE" "$SUMMARY_REPORT"

  echo -e "${GREEN}Test report generated: $REPORT_FILE${NC}"
  echo -e "${GREEN}Summary report: $SUMMARY_REPORT${NC}"
}

# Function to detect and handle duplicate files
handle_duplicate_files() {
  start_test_section "Duplicate File Management"
  echo -e "${YELLOW}Detecting duplicate files according to directory management protocols...${NC}"

  # Create backup directory
  mkdir -p "$BACKUP_DIR"
  echo -e "${BLUE}Created backup directory: $BACKUP_DIR${NC}"

  # Initialize a log file
  mkdir -p "$(dirname "$DUPLICATES_LOG")"
  echo "# Duplicate Files Report - $(date)" > "$DUPLICATES_LOG"
  echo "Backup directory: $BACKUP_DIR" >> "$DUPLICATES_LOG"
  echo "" >> "$DUPLICATES_LOG"

  # 1. Scan for exact duplicate files (same content, different location)
  echo -e "${CYAN}Scanning for exact duplicate files...${NC}"
  echo "## Exact Duplicate Files" >> "$DUPLICATES_LOG"

  # Using fdupes to find duplicate files
  fdupes_installed=false
  if command -v fdupes &> /dev/null; then
    fdupes_installed=true
    fdupes -r "$PROJECT_ROOT" >> "$DUPLICATES_LOG"
  else
    echo -e "${YELLOW}Warning: 'fdupes' is not installed. Skipping exact duplicate detection.${NC}"
    echo "Warning: 'fdupes' is not installed. Skipping exact duplicate detection." >> "$DUPLICATES_LOG"
  fi

  # 2. Scan for similar functionality (based on file patterns)
  echo -e "${CYAN}Scanning for files with similar functionality...${NC}"
  echo "" >> "$DUPLICATES_LOG"
  echo "## Files with Similar Patterns/Functionality" >> "$DUPLICATES_LOG"

  # Define file patterns to scan based on protocols
  file_patterns=("*.py" "*.js" "*.ts" "*.tsx" "*.json" "*.txt" "*.yml" "*.yaml" "*.babelrc"
                "*.cursorrules" "*.env" "*.sh" "*.Dockerfile" "*.conf" "*.xml" "*.css" "*.html")

  # Check for duplicate JavaScript/TypeScript modules
  echo -e "${BLUE}Checking for duplicate JavaScript/TypeScript modules...${NC}"
  echo "### Duplicate JavaScript/TypeScript Modules" >> "$DUPLICATES_LOG"

  # Find files with same export names or similar function names
  for ext in "js" "ts" "tsx"; do
    echo "#### Scanning *.$ext files" >> "$DUPLICATES_LOG"
    find "$PROJECT_ROOT" -name "*.$ext" | sort | xargs grep -l "^export " 2>/dev/null | \
    while read -r file; do
      basename=$(basename "$file")
      exports=$(grep "^export " "$file" | sed 's/export //g' | sed 's/{//g' | sed 's/}//g' | tr ',' '\n' | tr -d ' ')

      if [ -n "$exports" ]; then
        echo "File: $file" >> "$DUPLICATES_LOG"
        echo "Exports: $exports" >> "$DUPLICATES_LOG"
        echo "" >> "$DUPLICATES_LOG"
      fi
    done
  done

  # Check for duplicate Python modules
  echo -e "${BLUE}Checking for duplicate Python modules...${NC}"
  echo "" >> "$DUPLICATES_LOG"
  echo "### Duplicate Python Modules" >> "$DUPLICATES_LOG"

  find "$PROJECT_ROOT" -name "*.py" | sort | xargs grep -l "^def " 2>/dev/null | \
  while read -r file; do
    basename=$(basename "$file")
    functions=$(grep "^def " "$file" | sed 's/def //g' | sed 's/(.*//g' | tr -d ' ')

    if [ -n "$functions" ]; then
      echo "File: $file" >> "$DUPLICATES_LOG"
      echo "Functions: $functions" >> "$DUPLICATES_LOG"
      echo "" >> "$DUPLICATES_LOG"
    fi
  done

  # Check for duplicate shell scripts
  echo -e "${BLUE}Checking for duplicate shell scripts...${NC}"
  echo "" >> "$DUPLICATES_LOG"
  echo "### Duplicate Shell Scripts" >> "$DUPLICATES_LOG"

  find "$PROJECT_ROOT" -name "*.sh" | sort | \
  while read -r file; do
    basename=$(basename "$file")
    echo "File: $file" >> "$DUPLICATES_LOG"
    grep "^function " "$file" 2>/dev/null | sed 's/function //g' | sed 's/(.*//g' | tr -d ' ' >> "$DUPLICATES_LOG"
    echo "" >> "$DUPLICATES_LOG"
  done

  # If specified, use the directory management script to handle duplicates
  if [ "$REMOVE_DUPLICATES" = true ]; then
    echo -e "${YELLOW}Processing duplicate files...${NC}"
    echo "## Actions Taken" >> "$DUPLICATES_LOG"

    # Create a backup of files before removing
    echo -e "${BLUE}Creating backups before removing duplicates...${NC}"

    # Use the consolidated directory management script
    if [ -f "${PROJECT_ROOT}/scripts/manage-directories.sh" ]; then
      echo -e "${GREEN}Using consolidated directory management script...${NC}"
      run_test "Directory" "Remove Duplicates" "${PROJECT_ROOT}/scripts/manage-directories.sh --consolidate"

      # Run test to verify functionality after consolidation
      run_test "Verification" "Post-Consolidation Tests" "$0 --continue-on-error"

      echo -e "${GREEN}Duplicate file handling complete. Check logs for details.${NC}"
    else
      echo -e "${RED}Error: Consolidated directory management script not found.${NC}"
      echo -e "${YELLOW}Please run this script again after creating the management script.${NC}"
      echo "Error: Consolidated directory management script not found." >> "$DUPLICATES_LOG"
    fi
  else
    echo -e "${BLUE}Duplicate file analysis complete. Check the log for details:${NC}"
    echo -e "${CYAN}$DUPLICATES_LOG${NC}"
    echo -e "${YELLOW}To remove duplicates, run with --remove-duplicates option${NC}"
  fi

  echo -e "${GREEN}Duplicate file analysis saved to: $DUPLICATES_LOG${NC}"
}

# ==========================================
# Main test execution
# ==========================================

cd "$PROJECT_ROOT"

# Section 1: Health Checks
run_test_group "Health Checks" \
  "Basic" "Health Check" "node $TEST_DIR/simple_health_check.js" \
  "Service" "Basic Service Check" "node $TEST_DIR/test_case.js"

# Section 2: Unit Tests
run_test_group "Unit Tests" \
  "Frontend" "Jest Unit Tests" "npm test -- --testPathIgnorePatterns=integration" \
  "Backend" "Python Tests" "pytest -xvs ai_service/tests/" || true

# Section 3: API Tests
run_test_group "API Tests" \
  "API" "API Integration" "node $TEST_DIR/api_tests.js" \
  "Chart" "Chart Visualization" "node $TEST_DIR/test_chart_visualization.js" \
  "Integration" "Basic Integration" "node $TEST_DIR/test_integration.js"

# Section 4: UI Tests
run_test_group "UI Tests" \
  "UI" "UI Component Tests" "node $TEST_DIR/ui_tests.js"

# Section 5: Integration Tests
start_test_section "React Integration Tests"

# Check if services are running first
if ! check_services; then
  echo -e "${YELLOW}Frontend and API services need to be running for integration tests.${NC}"
  echo -e "${YELLOW}Starting services in background...${NC}"

  # Start services with npm if using local development
  if [ -f "$PROJECT_ROOT/start.sh" ]; then
    "$PROJECT_ROOT/start.sh" &
    wait_for_services
  else
    echo -e "${RED}Could not find start.sh script. Cannot run integration tests.${NC}"
  fi
fi

if check_services; then
  run_test "Integration" "React Integration Tests" "npm test -- --testMatch=**/__tests__/integration/**/*test.{ts,tsx}"
else
  echo -e "${RED}Services are not running. Skipping integration tests.${NC}"
  set_test_result "Integration::React Integration Tests" "skip"
fi

# Section 6: Docker Container Tests
if $TEST_CONTAINERS; then
  start_test_section "Docker Container Tests"

  run_test "Docker" "Container Build & Run" "$PROJECT_ROOT/scripts/run_containers.sh $DOCKER_MODE" || true
  run_test "Docker" "Container Tests" "$PROJECT_ROOT/scripts/test_containers.sh $DOCKER_MODE" || true
fi

# Section 7: Directory Management & Cleanup
if $CLEANUP_TEMP; then
  start_test_section "Directory Management & Cleanup"

  # Check if we have the consolidated script
  if [ -f "$PROJECT_ROOT/scripts/manage-directories.sh" ]; then
    run_test "Cleanup" "Temp Files" "$PROJECT_ROOT/scripts/manage-directories.sh --cleanup" || true
  else
    run_test "Cleanup" "Temp Files" "node $PROJECT_ROOT/scripts/cleanup-temp-files.js" || true
  fi

  # Only run consolidation if the admin explicitly confirms (too risky to run automatically)
  echo -e "${YELLOW}Note: Directory consolidation scripts are not run automatically.${NC}"
  echo -e "${YELLOW}To run them manually, use:${NC}"
  echo -e "  $PROJECT_ROOT/scripts/manage-directories.sh --consolidate"
  echo -e "  $PROJECT_ROOT/scripts/manage-directories.sh --finalize"
fi

# Section 8: Handle duplicate files if requested
if $REMOVE_DUPLICATES; then
  handle_duplicate_files
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
