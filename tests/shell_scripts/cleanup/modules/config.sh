#!/bin/bash
#
# Configuration settings for duplication detection
#

# Set bash options
set -o pipefail

# Global configuration options
SIMILARITY_THRESHOLD=0.1
DETECTION_METHODS=("token" "ast" "graph")
VERBOSE=false
SHOW_HELP=false
QUICK_MODE=false
REPORT_FILE="reports/duplication_report.txt"
DIRECTORIES=()

# Resource limits and performance settings
MAX_FILESIZE=200000              # Maximum file size in bytes
ANALYSIS_TIMEOUT=600             # Timeout for analysis in seconds
FILE_COMPARISON_TIMEOUT=10       # Timeout for file comparison in seconds
MAX_FILES_TO_COMPARE=500         # Maximum number of files to compare
SKIP_DIRECTORIES=("**/node_modules/**" "**/venv/**" "**/.venv/**" "**/.git/**" "**/migrations/**")

# Python environment settings
VENV_DIR="/tmp/duplication_env"
REQUIRED_PACKAGES=("jq")  # Only non-standard packages - difflib, ast, collections, and json are built-in

# Display settings
HAS_COLOR=true
SPINNER_DELAY=0.1
PROGRESS_WIDTH=30

# Terminal color codes
if [ "$HAS_COLOR" = true ]; then
    RED="\033[0;31m"
    GREEN="\033[0;32m"
    YELLOW="\033[0;33m"
    BLUE="\033[0;34m"
    MAGENTA="\033[0;35m"
    CYAN="\033[0;36m"
    BOLD="\033[1m"
    RESET="\033[0m"
else
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    MAGENTA=""
    CYAN=""
    BOLD=""
    RESET=""
fi

# Pattern matching configurations
MOCK_PATTERNS=(
    "mock\s*\("
    "Mock\s*\("
    "@\s*mock"
    "@\s*patch"
    "patch\s*\("
    "MagicMock"
    "#\s*mock"
    "simulate"
    "simulation"
    "dummy_"
    "fake_"
    "stub_"
    "# Test implementation"
    "# Temporary implementation"
    "TODO.*implement"
    "mock.*response"
    "fake_data"
    "mock_data"
    "# TODO: Replace with actual implementation"
    "# Stub"
    "# Placeholder"
    "MakeMock"
    "create_autospec"
    "@mock_"
    "mock_.*\("
    "faked_"
    "dummy_data"
    "get_test_"
    "# Not implemented"
    "# Simulated"
    "# Test mock"
    "pass  # TODO"
)

FALLBACK_PATTERNS=(
    "try\s*:.*except"
    "fallback"
    "backup"
    "alternative"
    "if\s+error"
    "on_error"
    "if\s+exception"
    "rescue"
    "# Fallback"
    "# Emergency"
    "catch\s*\("
    "recovery"
    "on_failure"
    "if failed"
    "emergency_mode"
    "# Workaround"
    "# Temporary fix"
    "retry_"
    "retry\s*\("
    "backoff"
    "circuit_breaker"
    "failover"
    "fail_safe"
    "recover_from_"
    "fallback_strategy"
    "handle_failure"
    "except.*?retry"
    "alternate_path"
    "contingency_"
    "except.*?finally"
    "on_connection_error"
)

HARDCODED_PATTERNS=(
    "HARDCODED_"
    "# hardcoded"
    "FixedValue"
    "# Fixed value"
    "magic.number"
    "FIXED_"
    "CONST_"
    "\"https?://"
    "'https?://"
    "TODO.*config"
    "# Magic number"
    "# Should be configurable"
    "PASSWORD"
    "SECRET"
    "API_KEY"
    "SPECIAL_VALUE"
    "# Hard-coded URL"
    "# Static configuration value"
    "token\s*=\s*[\"'][\w\d]{8,}[\"']"
    "key\s*=\s*[\"'][\w\d]{8,}[\"']"
    "\"eyJ[\w-]*\\.[\w-]*\\.[\w-]*\""
    "username\s*=\s*[\"'][\w\d]+[\"']"
    "password\s*=\s*[\"'][\w\d]+[\"']"
    "[0-9a-fA-F]{32,}"
    "# TODO: Move to configuration"
    "client_id\s*=\s*[\"'][\w\d]+[\"']"
    "client_secret\s*=\s*[\"'][\w\d]+[\"']"
    "access_key\s*=\s*[\"'][\w\d]+[\"']"
)

