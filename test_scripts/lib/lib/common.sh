#!/bin/bash

# Common utility functions for test scripts

# Colors for better output formatting
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default log file path
LOG_FILE=${LOG_FILE:-"./test_run.log"}

# Error handling framework
ERROR_LEVELS=("INFO" "WARNING" "ERROR" "FATAL")

# Function to log messages with timestamp and level
log_message() {
  local level="$1"
  local message="$2"
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")

  # Select color based on level
  local color=""
  case "$level" in
    "INFO") color="$BLUE" ;;
    "WARNING") color="$YELLOW" ;;
    "ERROR") color="$RED" ;;
    "FATAL") color="$RED$BOLD" ;;
    *) color="$NC" ;;
  esac

  echo -e "[${timestamp}] [${color}${level}${NC}] ${message}" | tee -a "$LOG_FILE"

  # Exit on fatal errors
  if [[ "$level" == "FATAL" ]]; then
    exit 1
  fi
}

# Function to check if a command exists
command_exists() {
  command -v "$1" &> /dev/null
}

# Function to check dependencies
check_dependencies() {
  local missing_deps=0

  log_message "INFO" "Checking dependencies..."

  # Required commands
  local required_commands=("curl" "jq")

  for cmd in "${required_commands[@]}"; do
    if ! command_exists "$cmd"; then
      log_message "ERROR" "Required dependency '$cmd' is not installed."
      missing_deps=$((missing_deps + 1))
    fi
  done

  # Check for websocat (optional)
  if command_exists "websocat"; then
    log_message "INFO" "WebSocket support enabled (websocat found)"
    WS_SUPPORT=true
  else
    log_message "WARNING" "WebSocket support disabled (websocat not found)"
    WS_SUPPORT=false
  fi

  if [[ $missing_deps -gt 0 ]]; then
    log_message "FATAL" "$missing_deps required dependencies are missing. Please install them and try again."
    return 1
  fi

  log_message "INFO" "All required dependencies are installed."
  return 0
}

# Function to parse command line arguments
parse_arguments() {
  local OPTIND opt

  # Default values
  VERBOSE=false
  TEST_ALL=false

  while getopts "hvmt:" opt; do
    case $opt in
      h)
        show_help
        exit 0
        ;;
      v)
        VERBOSE=true
        ;;
      m)
        MOCK_MODE=true
        log_message "INFO" "Mock mode enabled"
        ;;
      t)
        TEST_TYPE="$OPTARG"
        ;;
      \?)
        log_message "ERROR" "Invalid option: -$OPTARG"
        show_help
        exit 1
        ;;
    esac
  done

  shift $((OPTIND - 1))
}

# Function to display help message
show_help() {
  cat << EOF
Usage: run-simple-test.sh [OPTIONS]

A modular testing script for API and WebSocket testing.

Options:
  -h          Show this help message and exit
  -v          Enable verbose output
  -m          Enable mock mode (simulated API responses)
  -t TYPE     Specify test type (api, websocket, chart, questionnaire, all)

Examples:
  run-simple-test.sh -t api         Run API tests only
  run-simple-test.sh -t websocket   Run WebSocket tests only
  run-simple-test.sh -t all         Run all tests
  run-simple-test.sh -v             Run with verbose output
  run-simple-test.sh -m             Run in mock mode (no real API required)

EOF
}

# Export variables and functions
export GREEN BLUE YELLOW RED CYAN MAGENTA BOLD NC
export LOG_FILE ERROR_LEVELS
