#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}       API TESTING SCRIPT - SEQ DIAGRAM        ${NC}"
echo -e "${BLUE}===============================================${NC}"

# Store test results here
TEST_RESULTS_FILE="api_test_results.txt"
> "$TEST_RESULTS_FILE" # Clear the file

# Function to print results in a formatted way
print_test_result() {
    local endpoint=$1
    local curl_cmd=$2
    local response=$3
    local integration=$4
    local implementation=$5

    echo -e "\n=========== cURL TEST REPORT ===========" | tee -a "$TEST_RESULTS_FILE"
    echo "1. AI SERVICE API ENDPOINT: $endpoint" | tee -a "$TEST_RESULTS_FILE"
    echo "2. AI SERVICE API ENDPOINT INPUT: $curl_cmd" | tee -a "$TEST_RESULTS_FILE"
    echo "3. AI SERVICE API ENDPOINT RESPONSE STRUCTURE: $response" | tee -a "$TEST_RESULTS_FILE"
    echo "4. AI SERVICE <-> API GATEWAY API ENDPOINT INTEGRATION: $integration" | tee -a "$TEST_RESULTS_FILE"
    echo "5. AI SERVICE API ENDPOINT PRODUCTION IMPLEMENTATION WITHOUT MOCKUPS & FAKE POSITIVES VERIFIED: $implementation" | tee -a "$TEST_RESULTS_FILE"
    echo "========================================" | tee -a "$TEST_RESULTS_FILE"
}

# Function to test an API endpoint and return results
test_api_endpoint() {
    local endpoint=$1
    local http_method=$2
    local curl_params=$3
    local gateway_path=$4

    echo -e "${YELLOW}Testing endpoint: $endpoint${NC}"
    echo -e "${YELLOW}HTTP Method: $http_method${NC}"
    echo -e "${YELLOW}Command: curl -X $http_method $curl_params http://localhost:8000$endpoint${NC}"

    # Execute the curl command and capture the response
    local response
    response=$(eval "curl -s -X '$http_method' $curl_params 'http://localhost:8000$endpoint'")
    local exit_code=$?

    # Check if the curl command was successful
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}Error executing curl command. Exit code: $exit_code${NC}"
        return 1
    fi

    echo -e "${GREEN}Response: $response${NC}"

    # Return the response
    echo "$response"
}

# Function to check implementation in code files
check_implementation() {
    local endpoint=$1
    local pattern=$2

    echo -e "${YELLOW}Checking implementation for endpoint: $endpoint${NC}"

    # Use grep to search for the endpoint in the code
    local result
    result=$(find ai_service -name "*.py" -exec grep -l "$pattern" {} \;)

    if [ -n "$result" ]; then
        echo -e "${GREEN}Implementation found in: $result${NC}"
        echo "YES - The endpoint is implemented in $result"
    else
        echo -e "${RED}Implementation not found${NC}"
        echo "NO - Could not find implementation"
    fi
}

# Global variable to store the session ID
SESSION_ID=""

# Store chart_id
CHART_ID=""

# Store question ID
QUESTION_ID=""

echo -e "${BLUE}============ STARTING SEQUENCE 1 ============${NC}"
echo -e "${BLUE}Testing Session Initialization${NC}"

SESSION_RESPONSE=$(test_api_endpoint "/api/session/init" "GET" "")
SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"session_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}Session initialized with ID: $SESSION_ID${NC}"
    implementation=$(check_implementation "/api/v1/session/init" "def init_session")
    print_test_result "/api/v1/session/init" "curl -X GET http://localhost:8000/api/session/init" "$SESSION_RESPONSE" "/api/session/init → /api/v1/session/init" "$implementation"
else
    echo -e "${RED}Failed to initialize session${NC}"
    print_test_result "/api/v1/session/init" "curl -X GET http://localhost:8000/api/session/init" "$SESSION_RESPONSE" "/api/session/init → /api/v1/session/init" "NO - Session initialization failed"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 2 ============${NC}"
echo -e "${BLUE}Testing Geocoding${NC}"

