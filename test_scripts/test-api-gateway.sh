#!/bin/bash
#
# Test the API Gateway Implementation
#
# This script tests the unified API Gateway implementation
# by making requests to key endpoints and verifying responses.
#

set -e  # Exit on error

echo "=== API Gateway Test Script ==="
echo ""

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
API_URL=${API_URL:-"http://localhost:3000"}
BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
GATEWAY_PREFIX="/api/v1"
LEGACY_PREFIX="/api"

# Function to test an endpoint
test_endpoint() {
  local endpoint=$1
  local method=${2:-"GET"}
  local data=${3:-""}
  local expected_status=${4:-200}
  local prefix=${5:-$GATEWAY_PREFIX}

  echo -e "${YELLOW}Testing ${method} ${prefix}${endpoint}${NC}"

  # Build the curl command
  local curl_cmd="curl -s -X ${method} -w '%{http_code}' ${API_URL}${prefix}${endpoint}"

  # Add JSON data if provided
  if [ ! -z "$data" ]; then
    curl_cmd="${curl_cmd} -H 'Content-Type: application/json' -d '${data}'"
  fi

  # Execute the command and get the response with status code
  local response=$(eval ${curl_cmd})

  # Extract the status code (last 3 characters)
  local status_code=${response: -3}
  local response_body=${response:0:${#response}-3}

  # Print the results
  echo "Status Code: ${status_code}"
  echo "Response: ${response_body:0:100}..."

  # Check if status matches expected
  if [ "$status_code" -eq "$expected_status" ]; then
    echo -e "${GREEN}✓ Endpoint test passed${NC}"
    return 0
  else
    echo -e "${RED}✗ Endpoint test failed - Expected status ${expected_status}, got ${status_code}${NC}"
    echo "Full response: ${response_body}"
    return 1
  fi
}

# Test backward compatibility helper
test_legacy_endpoint() {
  local endpoint=$1
  local method=$2
  local data=$3
  local expected_status=$4

  test_endpoint "$endpoint" "$method" "$data" "$expected_status" "$LEGACY_PREFIX"
  return $?
}

# Start tests
echo "Starting API Gateway tests..."
echo ""

# Test health endpoint
test_endpoint "/health" "GET" "" 200
echo ""

# Test versioned health endpoint
test_endpoint "/health" "GET" "" 200
echo ""

# Test legacy health endpoint
test_legacy_endpoint "/health" "GET" "" 200
echo ""

# Test geocoding endpoint
test_endpoint "/geocode?query=New%20York" "GET" "" 200
echo ""

# Test legacy geocoding endpoint
test_legacy_endpoint "/geocode?query=New%20York" "GET" "" 200
echo ""

# Test chart validation endpoint
test_endpoint "/chart/validate" "POST" '{"date":"2023-01-01","time":"12:00","location":"New York","latitude":40.7128,"longitude":-74.0060}' 200
echo ""

# Test chart generation endpoint
test_endpoint "/chart/generate" "POST" '{"date":"2023-01-01","time":"12:00","location":"New York","latitude":40.7128,"longitude":-74.0060,"timezone":"America/New_York"}' 200
echo ""

# Test error handling - 404 Not Found
test_endpoint "/nonexistent-endpoint" "GET" "" 404
echo ""

# Test error handling - 400 Bad Request
test_endpoint "/chart/validate" "POST" '{"invalid":"data"}' 400
echo ""

echo -e "${GREEN}All API Gateway tests completed!${NC}"