WARNING_SUPPRESSION_PATTERNS=(
    "# noqa"
    "# nosec"
    "# pragma: no cover"
    "# type: ignore"
    "# pylint: disable"
    "# flake8: noqa"
    "warnings\.filter"
    "ignore\s+warning"
    "suppress\s+warning"
    "disable_warning"
    "# fmt: off"
    "# mypy: ignore"
    "# pyright: ignore"
    "disable_errors"
    "suppress_errors"
    "# Silence warning"
    "# ruff: noqa"
    "@suppress_warnings"
    "# ignore"
    "# no-check"
    "warnings\.catch_warnings"
    "# no-lint"
    "# NOSONAR"
    "# skipcq"
    "# codacy-disable-line"
    "@pytest\.mark\.filterwarnings"
    "ignore_warnings"
    "suppress_all_warnings"
)

ERROR_MASKING_PATTERNS=(
    "except.*?pass"
    "except.*?return"
    "except.*?None"
    "except\s*:"
    "catch\s*\(\s*\)"
    "except\s*Exception"
    "except\s*BaseException"
    "except\s*\*"
    "swallow\s+exception"
    "# Ignore exceptions"
    "# Silent fail"
    "ignore_errors"
    "suppress_exceptions"
    "# Deliberately ignoring exceptions"
    "except.*?continue"
    "silent\s*=\s*True"
    "except.*# TODO"
    "except.*?break"
    "try:.*?except.*?print"
    "if error.*?continue"
    "except.*# No action needed"
    "try:.*?except.*# Log only"
    "# Ignore any errors"
    "except.*?logging\.debug"
    "on_error\s*=\s*'ignore'"
    "try:.*?except.*?del"
    "# Errors can be ignored here"
)

TEST_SKIPPING_PATTERNS=(
    "@pytest.mark.skip"
    "@unittest.skip"
    "@skip"
    "skipTest"
    "skip_test"
    "skip\s*=\s*True"
    "# Skip test"
    "# TODO: Fix test"
    "# Disable test"
    "xtest"
    "xdescribe"
    "xit\s*\("
    "# Temporarily disabled"
    "# Test is flaky"
    "@pytest\.mark\.xfail"
    "# Flaky test"
    "# Skip on CI"
    "if CI.*?return"
    "@skip_if_"
    "# Disabled test"
    "# Skip due to"
    "pendingif"
    "disable_test"
    "# Test fails intermittently"
    "if os\.environ\.get.*?skip"
    "skipIf"
    "@pytest\.mark\.skipif"
    "# Test disabled until"
    "unittest\.skip"
)

# Tree analysis configuration
TREE_MAX_DEPTH=8
TREE_EXCLUDE_PATTERNS="node_modules|\.git|\.cache|__pycache__|\.venv|venv"

# Parse command line arguments
parse_args() {
    # Store the original args for later
    local args=("$@")

    # Process options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--threshold)
                if [[ $2 =~ ^0*([0-9]*\.?[0-9]+)$ ]]; then
                    SIMILARITY_THRESHOLD="$2"
                    shift 2
                else
                    log "ERROR" "Invalid similarity threshold value: $2"
                    return 1
                fi
                ;;
            -m|--methods)
                # Split methods by comma
                IFS=',' read -ra DETECTION_METHODS <<< "$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                SHOW_HELP=true
                shift
                ;;
            -q|--quick)
                QUICK_MODE=true
                shift
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                return 1
                ;;
            *)
                # Directories
                if [ -d "$1" ]; then
                    DIRECTORIES+=("$1")
                    shift
                else
                    log "ERROR" "Directory does not exist: $1"
                    return 1
                fi
                ;;
        esac
    done

    # Validate arguments
    if [ "${#DIRECTORIES[@]}" -eq 0 ] && [ "$SHOW_HELP" = false ]; then
        log "ERROR" "No directories specified"
        return 1
    fi

    # Validate threshold
    if (( $(echo "$SIMILARITY_THRESHOLD <= 0 || $SIMILARITY_THRESHOLD > 1" | bc -l) )); then
        log "ERROR" "Invalid similarity threshold: $SIMILARITY_THRESHOLD (must be between 0 and 1)"
        return 1
    fi

    # Validate methods
    for method in "${DETECTION_METHODS[@]}"; do
        if [[ ! " token ast graph " =~ " $method " ]]; then
            log "ERROR" "Invalid detection method: $method (valid options: token, ast, graph)"
            return 1
        fi
    done

    return 0
}
