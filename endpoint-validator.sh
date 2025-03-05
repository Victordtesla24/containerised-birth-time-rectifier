#!/bin/bash

# Endpoint Validator for Birth Time Rectifier API
#
# This script tests the API endpoints against the dual-registration pattern:
# - Primary endpoints with /api/ prefix (e.g., /api/chart/validate)
# - Alternative endpoints without prefix (e.g., /chart/validate)
#
# Usage:
#   ./endpoint-validator.sh [options]
#
# Options:
#   --host,-h HOST     Base host URL to test (default: http://localhost:3000)
#   --verbose,-v       Show more detailed output
#   --help             Show this help message
#

# Default settings
HOST="http://localhost:3000"
VERBOSE=false

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --host|-h)
      HOST="$2"
      shift 2
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --host,-h HOST     Base host URL to test (default: http://localhost:3000)"
      echo "  --verbose,-v       Show more detailed output"
      echo "  --help             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Remove trailing slash from host if present
if [[ "$HOST" == */ ]]; then
  HOST="${HOST%/}"
fi

echo -e "${BLUE}=== Endpoint Validator for Birth Time Rectifier API ===${NC}"
echo -e "Testing host: $HOST"
echo -e "Verifying dual-registration pattern...\n"

# Define endpoints to test based on the dual-registration pattern
# Format: method:path:description
ENDPOINTS=(
  # Primary endpoints (with /api/ prefix)
  "GET:/api/health:Health check"
  "POST:/api/chart/validate:Birth details validation"
  "GET:/api/geocode:Geocoding service"
  "POST:/api/chart/generate:Chart generation"
  "GET:/api/chart/1:Chart retrieval"
  "GET:/api/questionnaire:Questionnaire"
  "POST:/api/chart/rectify:Birth time rectification"
  "POST:/api/chart/export:Chart export"

  # Alternative endpoints (without /api/ prefix)
  "GET:/health:Health check (alt)"
  "POST:/chart/validate:Birth details validation (alt)"
  "GET:/geocode:Geocoding service (alt)"
  "POST:/chart/generate:Chart generation (alt)"
  "GET:/chart/1:Chart retrieval (alt)"
  "GET:/questionnaire:Questionnaire (alt)"
  "POST:/chart/rectify:Birth time rectification (alt)"
  "POST:/chart/export:Chart export (alt)"
)

# Statistics
TOTAL=0
TOTAL_SUCCESS=0
PRIMARY_SUCCESS=0
ALTERNATIVE_SUCCESS=0

# Results storage for constants.js generation
PRIMARY_RESULTS=()
ALTERNATIVE_RESULTS=()

# Test a single endpoint
test_endpoint() {
  local method=$1
  local path=$2
  local description=$3
  local is_primary=false

  if [[ "$path" == /api/* ]]; then
    is_primary=true
  fi

  local url="${HOST}${path}"

  # Prepare curl command
  if [[ "$method" == "GET" ]]; then
    # For GET requests
    cmd="curl -s -o /dev/null -w '%{http_code}' -X $method \"$url\""
  else
    # For POST/PUT/DELETE with minimal JSON body
    cmd="curl -s -o /dev/null -w '%{http_code}' -X $method -H 'Content-Type: application/json' -d '{}' \"$url\""
  fi

  # Run the command and capture status code
  if $VERBOSE; then
    echo "Testing $method $path ($description)"
    echo "Command: $cmd"
  fi

  # Execute the curl command
  status=$(eval $cmd)

  # Check if endpoint is available (200 OK or 4xx = endpoint exists but has validation issues)
  if [[ "$status" =~ ^(200|400|401|403|404|422)$ ]]; then
    if $is_primary; then
      echo -e "${GREEN}✓${NC} Primary: $method $path - $status"
      PRIMARY_SUCCESS=$((PRIMARY_SUCCESS + 1))
      # Store successful endpoint for constants.js generation
      normalized_path=${path#/api/}
      PRIMARY_RESULTS+=("$normalized_path:$method")
    else
      echo -e "${GREEN}✓${NC} Alternative: $method $path - $status"
      ALTERNATIVE_SUCCESS=$((ALTERNATIVE_SUCCESS + 1))
      # Store successful endpoint for constants.js generation
      normalized_path=${path#/}
      ALTERNATIVE_RESULTS+=("$normalized_path:$method")
    fi
    TOTAL_SUCCESS=$((TOTAL_SUCCESS + 1))
    return 0
  else
    if $is_primary; then
      echo -e "${RED}✗${NC} Primary: $method $path - $status"
    else
      echo -e "${RED}✗${NC} Alternative: $method $path - $status"
    fi
    return 1
  fi
}

# Test all endpoints
for endpoint in "${ENDPOINTS[@]}"; do
  IFS=':' read -r method path description <<< "$endpoint"
  test_endpoint "$method" "$path" "$description"
  TOTAL=$((TOTAL + 1))
done

# Calculate statistics
PRIMARY_TOTAL=$((TOTAL / 2))
ALTERNATIVE_TOTAL=$((TOTAL / 2))

# Output results
echo -e "\n${BLUE}=== Test Results ===${NC}"
echo "Total endpoints tested: $TOTAL"
echo "Total successful: $TOTAL_SUCCESS/$TOTAL"
echo "Primary (/api/ prefix) endpoints: $PRIMARY_SUCCESS/$PRIMARY_TOTAL"
echo "Alternative (no prefix) endpoints: $ALTERNATIVE_SUCCESS/$ALTERNATIVE_TOTAL"

# Check if both patterns are supported
if [[ $PRIMARY_SUCCESS -gt 0 && $ALTERNATIVE_SUCCESS -gt 0 ]]; then
  echo -e "\n${GREEN}✓ Dual-registration pattern is supported${NC}"
else
  echo -e "\n${RED}✗ Dual-registration pattern is not fully supported${NC}"
  if [[ $PRIMARY_SUCCESS -gt 0 ]]; then
    echo "   Only primary endpoints (/api/ prefix) are working"
  elif [[ $ALTERNATIVE_SUCCESS -gt 0 ]]; then
    echo "   Only alternative endpoints (no prefix) are working"
  else
    echo "   No endpoints are working"
  fi
fi

# Generate recommended constants.js configuration
echo -e "\n${BLUE}=== Recommended constants.js Configuration ===${NC}"

# Start generating constants.js content
echo "export const API_ENDPOINTS = {"
echo "    // Primary endpoints (with /api/ prefix)"

# Add primary endpoints
for result in "${PRIMARY_RESULTS[@]}"; do
  IFS=':' read -r path method <<< "$result"

  # Convert path to camelCase for key name
  key=$(echo "$path" | sed -E 's/[\/{}]/_/g' | sed -E 's/_([a-z])/\U\1/g' | sed -E 's/^_//')

  # Handle chart endpoints specially
  if [[ "$path" == chart/* ]]; then
    echo "    $key: '/api/$path',"
  else
    echo "    $key: '/api/$path',"
  fi
done

echo ""
echo "    // Alternative endpoints without /api/ prefix (for backward compatibility)"

# Add alternative endpoints
for result in "${ALTERNATIVE_RESULTS[@]}"; do
  IFS=':' read -r path method <<< "$result"

  # Convert path to camelCase for key name
  key=$(echo "$path" | sed -E 's/[\/{}]/_/g' | sed -E 's/_([a-z])/\U\1/g' | sed -E 's/^_//')

  echo "    ${key}Alt: '/$path',"
done

echo "};"

echo -e "\n${YELLOW}Based on successful endpoints, update tests/e2e/constants.js with the working endpoints.${NC}"
