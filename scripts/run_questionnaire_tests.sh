#!/bin/bash

# Script to run questionnaire tests with real API calls
# This script runs inside the container and ensures access to all necessary services

set -e  # Exit on error

# Set variables
CONTAINER_NAME=${CONTAINER_PREFIX:-birth-rectifier}-ai
TEST_PATH="/app/tests/integration/test_questionnaire.py"
PYTEST_INI="/app/tests/pytest.ini"

echo "Starting questionnaire tests with real API calls..."

# Ensure the container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: Container $CONTAINER_NAME is not running!"
    exit 1
fi

# Check if the test file exists
if ! docker exec $CONTAINER_NAME bash -c "[ -f $TEST_PATH ]"; then
    echo "Error: Test file $TEST_PATH not found in container!"
    exit 1
fi

# Check for API key
if ! docker exec $CONTAINER_NAME bash -c "[ -n \"\$OPENAI_API_KEY\" ]"; then
    echo "Warning: OPENAI_API_KEY not found in container environment!"
    echo "Tests may be skipped if API key is missing."
fi

# Run the tests
echo "Running questionnaire tests with real APIs..."
docker exec -it $CONTAINER_NAME bash -c "cd /app && python -m pytest $TEST_PATH -v"

# Backup the tests to ensure persistence
echo "Backing up tests for persistence..."
./scripts/backup_questionnaire_tests.sh

echo "Questionnaire tests completed."