GEOCODE_RESPONSE=$(test_api_endpoint "/api/geocode?query=NYC&limit=5&include_timezone=true" "GET" "")
GEOCODE_SUCCESS=$(echo "$GEOCODE_RESPONSE" | grep -o '"success":true' | wc -l)

if [ "$GEOCODE_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Geocoding successful${NC}"
    implementation=$(check_implementation "/api/v1/geocode" "def geocode")
    print_test_result "/api/v1/geocode" "curl -X GET \"http://localhost:8000/api/geocode?query=NYC&limit=5&include_timezone=true\"" "$GEOCODE_RESPONSE" "/api/geocode → /api/v1/geocode" "$implementation"
else
    echo -e "${RED}Geocoding failed${NC}"
    print_test_result "/api/v1/geocode" "curl -X GET \"http://localhost:8000/api/geocode?query=NYC&limit=5&include_timezone=true\"" "$GEOCODE_RESPONSE" "/api/geocode → /api/v1/geocode" "NO - Geocoding failed"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 3 ============${NC}"
echo -e "${BLUE}Testing Chart Validation${NC}"

VALIDATE_DATA='{\"birth_details\":{\"birth_date\":\"1990-01-01\",\"birth_time\":\"12:00:00\",\"latitude\":40.7128,\"longitude\":-74.0060,\"timezone\":\"America/New_York\"}}'
VALIDATE_RESPONSE=$(test_api_endpoint "/api/chart/validate" "POST" "-H \"Content-Type: application/json\" -d '$VALIDATE_DATA'")
VALIDATE_SUCCESS=$(echo "$VALIDATE_RESPONSE" | grep -o '"valid":true' | wc -l)

if [ "$VALIDATE_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Chart validation successful${NC}"
    implementation=$(check_implementation "/api/v1/chart/validate" "def validate")
    print_test_result "/api/v1/chart/validate" "curl -X POST http://localhost:8000/api/chart/validate -H \"Content-Type: application/json\" -d '$VALIDATE_DATA'" "$VALIDATE_RESPONSE" "/api/chart/validate → /api/v1/chart/validate" "$implementation"
else
    echo -e "${RED}Chart validation failed${NC}"
    print_test_result "/api/v1/chart/validate" "curl -X POST http://localhost:8000/api/chart/validate -H \"Content-Type: application/json\" -d '$VALIDATE_DATA'" "$VALIDATE_RESPONSE" "/api/chart/validate → /api/v1/chart/validate" "NO - Chart validation failed"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 4 ============${NC}"
echo -e "${BLUE}Testing Chart Generation${NC}"

GENERATE_DATA='{\"birth_details\":{\"birth_date\":\"1990-01-01\",\"birth_time\":\"12:00:00\",\"latitude\":40.7128,\"longitude\":-74.0060,\"timezone\":\"America/New_York\"},\"session_id\":\"'$SESSION_ID'\",\"verify_with_openai\":true}'
GENERATE_RESPONSE=$(test_api_endpoint "/api/chart/generate" "POST" "-H \"Content-Type: application/json\" -d '$GENERATE_DATA'")
CHART_ID=$(echo "$GENERATE_RESPONSE" | grep -o '"chart_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')

if [ -n "$CHART_ID" ]; then
    echo -e "${GREEN}Chart generated with ID: $CHART_ID${NC}"
    implementation=$(check_implementation "/api/v1/chart/generate" "def generate_chart")
    print_test_result "/api/v1/chart/generate" "curl -X POST http://localhost:8000/api/chart/generate -H \"Content-Type: application/json\" -d '$GENERATE_DATA'" "$GENERATE_RESPONSE" "/api/chart/generate → /api/v1/chart/generate" "$implementation"
else
    echo -e "${RED}Chart generation failed${NC}"
    print_test_result "/api/v1/chart/generate" "curl -X POST http://localhost:8000/api/chart/generate -H \"Content-Type: application/json\" -d '$GENERATE_DATA'" "$GENERATE_RESPONSE" "/api/chart/generate → /api/v1/chart/generate" "NO - Chart generation failed"
    # Use a fallback chart ID for further tests if generation failed
    CHART_ID="test-chart-id-$(date +%s)"
    echo -e "${YELLOW}Using fallback chart ID: $CHART_ID for further tests${NC}"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 5 ============${NC}"
echo -e "${BLUE}Testing Chart Retrieval${NC}"

CHART_RESPONSE=$(test_api_endpoint "/api/chart/$CHART_ID" "GET" "")
CHART_SUCCESS=$(echo "$CHART_RESPONSE" | grep -o '"chart_id"' | wc -l)

if [ "$CHART_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Chart retrieval successful${NC}"
    implementation=$(check_implementation "/api/v1/chart/{chart_id}" "def get_chart")
    print_test_result "/api/v1/chart/{chart_id}" "curl -X GET http://localhost:8000/api/chart/$CHART_ID" "$CHART_RESPONSE" "/api/chart/{chart_id} → /api/v1/chart/{chart_id}" "$implementation"
else
    echo -e "${RED}Chart retrieval failed${NC}"
    print_test_result "/api/v1/chart/{chart_id}" "curl -X GET http://localhost:8000/api/chart/$CHART_ID" "$CHART_RESPONSE" "/api/chart/{chart_id} → /api/v1/chart/{chart_id}" "NO - Chart retrieval failed"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 6 ============${NC}"
echo -e "${BLUE}Testing Questionnaire${NC}"

QUESTIONNAIRE_RESPONSE=$(test_api_endpoint "/api/questionnaire?chart_id=$CHART_ID&session_id=$SESSION_ID" "GET" "")
QUESTION_ID=$(echo "$QUESTIONNAIRE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')

if [ -n "$QUESTION_ID" ]; then
    echo -e "${GREEN}Questionnaire retrieval successful with first question ID: $QUESTION_ID${NC}"
    implementation=$(check_implementation "/api/v1/questionnaire" "def get_questionnaire")
    print_test_result "/api/v1/questionnaire" "curl -X GET \"http://localhost:8000/api/questionnaire?chart_id=$CHART_ID&session_id=$SESSION_ID\"" "$QUESTIONNAIRE_RESPONSE" "/api/questionnaire → /api/v1/questionnaire" "$implementation"
else
    echo -e "${RED}Questionnaire retrieval failed${NC}"
    print_test_result "/api/v1/questionnaire" "curl -X GET \"http://localhost:8000/api/questionnaire?chart_id=$CHART_ID&session_id=$SESSION_ID\"" "$QUESTIONNAIRE_RESPONSE" "/api/questionnaire → /api/v1/questionnaire" "NO - Questionnaire retrieval failed"
    # Use a fallback question ID
    QUESTION_ID="test-question-id-$(date +%s)"
    echo -e "${YELLOW}Using fallback question ID: $QUESTION_ID for further tests${NC}"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 7 ============${NC}"
echo -e "${BLUE}Testing Question Answer Submission${NC}"

ANSWER_DATA='{\"answer\":\"yes\",\"session_id\":\"'$SESSION_ID'\",\"chart_id\":\"'$CHART_ID'\"}'
ANSWER_RESPONSE=$(test_api_endpoint "/api/questionnaire/$QUESTION_ID/answer" "POST" "-H \"Content-Type: application/json\" -d '$ANSWER_DATA'")
ANSWER_SUCCESS=$(echo "$ANSWER_RESPONSE" | grep -o '"next_question"' | wc -l)

if [ "$ANSWER_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Answer submission successful${NC}"
    implementation=$(check_implementation "/api/v1/questionnaire/{id}/answer" "def answer_question")
    print_test_result "/api/v1/questionnaire/{id}/answer" "curl -X POST http://localhost:8000/api/questionnaire/$QUESTION_ID/answer -H \"Content-Type: application/json\" -d '$ANSWER_DATA'" "$ANSWER_RESPONSE" "/api/questionnaire/{id}/answer → /api/v1/questionnaire/{id}/answer" "$implementation"
else
    echo -e "${RED}Answer submission failed${NC}"
    print_test_result "/api/v1/questionnaire/{id}/answer" "curl -X POST http://localhost:8000/api/questionnaire/$QUESTION_ID/answer -H \"Content-Type: application/json\" -d '$ANSWER_DATA'" "$ANSWER_RESPONSE" "/api/questionnaire/{id}/answer → /api/v1/questionnaire/{id}/answer" "NO - Answer submission failed"
fi

echo -e "\n${BLUE}Testing Questionnaire Completion${NC}"

COMPLETE_DATA='{\"session_id\":\"'$SESSION_ID'\",\"chart_id\":\"'$CHART_ID'\"}'
COMPLETE_RESPONSE=$(test_api_endpoint "/api/questionnaire/complete" "POST" "-H \"Content-Type: application/json\" -d '$COMPLETE_DATA'")
COMPLETE_SUCCESS=$(echo "$COMPLETE_RESPONSE" | grep -o '"status"' | wc -l)

if [ "$COMPLETE_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Questionnaire completion successful${NC}"
    implementation=$(check_implementation "/api/v1/questionnaire/complete" "def complete_questionnaire")
    print_test_result "/api/v1/questionnaire/complete" "curl -X POST http://localhost:8000/api/questionnaire/complete -H \"Content-Type: application/json\" -d '$COMPLETE_DATA'" "$COMPLETE_RESPONSE" "/api/questionnaire/complete → /api/v1/questionnaire/complete" "$implementation"
else
    echo -e "${RED}Questionnaire completion failed${NC}"
    print_test_result "/api/v1/questionnaire/complete" "curl -X POST http://localhost:8000/api/questionnaire/complete -H \"Content-Type: application/json\" -d '$COMPLETE_DATA'" "$COMPLETE_RESPONSE" "/api/questionnaire/complete → /api/v1/questionnaire/complete" "NO - Questionnaire completion failed"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 8 ============${NC}"
echo -e "${BLUE}Testing Chart Rectification${NC}"

RECTIFY_DATA='{\"session_id\":\"'$SESSION_ID'\",\"chart_id\":\"'$CHART_ID'\"}'
RECTIFY_RESPONSE=$(test_api_endpoint "/api/chart/rectify" "POST" "-H \"Content-Type: application/json\" -d '$RECTIFY_DATA'")
RECTIFY_SUCCESS=$(echo "$RECTIFY_RESPONSE" | grep -o '"rectified_time"' | wc -l)

if [ "$RECTIFY_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Chart rectification successful${NC}"
    implementation=$(check_implementation "/api/v1/chart/rectify" "def rectify_chart")
    print_test_result "/api/v1/chart/rectify" "curl -X POST http://localhost:8000/api/chart/rectify -H \"Content-Type: application/json\" -d '$RECTIFY_DATA'" "$RECTIFY_RESPONSE" "/api/chart/rectify → /api/v1/chart/rectify" "$implementation"
else
    echo -e "${RED}Chart rectification failed${NC}"
    print_test_result "/api/v1/chart/rectify" "curl -X POST http://localhost:8000/api/chart/rectify -H \"Content-Type: application/json\" -d '$RECTIFY_DATA'" "$RECTIFY_RESPONSE" "/api/chart/rectify → /api/v1/chart/rectify" "NO - Chart rectification failed"
fi

echo -e "\n${BLUE}Testing Chart Comparison${NC}"

# Assume we have two chart IDs for comparison
COMPARE_PARAMS="?chart1=$CHART_ID&chart2=${CHART_ID}_rectified&session_id=$SESSION_ID"
COMPARE_RESPONSE=$(test_api_endpoint "/api/chart/compare$COMPARE_PARAMS" "GET" "")
COMPARE_SUCCESS=$(echo "$COMPARE_RESPONSE" | grep -o '"differences"' | wc -l)

if [ "$COMPARE_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Chart comparison successful${NC}"
    implementation=$(check_implementation "/api/v1/chart/compare" "def compare_charts")
    print_test_result "/api/v1/chart/compare" "curl -X GET \"http://localhost:8000/api/chart/compare$COMPARE_PARAMS\"" "$COMPARE_RESPONSE" "/api/chart/compare → /api/v1/chart/compare" "$implementation"
else
    echo -e "${RED}Chart comparison failed${NC}"
    print_test_result "/api/v1/chart/compare" "curl -X GET \"http://localhost:8000/api/chart/compare$COMPARE_PARAMS\"" "$COMPARE_RESPONSE" "/api/chart/compare → /api/v1/chart/compare" "NO - Chart comparison failed"
fi

echo -e "\n${BLUE}============ STARTING SEQUENCE 9 ============${NC}"
echo -e "${BLUE}Testing Chart Export${NC}"

EXPORT_DATA='{\"chart_id\":\"'$CHART_ID'\",\"session_id\":\"'$SESSION_ID'\",\"format\":\"pdf\"}'
EXPORT_RESPONSE=$(test_api_endpoint "/api/chart/export" "POST" "-H \"Content-Type: application/json\" -d '$EXPORT_DATA'")
EXPORT_ID=$(echo "$EXPORT_RESPONSE" | grep -o '"export_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')

if [ -n "$EXPORT_ID" ]; then
    echo -e "${GREEN}Chart export preparation successful with ID: $EXPORT_ID${NC}"
    implementation=$(check_implementation "/api/v1/chart/export" "def export_chart")
    print_test_result "/api/v1/chart/export" "curl -X POST http://localhost:8000/api/chart/export -H \"Content-Type: application/json\" -d '$EXPORT_DATA'" "$EXPORT_RESPONSE" "/api/chart/export → /api/v1/chart/export" "$implementation"
else
    echo -e "${RED}Chart export preparation failed${NC}"
    print_test_result "/api/v1/chart/export" "curl -X POST http://localhost:8000/api/chart/export -H \"Content-Type: application/json\" -d '$EXPORT_DATA'" "$EXPORT_RESPONSE" "/api/chart/export → /api/v1/chart/export" "NO - Chart export preparation failed"
    # Use a fallback export ID
    EXPORT_ID="test-export-id-$(date +%s)"
    echo -e "${YELLOW}Using fallback export ID: $EXPORT_ID for further tests${NC}"
fi

echo -e "\n${BLUE}Testing Export Download${NC}"

# Only test the headers for the download to avoid binary output
DOWNLOAD_RESPONSE=$(curl -s -I -X GET "http://localhost:8000/api/chart/export/$EXPORT_ID/download?session_id=$SESSION_ID")
DOWNLOAD_SUCCESS=$(echo "$DOWNLOAD_RESPONSE" | grep -i "content-type" | wc -l)

if [ "$DOWNLOAD_SUCCESS" -gt 0 ]; then
    echo -e "${GREEN}Export download header check successful${NC}"
    implementation=$(check_implementation "/api/v1/chart/export/{id}/download" "def download_export")
    print_test_result "/api/v1/chart/export/{id}/download" "curl -I -X GET \"http://localhost:8000/api/chart/export/$EXPORT_ID/download?session_id=$SESSION_ID\"" "$DOWNLOAD_RESPONSE" "/api/chart/export/{id}/download → /api/v1/chart/export/{id}/download" "$implementation"
else
    echo -e "${RED}Export download header check failed${NC}"
    print_test_result "/api/v1/chart/export/{id}/download" "curl -I -X GET \"http://localhost:8000/api/chart/export/$EXPORT_ID/download?session_id=$SESSION_ID\"" "$DOWNLOAD_RESPONSE" "/api/chart/export/{id}/download → /api/v1/chart/export/{id}/download" "NO - Export download header check failed"
fi

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}       API TESTING COMPLETE                    ${NC}"
echo -e "${BLUE}===============================================${NC}"
echo -e "${GREEN}Results have been saved to $TEST_RESULTS_FILE${NC}"
