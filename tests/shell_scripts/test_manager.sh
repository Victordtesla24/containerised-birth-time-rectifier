#!/bin/bash
#
# Birth Time Rectifier - Test Management Script
# Purpose: A consolidated script for all testing operations
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Set strict mode
set -eo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Source the helper scripts
source "${SCRIPT_DIR}/docker/helpers/ui_helpers.sh"
source "${SCRIPT_DIR}/docker/helpers/docker_helpers.sh"

# Configuration
CONFIG_FILE="${PROJECT_ROOT}/.service_config.json"
TEST_LOG_FILE="${SCRIPT_DIR}/test_run.log"
CONTAINER_PREFIX=${CONTAINER_PREFIX:-"birth-rectifier"}
TEST_TYPE="integration"
TEST_PATH=""
TEST_FILTER=""
TEST_OPTIONS=""
REBUILD_CONTAINERS=false
SHOW_LOGS=false
VERBOSE=false
CLEAN_UP=false
TEST_ENV="test"

# Print usage information
function print_usage() {
    echo -e "\n${BOLD}Birth Time Rectifier - Test Management System${RESET}"
    echo -e "${BOLD}Usage:${RESET} $0 [command] [options]"
    echo
    echo -e "${BOLD}Commands:${RESET}"
    echo "  run            Run specified tests"
    echo "  rebuild        Rebuild test containers and run tests"
    echo "  clean          Clean up test environment"
    echo "  help           Show this help message"
    echo
    echo -e "${BOLD}Options:${RESET}"
    echo "  -t, --type TYPE         Test type (unit, integration, e2e, all) [default: integration]"
    echo "  -p, --path PATH         Specific test path to run"
    echo "  -f, --filter PATTERN    Only run tests matching pattern"
    echo "  -o, --options \"OPTS\"    Pass additional options to pytest"
    echo "  -e, --env ENV           Set test environment (test, dev, prod) [default: test]"
    echo "  -l, --logs              Show container logs during tests"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -c, --clean             Clean up containers after tests"
    echo "  -h, --help              Show this help message"
    echo
    echo -e "${BOLD}Examples:${RESET}"
    echo "  $0 run --type integration"
    echo "  $0 run --path tests/integration/birth_time_rectification/test_integration_birth_time_01_session_init.py"
    echo "  $0 rebuild --filter \"session_init\""
    echo "  $0 clean"
    echo
}

# Execute the actual test script
exec "${PROJECT_ROOT}/tests/shell_scripts/test_manager.sh" "$@"
