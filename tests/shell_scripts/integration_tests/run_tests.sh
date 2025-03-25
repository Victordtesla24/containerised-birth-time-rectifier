#!/bin/bash
# Run birth time rectification tests in sequence

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Configure test environment
export API_BASE_URL=${API_BASE_URL:-"http://api_gateway:8000"}
export TEST_LOG_DIR="$SCRIPT_DIR/logs"
export TEST_RESULTS_DIR="$SCRIPT_DIR/results"
export TEST_SEQUENCE_FILE="$TEST_RESULTS_DIR/test_sequence.pkl"

# Create directories if they don't exist
mkdir -p "$TEST_LOG_DIR"
mkdir -p "$TEST_RESULTS_DIR"

# Initialize test sequence file
if [ -f "$TEST_SEQUENCE_FILE" ]; then
    echo "Removing previous test sequence file"
    rm -f "$TEST_SEQUENCE_FILE"
fi

# Run tests in sequence
echo "===== Starting Birth Time Rectification Tests ====="
echo "API Base URL: $API_BASE_URL"
echo "Test Sequence File: $TEST_SEQUENCE_FILE"

# Run test 01 - Session Initialization
echo "===== Running Test 01: Session Initialization ====="
python -m pytest test_01_session_init.py -v

if [ $? -ne 0 ]; then
    echo "Test 01 failed! Aborting test sequence."
    exit 1
fi

# Verify the sequence file exists
if [ ! -f "$TEST_SEQUENCE_FILE" ]; then
    echo "ERROR: Test sequence file was not created!"
    exit 1
fi

# Run test 02 - Geocoding
echo "===== Running Test 02: Geocoding ====="
python -m pytest test_02_geocoding.py -v

if [ $? -ne 0 ]; then
    echo "Test 02 failed! Aborting test sequence."
    exit 1
fi

echo "===== Birth Time Rectification Tests Completed Successfully ====="
exit 0
