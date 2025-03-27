#!/bin/bash
# test_api_sequence.sh - Test the API endpoints in sequence according to api_architecture.md
# Usage: ./test_api_sequence.sh

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Config
API_GATEWAY="http://localhost:3000"
AI_SERVICE="http://localhost:8000"
OUTPUT_DIR="test_results"
SHOW_RESPONSE=true

# Create output directory
mkdir -p $OUTPUT_DIR

# Function to print header
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}# $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to run curl command and save/display results
run_curl() {
    local description=$1
    local command=$2
    local output_file=$3

    echo -e "\n${CYAN}>> $description${NC}"
    echo -e "${YELLOW}Command: $command${NC}\n"

    # Run command and save output
    eval "$command > $output_file 2>&1"
    local status=$?

    # Check if command was successful
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
        if [ "$SHOW_RESPONSE" = true ]; then
            echo -e "${YELLOW}Response:${NC}"
            cat $output_file | jq . 2>/dev/null || cat $output_file
        fi
    else
        echo -e "${RED}✗ Failed (status $status)${NC}"
        echo -e "${YELLOW}Response:${NC}"
        cat $output_file
    fi

    # Extract session ID if available
    if grep -q "session_id" $output_file; then
        SESSION_ID=$(cat $output_file | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)
        echo -e "${GREEN}Extracted session ID: $SESSION_ID${NC}"
    fi
}

print_header "SEQUENCE FLOW 1 TESTING - API ARCHITECTURE VERIFICATION"
echo -e "${YELLOW}Testing according to the API architecture document${NC}"
echo -e "${YELLOW}API Gateway: $API_GATEWAY${NC}"
echo -e "${YELLOW}AI Service: $AI_SERVICE${NC}"

print_header "1. Session Initialization"
run_curl "Initialize session via API Gateway" \
    "curl -s $API_GATEWAY/api/session/init" \
    "$OUTPUT_DIR/1_session_init.json"

print_header "2. Geocoding Request"
run_curl "Geocode location (NYC) via API Gateway" \
    "curl -s -X POST -H \"Content-Type: application/json\" -H \"X-Session-ID: $SESSION_ID\" -d '{\"query\": \"NYC\"}' $API_GATEWAY/api/geocode" \
    "$OUTPUT_DIR/2_geocode.json"

print_header "3. Direct Test of Geocoding API"
run_curl "Test direct geocoding endpoint on AI service" \
    "curl -s $AI_SERVICE/api/geocode/direct-test" \
    "$OUTPUT_DIR/3_direct_geocode.json"

print_header "4. Chart Validation"
BIRTH_DATE="1985-10-25"
BIRTH_TIME="14:30:00"
LATITUDE="40.7127753"
LONGITUDE="-74.0059728"
LOCATION="New York, NY, USA"

run_curl "Validate chart input data" \
    "curl -s -X POST -H \"Content-Type: application/json\" -H \"X-Session-ID: $SESSION_ID\" -d '{\"birth_date\": \"$BIRTH_DATE\", \"birth_time\": \"$BIRTH_TIME\", \"latitude\": $LATITUDE, \"longitude\": $LONGITUDE, \"location\": \"$LOCATION\"}' $API_GATEWAY/api/chart/validate" \
    "$OUTPUT_DIR/4_chart_validate.json"

print_header "5. Chart Generation"
run_curl "Generate chart with verification" \
    "curl -s -X POST -H \"Content-Type: application/json\" -H \"X-Session-ID: $SESSION_ID\" -d '{\"birth_date\": \"$BIRTH_DATE\", \"birth_time\": \"$BIRTH_TIME\", \"latitude\": $LATITUDE, \"longitude\": $LONGITUDE, \"location\": \"$LOCATION\", \"verify_with_openai\": true}' $API_GATEWAY/api/chart/generate" \
    "$OUTPUT_DIR/5_chart_generate.json"

# Extract chart ID if available
if grep -q "chart_id" "$OUTPUT_DIR/5_chart_generate.json"; then
    CHART_ID=$(cat "$OUTPUT_DIR/5_chart_generate.json" | grep -o '"chart_id":"[^"]*' | cut -d'"' -f4)
    echo -e "${GREEN}Extracted chart ID: $CHART_ID${NC}"

    print_header "6. Chart Retrieval"
    run_curl "Retrieve generated chart" \
        "curl -s -H \"X-Session-ID: $SESSION_ID\" $API_GATEWAY/api/chart/$CHART_ID" \
        "$OUTPUT_DIR/6_chart_retrieve.json"
else
    echo -e "${RED}Chart ID not found in response, skipping chart retrieval test${NC}"
fi

print_header "7. Format Testing: AI Service Health Check"
run_curl "Test AI service health check format" \
    "curl -s $AI_SERVICE/health" \
    "$OUTPUT_DIR/7_ai_health.json"

print_header "8. Format Testing: API Gateway Health Check"
run_curl "Test API gateway health check format" \
    "curl -s $API_GATEWAY/health" \
    "$OUTPUT_DIR/8_gateway_health.json"

print_header "9. Testing V1 API Versioning"
run_curl "Test V1 session endpoint" \
    "curl -s $API_GATEWAY/api/v1/session/init" \
    "$OUTPUT_DIR/9_v1_session.json"

echo -e "\n${GREEN}Testing complete!${NC}"
echo -e "${YELLOW}Results saved to $OUTPUT_DIR directory.${NC}"

# Print summary
echo -e "\n${BLUE}=== Test Summary ===${NC}"
SUCCESS_COUNT=$(grep -c "✓ Success" "$0.log" 2>/dev/null || echo "0")
FAILURE_COUNT=$(grep -c "✗ Failed" "$0.log" 2>/dev/null || echo "0")
echo -e "${GREEN}Successful tests: $SUCCESS_COUNT${NC}"
echo -e "${RED}Failed tests: $FAILURE_COUNT${NC}"

echo -e "\n${YELLOW}To rerun a specific test, use the curl command shown above.${NC}"
