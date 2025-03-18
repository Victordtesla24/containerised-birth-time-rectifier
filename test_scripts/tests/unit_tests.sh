#!/bin/bash

# Unit tests for script components
# These tests verify that individual functions work correctly

# Source common functions
SCRIPT_DIR="$(dirname "$(dirname "$0")")"
source "$SCRIPT_DIR/lib/common.sh"

# Total and failed test counters
TOTAL_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
  local test_name="$1"
  local test_func="$2"

  TOTAL_TESTS=$((TOTAL_TESTS + 1))

  log_message "INFO" "Running test: $test_name"

  # Run the test function
  if $test_func; then
    log_message "INFO" "Test passed: $test_name"
    return 0
  else
    log_message "ERROR" "Test failed: $test_name"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    return 1
  fi
}

# Function to assert equality
assert_equals() {
  local expected="$1"
  local actual="$2"
  local message="${3:-Values should be equal}"

  if [[ "$expected" == "$actual" ]]; then
    return 0
  else
    log_message "ERROR" "Assertion failed: $message (expected: '$expected', actual: '$actual')"
    return 1
  fi
}

# Function to assert non-equality
assert_not_equals() {
  local expected="$1"
  local actual="$2"
  local message="${3:-Values should not be equal}"

  if [[ "$expected" != "$actual" ]]; then
    return 0
  else
    log_message "ERROR" "Assertion failed: $message (expected not: '$expected', actual: '$actual')"
    return 1
  fi
}

# Function to assert command success
assert_success() {
  local command="$1"
  local message="${2:-Command should succeed}"

  if eval "$command"; then
    return 0
  else
    log_message "ERROR" "Assertion failed: $message (command: '$command')"
    return 1
  fi
}

# Function to assert command failure
assert_failure() {
  local command="$1"
  local message="${2:-Command should fail}"

  if ! eval "$command"; then
    return 0
  else
    log_message "ERROR" "Assertion failed: $message (command: '$command')"
    return 1
  fi
}

# Test the log_message function
test_log_message() {
  local test_log="/tmp/test_log_$$.txt"
  LOG_FILE="$test_log"

  # Test INFO level
  log_message "INFO" "Test info message"
  local result=$(grep -c "\[INFO\] Test info message" "$test_log")
  assert_equals "1" "$result" "INFO message should be logged" || return 1

  # Test WARNING level
  log_message "WARNING" "Test warning message"
  local result=$(grep -c "\[WARNING\] Test warning message" "$test_log")
  assert_equals "1" "$result" "WARNING message should be logged" || return 1

  # Test ERROR level
  log_message "ERROR" "Test error message"
  local result=$(grep -c "\[ERROR\] Test error message" "$test_log")
  assert_equals "1" "$result" "ERROR message should be logged" || return 1

  # Cleanup
  rm -f "$test_log"
  return 0
}

# Test the command_exists function
test_command_exists() {
  # Test for a command that should exist
  assert_success "command_exists ls" "ls command should exist" || return 1

  # Test for a command that should not exist
  assert_failure "command_exists nonexistentcommand123" "Nonexistent command should not exist" || return 1

  return 0
}

# Test the validate_json function from validation.sh
test_validate_json() {
  source "$SCRIPT_DIR/lib/validation.sh"

  # Test valid JSON
  local valid_json='{"name":"test","value":123}'
  assert_success "validate_json '$valid_json'" "Valid JSON should validate" || return 1

  # Test invalid JSON
  local invalid_json='{"name":"test",value:123}'
  assert_failure "validate_json '$invalid_json'" "Invalid JSON should fail validation" || return 1

  return 0
}

# Test the validate_date function from validation.sh
test_validate_date() {
  source "$SCRIPT_DIR/lib/validation.sh"

  # Test valid date
  local valid_date="2000-01-01T12:00:00"
  assert_success "validate_date '$valid_date'" "Valid date should validate" || return 1

  # Test invalid date
  local invalid_date="2000-13-01T12:00:00"
  assert_failure "validate_date '$invalid_date'" "Invalid date should fail validation" || return 1

  return 0
}

# Test the api_request function from api_client.sh
test_api_request() {
  source "$SCRIPT_DIR/lib/api_client.sh"

  # Mock the curl command with a wrapper function
  curl() {
    echo '{"result":"success"}'
    return 0
  }

  # Test a successful API request
  local response=$(api_request "GET" "/test" "{}")
  assert_equals '{"result":"success"}' "$response" "API request should return expected response" || return 1

  # Mock a failing curl command
  curl() {
    return 1
  }

  # Test a failing API request with retry
  assert_failure "api_request 'GET' '/test' '{}' >/dev/null" "API request should fail after retries" || return 1

  return 0
}

# Run all tests
run_all_tests() {
  log_message "INFO" "Starting unit tests..."

  # Run individual tests
  run_test "log_message" test_log_message
  run_test "command_exists" test_command_exists
  run_test "validate_json" test_validate_json
  run_test "validate_date" test_validate_date
  run_test "api_request" test_api_request

  # Add more tests here

  # Print summary
  log_message "INFO" "Tests completed: $TOTAL_TESTS total, $((TOTAL_TESTS - FAILED_TESTS)) passed, $FAILED_TESTS failed"

  # Return success if all tests passed
  if [[ $FAILED_TESTS -eq 0 ]]; then
    log_message "INFO" "All tests passed!"
    return 0
  else
    log_message "ERROR" "Some tests failed!"
    return 1
  fi
}

# Run all tests if this script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  run_all_tests
fi
