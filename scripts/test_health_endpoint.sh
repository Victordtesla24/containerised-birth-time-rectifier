#!/bin/bash
# Test script for verifying the health endpoint implementation using the FastAPI Mounted Sub-Application pattern

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Container name
CONTAINER_NAME="birth-rectifier-ai"

echo -e "${YELLOW}Starting health endpoint verification tests...${NC}"
echo "==============================================="

# Function to test health endpoint and check response
test_endpoint() {
    local endpoint=$1
    local expected_status_code=$2
    local container=$3

    echo -e "${YELLOW}Testing endpoint: ${endpoint}${NC}"

    # Execute curl command and capture status code and response
    response=$(docker exec ${container} curl -s -o /dev/null -w "%{http_code}\n%{time_total}s" -X GET "http://localhost:8000${endpoint}")
    status_code=$(echo "${response}" | head -n1)
    time_total=$(echo "${response}" | tail -n1)

    # Verify status code
    if [ "$status_code" -eq "$expected_status_code" ]; then
        echo -e "${GREEN}✓ Status code: ${status_code} (Expected: ${expected_status_code})${NC}"
    else
        echo -e "${RED}✗ Status code: ${status_code} (Expected: ${expected_status_code})${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Response time: ${time_total}${NC}"

    # Get the full response to check the body
    body=$(docker exec ${container} curl -s "http://localhost:8000${endpoint}")
    echo "Response body: ${body}"

    # Check if response includes middleware_bypassed field (indicating mounted app is used)
    if echo "$body" | grep -q "middleware_bypassed"; then
        echo -e "${GREEN}✓ Response contains middleware_bypassed field${NC}"
    else
        echo -e "${RED}✗ Response is missing middleware_bypassed field${NC}"
        return 1
    fi

    # Check for expected fields
    if echo "$body" | grep -q "status" && echo "$body" | grep -q "timestamp" && echo "$body" | grep -q "service"; then
        echo -e "${GREEN}✓ Response contains all required fields${NC}"
    else
        echo -e "${RED}✗ Response is missing required fields${NC}"
        return 1
    fi

    return 0
}

# Function to check headers
check_headers() {
    local endpoint=$1
    local container=$2

    echo -e "${YELLOW}Checking headers for endpoint: ${endpoint}${NC}"

    # Get headers only
    headers=$(docker exec ${container} curl -s -I "http://localhost:8000${endpoint}")

    # Check for content-type
    if echo "$headers" | grep -q "content-type: application/json"; then
        echo -e "${GREEN}✓ Content-Type header is application/json${NC}"
    else
        echo -e "${RED}✗ Content-Type header is not application/json${NC}"
        echo "Headers: ${headers}"
        return 1
    fi

    # Check for cache control
    if echo "$headers" | grep -q "cache-control"; then
        echo -e "${GREEN}✓ Cache-Control header is present${NC}"
    else
        echo -e "${YELLOW}⚠ Cache-Control header is missing${NC}"
    fi

    return 0
}

# Function to test endpoint under load
test_endpoint_load() {
    local endpoint=$1
    local container=$2
    local num_requests=$3

    echo -e "${YELLOW}Testing endpoint under load: ${endpoint} with ${num_requests} requests${NC}"

    # Use a for loop to send multiple requests
    success_count=0
    for i in $(seq 1 ${num_requests}); do
        status_code=$(docker exec ${container} curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000${endpoint}")
        if [ "$status_code" -eq 200 ]; then
            success_count=$((success_count + 1))
        fi
        # Show progress
        if [ $((i % 5)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""

    # Calculate success rate
    success_rate=$(echo "scale=2; $success_count * 100 / $num_requests" | bc)

    if [ "$success_count" -eq "$num_requests" ]; then
        echo -e "${GREEN}✓ All ${num_requests} requests succeeded (100% success rate)${NC}"
    else
        echo -e "${RED}✗ ${success_count}/${num_requests} requests succeeded (${success_rate}% success rate)${NC}"
        return 1
    fi

    return 0
}

# Run the tests

# 1. Test the direct health endpoint
echo "==============================================="
echo -e "${YELLOW}Testing main health endpoint${NC}"
test_endpoint "/health" 200 "${CONTAINER_NAME}"
result1=$?
echo "==============================================="

# 2. Test the versioned health endpoint
echo -e "${YELLOW}Testing versioned health endpoint${NC}"
test_endpoint "/api/v1/health" 200 "${CONTAINER_NAME}"
result2=$?
echo "==============================================="

# 3. Test the system health endpoint
echo -e "${YELLOW}Testing system health endpoint${NC}"
test_endpoint "/system/health" 200 "${CONTAINER_NAME}"
result3=$?
echo "==============================================="

# 4. Check headers
echo -e "${YELLOW}Checking response headers${NC}"
check_headers "/health" "${CONTAINER_NAME}"
result4=$?
echo "==============================================="

# 5. Test endpoint under load (10 requests)
echo -e "${YELLOW}Testing endpoint under load${NC}"
test_endpoint_load "/health" "${CONTAINER_NAME}" 10
result5=$?
echo "==============================================="

# Summarize results
echo -e "${YELLOW}Test Summary:${NC}"
echo "==============================================="

if [ $result1 -eq 0 ]; then
    echo -e "${GREEN}✓ Main health endpoint test passed${NC}"
else
    echo -e "${RED}✗ Main health endpoint test failed${NC}"
fi

if [ $result2 -eq 0 ]; then
    echo -e "${GREEN}✓ Versioned health endpoint test passed${NC}"
else
    echo -e "${RED}✗ Versioned health endpoint test failed${NC}"
fi

if [ $result3 -eq 0 ]; then
    echo -e "${GREEN}✓ System health endpoint test passed${NC}"
else
    echo -e "${RED}✗ System health endpoint test failed${NC}"
fi

if [ $result4 -eq 0 ]; then
    echo -e "${GREEN}✓ Headers check passed${NC}"
else
    echo -e "${RED}✗ Headers check failed${NC}"
fi

if [ $result5 -eq 0 ]; then
    echo -e "${GREEN}✓ Load test passed${NC}"
else
    echo -e "${RED}✗ Load test failed${NC}"
fi

echo "==============================================="

# Calculate overall test result
if [ $result1 -eq 0 ] && [ $result2 -eq 0 ] && [ $result3 -eq 0 ] && [ $result4 -eq 0 ] && [ $result5 -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
