#!/bin/bash

# Script to copy test files to the container and run the tests

set -e  # Exit on error

# Container name for the AI service
CONTAINER_NAME=${CONTAINER_PREFIX:-birth-rectifier}-ai

echo "Ensuring test files are up-to-date in container: $CONTAINER_NAME"

# Check if the container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "Error: Container $CONTAINER_NAME is not running"
    echo "Make sure to start the containers with 'docker-compose up -d' first"
    exit 1
fi

# Copy the test files to the container
echo "Copying test files to container..."
docker cp ./tests $CONTAINER_NAME:/app/tests
echo "Test files copied successfully."

# Set environment variables for API endpoints
API_URL=${API_URL:-"http://api_gateway:8000"}
WS_URL=${WS_URL:-"ws://api_gateway:8000/ws"}

# Check if we have a specific test to run
if [ "$1" != "" ]; then
    TEST_PATH="$1"
    shift # Remove the first argument (test path)
    echo "Running specific test: $TEST_PATH"
    docker exec -it -e API_URL="$API_URL" -e WS_URL="$WS_URL" $CONTAINER_NAME python -m pytest $TEST_PATH "$@"
else
    # Run all tests
    echo "Running all birth time rectification tests..."
    docker exec -it -e API_URL="$API_URL" -e WS_URL="$WS_URL" $CONTAINER_NAME python -m pytest tests/integration/birth_time_rectification/run_all_tests.py "$@"
fi

# Get the exit code of the last command
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "Tests completed successfully!"
else
    echo "Tests failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
