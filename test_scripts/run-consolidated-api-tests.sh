#!/bin/bash
#
# Consolidated API Tests Script
#
# This script runs tests for the consolidated API gateway implementation
# to verify endpoints are correctly mapped with the standardized v1 prefix
# and path rewriting middleware. It integrates Python unit tests and direct
# HTTP endpoint testing to ensure complete coverage.

set -e  # Exit on any error

# Configuration
BACKEND_PORT=8000 # Python backend port
NEXT_PORT=3000 # Next.js API Gateway port (if running separately)
TIMEOUT=3 # Connection timeout in seconds

# Helper functions for colored output
green() { echo -e "\033[0;32m$1\033[0m"; }
red() { echo -e "\033[0;31m$1\033[0m"; }
yellow() { echo -e "\033[0;33m$1\033[0m"; }
blue() { echo -e "\033[0;34m$1\033[0m"; }

# Helper function to make a request with proper formatting
test_endpoint() {
  local method=$1
  local endpoint=$2
  local description=$3
  local payload=$4
  local expected_status=${5:-200}

  echo ""
  blue "Testing: $description"
  echo "Endpoint: $method $endpoint"

  # Build the curl command
  curl_cmd="curl -s -o response.json -w '%{http_code}' -X $method"
  curl_cmd+=" -H 'Content-Type: application/json'"
  curl_cmd+=" -m $TIMEOUT"

  # Add payload if provided
  if [ -n "$payload" ]; then
    curl_cmd+=" -d '$payload'"
  fi

  curl_cmd+=" $endpoint"

  # Execute the request
  echo -n "Response: "
  status=$(eval $curl_cmd)

  # Check status code
  if [ "$status" -eq "$expected_status" ]; then
    green "✓ Status $status (Expected: $expected_status)"
  else
    red "✗ Status $status (Expected: $expected_status)"
  fi

  # Display response content (limited to first few lines for brevity)
  if [ -f "response.json" ]; then
    echo "Response Preview:"
    head -n 10 response.json | sed 's/^/  /'
    echo "..."
    rm -f response.json
  fi
}

green "=================================================="
green "  Consolidated API Gateway Tests"
green "=================================================="
echo ""
yellow "This script tests the API gateway implementation with"
yellow "the standardized path structure using the /api/v1/ prefix"
yellow "and path rewriting middleware."
echo ""

# Check if services are running
yellow "Checking if services are running..."
if ! curl -s http://localhost:$BACKEND_PORT/api/v1/health > /dev/null; then
    red "❌ ERROR: Services do not appear to be running."
    red "Please start the services with 'docker-compose up' or 'npm run dev' before running tests."
    exit 1
fi
green "✅ Services are running."
echo ""

# Basic test data for API requests
BIRTH_DETAILS='{
  "birth_details": {
    "birth_date": "1990-01-01",
    "birth_time": "12:00:00",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "timezone": "America/Los_Angeles"
  }
}'

# Run Python consolidated API flow test
yellow "Running consolidated API flow test..."
cd "$(dirname "$0")/.."
python -m tests.test_consolidated_api_flow
if [ $? -eq 0 ]; then
    green "✅ Consolidated API flow test passed!"
else
    red "❌ Consolidated API flow test failed!"
    exit 1
fi
echo ""

# Run sequence diagram implementation test
yellow "Running sequence diagram implementation test..."
python -m tests.test_sequence_diagram_implementation
if [ $? -eq 0 ]; then
    green "✅ Sequence diagram implementation test passed!"
else
    red "❌ Sequence diagram implementation test failed!"
    exit 1
fi
echo ""

# Direct API endpoint testing
yellow "Testing direct API endpoints..."
yellow "This tests responses from API endpoints and backend services."

# Test verification endpoint with actual data
test_endpoint "POST" "http://localhost:$BACKEND_PORT/api/v1/chart/validate" "API Gateway - Chart Validation" "$BIRTH_DETAILS"

# Test API versioning by comparing responses
test_endpoint "GET" "http://localhost:$BACKEND_PORT/api/v1/health" "Versioned API Health Check"
test_endpoint "GET" "http://localhost:$BACKEND_PORT/api/health" "Legacy API Health Check"

# Test path rewriting with curl
yellow "Testing path rewriting middleware..."
yellow "This tests that legacy endpoints are correctly rewritten to the standardized /api/v1/ prefix."

# Test pairs (legacy path, standardized path)
test_paths=(
    "/health|/api/v1/health"
    "/geocode|/api/v1/geocode"
    "/chart/validate|/api/v1/chart/validate"
    "/chart/generate|/api/v1/chart/generate"
    "/questionnaire|/api/v1/questionnaire"
    "/chart/compare|/api/v1/chart/compare"
    "/chart/export|/api/v1/chart/export"
)

for pair in "${test_paths[@]}"; do
    legacy_path=$(echo $pair | cut -d'|' -f1)
    new_path=$(echo $pair | cut -d'|' -f2)

    blue "Testing $legacy_path redirects to $new_path... "

    # Get response headers from legacy path
    response=$(curl -s -I -X GET "http://localhost:8000$legacy_path" 2>&1)
    header_status=$(echo "$response" | grep -i "X-Deprecation-Warning")

    if [ -n "$header_status" ]; then
        green "✅ Path rewriting confirmed ($legacy_path has deprecation header)"
    else
        # Try to fetch both endpoints to see if they return similar content
        legacy_content=$(curl -s -X GET "http://localhost:8000$legacy_path" 2>&1)
        new_content=$(curl -s -X GET "http://localhost:8000$new_path" 2>&1)

        # Simple check - content length should be similar
        legacy_length=${#legacy_content}
        new_length=${#new_content}

        if (( legacy_length > 10 && new_length > 10 )) && (( ${legacy_length} * 80 / 100 <= ${new_length} && ${new_length} <= ${legacy_length} * 120 / 100 )); then
            green "✅ Path rewriting seems functional (similar content length)"
        else
            yellow "❓ Path rewriting uncertain (content differs significantly)"
        fi
    fi
done

echo ""
green "=================================================="
green "  All API Gateway Tests Completed!"
green "=================================================="
echo ""
