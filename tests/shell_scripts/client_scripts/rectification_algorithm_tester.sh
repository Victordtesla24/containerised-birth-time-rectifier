#!/bin/bash

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# API Gateway URL
API_URL="http://localhost:3001"
AI_SERVICE_URL="http://localhost:8001"

# Session and chart IDs (will be overridden by command line args or new session)
SESSION_ID=""
CHART_ID=""
RECTIFIED_CHART_ID=""

# Results directory for exports
RESULTS_DIR="rectification_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Confidence threshold
CONFIDENCE_THRESHOLD=90

# Parse command line arguments
for arg in "$@"
do
    case $arg in
        --session=*)
        SESSION_ID="${arg#*=}"
        shift
        ;;
        --chart=*)
        CHART_ID="${arg#*=}"
        shift
        ;;
        --rectified=*)
        RECTIFIED_CHART_ID="${arg#*=}"
        shift
        ;;
        --threshold=*)
        CONFIDENCE_THRESHOLD="${arg#*=}"
        shift
        ;;
        *)
        # Unknown option
        ;;
    esac
done

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}  RECTIFICATION ALGORITHM & INTERPRETATION TEST ${NC}"
echo -e "${BLUE}===============================================${NC}"
echo -e "${YELLOW}Testing with confidence threshold: $CONFIDENCE_THRESHOLD%${NC}"
echo -e "${YELLOW}Results will be saved to: $RESULTS_DIR${NC}"

# Function to check if a server is running
check_server() {
    local url=$1
    local name=$2

    echo -e "\n${YELLOW}Checking if $name is running...${NC}"

    if curl -s --connect-timeout 3 "$url/api/v1/health" > /dev/null; then
        echo -e "${GREEN}✅ $name is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $name is not running${NC}"
        return 1
    fi
}

# Function to execute a test and report results
test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4
    local session_header=""

    if [ -n "$SESSION_ID" ]; then
        session_header="-H 'X-Session-ID: $SESSION_ID'"
    fi

    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo -e "${YELLOW}Endpoint: $endpoint${NC}"
    echo -e "${YELLOW}Method: $method${NC}"

    if [ -n "$data" ]; then
        echo -e "${YELLOW}Data: $data${NC}"
    fi

    # Build curl command
    local cmd="curl -s -w '\n%{http_code}' -X $method"

    # Add headers and data if applicable
    if [ "$method" == "POST" ] || [ "$method" == "PUT" ]; then
        cmd="$cmd -H 'Content-Type: application/json'"
        if [ -n "$session_header" ]; then
            cmd="$cmd $session_header"
        fi
        if [ -n "$data" ]; then
            cmd="$cmd -d '$data'"
        fi
    else
        if [ -n "$session_header" ]; then
            cmd="$cmd $session_header"
        fi
    fi

    # Add the endpoint
    cmd="$cmd $API_URL$endpoint"

    echo -e "${YELLOW}Command: $cmd${NC}"

    # Execute curl and capture response and status code
    response=$(eval $cmd)
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    # Save the response to a file for detailed analysis
    local filename=$(echo "$description" | tr ' ' '_' | tr -d '[:punct:]')
    echo "$body" > "$RESULTS_DIR/${filename}.json"

    # Check if status code indicates success (2xx)
    if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
        echo -e "${GREEN}SUCCESS (Status $status_code)${NC}"
        echo -e "${GREEN}Response saved to: $RESULTS_DIR/${filename}.json${NC}"
        echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
        # Return body for parsing, but filter out any console output
        echo "$body" | grep -v "SUCCESS" | grep -v "Command" | grep -v "Method" | grep -v "Endpoint"
        return 0
    else
        echo -e "${RED}FAILED (Status $status_code)${NC}"
        echo -e "${RED}Error response saved to: $RESULTS_DIR/${filename}_error.json${NC}"
        echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
        return 1
    fi
}

# Function to extract OpenAI verification information from chart data
extract_verification_info() {
    local chart_data=$1
    local chart_type=$2

    # Extract verification information
    local verified=$(echo "$chart_data" | grep -o '"verified":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    local confidence=$(echo "$chart_data" | grep -o '"confidence_score":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    local corrections=$(echo "$chart_data" | grep -o '"corrections_applied":[^,]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    local message=$(echo "$chart_data" | grep -o '"message":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')
    local method=$(echo "$chart_data" | grep -o '"verification_method":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')

    echo -e "\n${CYAN}=== OpenAI Chart $chart_type Verification Results ===${NC}"
    echo -e "${CYAN}Verified: $verified${NC}"
    echo -e "${CYAN}Confidence Score: $confidence${NC}"
    echo -e "${CYAN}Corrections Applied: $corrections${NC}"
    echo -e "${CYAN}Message: $message${NC}"
    echo -e "${CYAN}Method: $method${NC}"

    # Save verification info to file
    echo "Chart Type: $chart_type" > "$RESULTS_DIR/verification_${chart_type}.txt"
    echo "Verified: $verified" >> "$RESULTS_DIR/verification_${chart_type}.txt"
    echo "Confidence Score: $confidence" >> "$RESULTS_DIR/verification_${chart_type}.txt"
    echo "Corrections Applied: $corrections" >> "$RESULTS_DIR/verification_${chart_type}.txt"
    echo "Message: $message" >> "$RESULTS_DIR/verification_${chart_type}.txt"
    echo "Method: $method" >> "$RESULTS_DIR/verification_${chart_type}.txt"

    # Return the confidence score
    echo $confidence
}

# Function to generate a summary of planetary positions for a chart
generate_planet_summary() {
    local chart_data=$1
    local chart_type=$2

    local summary_file="$RESULTS_DIR/planet_summary_${chart_type}.txt"

    echo -e "\n${MAGENTA}=== Planetary Positions for $chart_type Chart ===${NC}"
    echo "Planetary Positions for $chart_type Chart" > "$summary_file"
    echo "Generated at: $(date)" >> "$summary_file"
    echo "----------------------------------------" >> "$summary_file"

    # Extract ascendant info
    local asc_lon=$(echo "$chart_data" | grep -o '"ascendant":{[^}]*}' | grep -o '"longitude":[^,]*' | cut -d':' -f2 | tr -d ' ')
    local asc_sign=$(echo "$chart_data" | grep -o '"ascendant":{[^}]*}' | grep -o '"sign":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    local asc_degree=$(echo "$chart_data" | grep -o '"ascendant":{[^}]*}' | grep -o '"degree":[^,}]*' | cut -d':' -f2 | tr -d ' ')

    echo -e "${MAGENTA}Ascendant: ${asc_sign} ${asc_degree}° (${asc_lon})${NC}"
    echo "Ascendant: ${asc_sign} ${asc_degree}° (${asc_lon})" >> "$summary_file"

    # Extract MC info
    local mc_lon=$(echo "$chart_data" | grep -o '"mc":{[^}]*}' | grep -o '"longitude":[^,]*' | cut -d':' -f2 | tr -d ' ')
    local mc_sign=$(echo "$chart_data" | grep -o '"mc":{[^}]*}' | grep -o '"sign":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    local mc_degree=$(echo "$chart_data" | grep -o '"mc":{[^}]*}' | grep -o '"degree":[^,}]*' | cut -d':' -f2 | tr -d ' ')

    echo -e "${MAGENTA}Midheaven: ${mc_sign} ${mc_degree}° (${mc_lon})${NC}"
    echo "Midheaven: ${mc_sign} ${mc_degree}° (${mc_lon})" >> "$summary_file"

    echo "----------------------------------------" >> "$summary_file"
    echo "Planets:" >> "$summary_file"

    # Extract each planet's info
    local planets=$(echo "$chart_data" | grep -o '"planets":{[^}]*}}' | sed 's/"planets":{//')
    local planet_ids=("0" "1" "2" "3" "4" "5" "6" "7" "8" "9" "10" "12")
    local planet_names=("Sun" "Moon" "Mercury" "Venus" "Mars" "Jupiter" "Saturn" "Uranus" "Neptune" "Pluto" "Rahu" "Ketu")

    echo -e "${MAGENTA}Planets:${NC}"

    for i in "${!planet_ids[@]}"; do
        id="${planet_ids[$i]}"
        name="${planet_names[$i]}"

        # Extract planet data
        planet_data=$(echo "$planets" | grep -o "\"$id\":{[^}]*}" || echo "")

        if [ -n "$planet_data" ]; then
            lon=$(echo "$planet_data" | grep -o '"longitude":[^,]*' | cut -d':' -f2 | tr -d ' ')
            sign=$(echo "$planet_data" | grep -o '"sign":"[^"]*"' | cut -d':' -f2 | tr -d '"')
            degree=$(echo "$planet_data" | grep -o '"degree":[^,}]*' | cut -d':' -f2 | tr -d ' ')
            house=$(echo "$planet_data" | grep -o '"house":[^,}]*' | cut -d':' -f2 | tr -d ' ')

            echo -e "${MAGENTA}${name}: ${sign} ${degree}° (${lon}) House: ${house}${NC}"
            echo "${name}: ${sign} ${degree}° (${lon}) House: ${house}" >> "$summary_file"
        fi
    done

    echo -e "\n${GREEN}Planetary summary saved to ${summary_file}${NC}"
}

# Function to analyze chart comparison and highlight key differences
analyze_chart_comparison() {
    local comparison_data=$1
    local summary_file="$RESULTS_DIR/comparison_analysis.txt"

    echo -e "\n${BLUE}=== Chart Comparison Analysis ===${NC}"
    echo "Chart Comparison Analysis" > "$summary_file"
    echo "Generated at: $(date)" >> "$summary_file"
    echo "----------------------------------------" >> "$summary_file"

    # Extract comparison data
    local original_time=$(echo "$comparison_data" | grep -o '"original_time":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    local rectified_time=$(echo "$comparison_data" | grep -o '"rectified_time":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    local time_diff=$(echo "$comparison_data" | grep -o '"time_difference_minutes":[^,}]*' | cut -d':' -f2 | tr -d ' ')
    local similarity=$(echo "$comparison_data" | grep -o '"similarity_score":[^,}]*' | cut -d':' -f2 | tr -d ' ')
    local confidence=$(echo "$comparison_data" | grep -o '"confidence":[^,}]*' | cut -d':' -f2 | tr -d ' ')

    echo -e "${BLUE}Original Time: ${original_time}${NC}"
    echo -e "${BLUE}Rectified Time: ${rectified_time}${NC}"
    echo -e "${BLUE}Time Difference: ${time_diff} minutes${NC}"
    echo -e "${BLUE}Similarity Score: ${similarity}%${NC}"
    echo -e "${BLUE}Confidence: ${confidence}%${NC}"

    echo "Original Time: ${original_time}" >> "$summary_file"
    echo "Rectified Time: ${rectified_time}" >> "$summary_file"
    echo "Time Difference: ${time_diff} minutes" >> "$summary_file"
    echo "Similarity Score: ${similarity}%" >> "$summary_file"
    echo "Confidence: ${confidence}%" >> "$summary_file"

    echo "----------------------------------------" >> "$summary_file"
    echo "Key Differences:" >> "$summary_file"

    # Extract differences for key points
    local differences=$(echo "$comparison_data" | grep -o '"differences":\[.*\]' | sed 's/"differences":\[//' | sed 's/\]$//')

    # Parse and display differences
    echo -e "${YELLOW}Key Differences:${NC}"
    while read -r diff; do
        element=$(echo "$diff" | grep -o '"element":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        type=$(echo "$diff" | grep -o '"type":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        original=$(echo "$diff" | grep -o '"original":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        rectified=$(echo "$diff" | grep -o '"rectified":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        impact=$(echo "$diff" | grep -o '"impact":[^,}]*' | cut -d':' -f2 | tr -d ' ')

        echo -e "${YELLOW}Element: ${element} (${type})${NC}"
        echo -e "${YELLOW}  Original: ${original}${NC}"
        echo -e "${YELLOW}  Rectified: ${rectified}${NC}"
        echo -e "${YELLOW}  Impact: ${impact}${NC}"

        echo "Element: ${element} (${type})" >> "$summary_file"
        echo "  Original: ${original}" >> "$summary_file"
        echo "  Rectified: ${rectified}" >> "$summary_file"
        echo "  Impact: ${impact}" >> "$summary_file"
        echo "" >> "$summary_file"
    done < <(echo "$differences" | grep -o '{[^}]*}')

    # Extract interpretation summary
    local interpretation=$(echo "$comparison_data" | grep -o '"interpretation":"[^"]*"' | cut -d':' -f2 | tr -d '"')

    echo -e "\n${GREEN}Interpretation Summary:${NC}"
    echo -e "${GREEN}${interpretation}${NC}"

    echo "----------------------------------------" >> "$summary_file"
    echo "Interpretation Summary:" >> "$summary_file"
    echo "${interpretation}" >> "$summary_file"

    echo -e "\n${GREEN}Comparison analysis saved to ${summary_file}${NC}"
}

# Function to analyze interpretation results
analyze_interpretation() {
    local interpretation_data=$1
    local chart_type=$2
    local summary_file="$RESULTS_DIR/interpretation_${chart_type}.txt"

    echo -e "\n${CYAN}=== Chart Interpretation Analysis for ${chart_type} Chart ===${NC}"
    echo "Chart Interpretation Analysis for ${chart_type} Chart" > "$summary_file"
    echo "Generated at: $(date)" >> "$summary_file"
    echo "----------------------------------------" >> "$summary_file"

    # Extract overall interpretation
    local overall=$(echo "$interpretation_data" | grep -o '"overall":"[^"]*"' | cut -d':' -f2 | tr -d '"')

    echo -e "${CYAN}Overall Interpretation:${NC}"
    echo -e "${CYAN}${overall}${NC}"

    echo "Overall Interpretation:" >> "$summary_file"
    echo "${overall}" >> "$summary_file"

    echo "----------------------------------------" >> "$summary_file"
    echo "Detailed Analysis:" >> "$summary_file"

    # Extract sections
    local sections=$(echo "$interpretation_data" | grep -o '"sections":\[.*\]' | sed 's/"sections":\[//' | sed 's/\]$//')

    # Parse and display sections
    echo -e "\n${CYAN}Detailed Analysis:${NC}"
    while read -r section; do
        title=$(echo "$section" | grep -o '"title":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        content=$(echo "$section" | grep -o '"content":"[^"]*"' | cut -d':' -f2 | tr -d '"')

        echo -e "${CYAN}${title}:${NC}"
        echo -e "${content}"

        echo "${title}:" >> "$summary_file"
        echo "${content}" >> "$summary_file"
        echo "" >> "$summary_file"
    done < <(echo "$sections" | grep -o '{[^}]*}')

    echo -e "\n${GREEN}Interpretation analysis saved to ${summary_file}${NC}"
}

# Step 1: Check if servers are running
check_server "$API_URL" "API Gateway" || { echo -e "${RED}API Gateway must be running. Exiting.${NC}"; exit 1; }
check_server "$AI_SERVICE_URL" "AI Service" || { echo -e "${RED}AI Service must be running. Exiting.${NC}"; exit 1; }

# Step 2: Create session if not provided
if [ -z "$SESSION_ID" ]; then
    echo -e "\n${BLUE}=== Creating New Session ===${NC}"
    SESSION_RESPONSE=$(test_endpoint "/api/v1/session/init" "GET" "" "Session Initialization")
    SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

    if [ -n "$SESSION_ID" ]; then
        echo -e "${GREEN}Session created with ID: $SESSION_ID${NC}"
    else
        echo -e "${RED}Failed to create session${NC}"
        SESSION_ID="fallback-session-$(date +%s)"
        echo -e "${YELLOW}Using fallback session ID: $SESSION_ID${NC}"
    fi
else
    echo -e "\n${GREEN}Using provided Session ID: $SESSION_ID${NC}"
fi

# Step 3: Run the OpenAI integration script to generate chart and rectified chart if not provided
if [ -z "$CHART_ID" ] || [ -z "$RECTIFIED_CHART_ID" ]; then
    echo -e "\n${BLUE}=== Running OpenAI Integration Tester to Generate Charts ===${NC}"
    echo -e "${YELLOW}This will create original and rectified charts with a confidence threshold of $CONFIDENCE_THRESHOLD%${NC}"

    # Define command
    OPENAI_CMD="./openai_integration_tester.sh --session=$SESSION_ID --threshold=$CONFIDENCE_THRESHOLD"

    # Run OpenAI integration script
    OPENAI_OUTPUT=$(eval $OPENAI_CMD)

    # Save output to file
    echo "$OPENAI_OUTPUT" > "$RESULTS_DIR/openai_integration.log"
    echo -e "${GREEN}OpenAI Integration output saved to $RESULTS_DIR/openai_integration.log${NC}"

    # Extract chart IDs from output
    if [ -z "$CHART_ID" ]; then
        CHART_ID=$(echo "$OPENAI_OUTPUT" | grep "Original Chart ID:" | head -1 | cut -d':' -f2 | tr -d ' ')
        if [ -n "$CHART_ID" ]; then
            echo -e "${GREEN}Extracted Original Chart ID: $CHART_ID${NC}"
        else
            echo -e "${RED}Failed to extract Original Chart ID${NC}"
            exit 1
        fi
    fi

    if [ -z "$RECTIFIED_CHART_ID" ]; then
        RECTIFIED_CHART_ID=$(echo "$OPENAI_OUTPUT" | grep "Rectified Chart ID:" | head -1 | cut -d':' -f2 | tr -d ' ')
        if [ -n "$RECTIFIED_CHART_ID" ]; then
            echo -e "${GREEN}Extracted Rectified Chart ID: $RECTIFIED_CHART_ID${NC}"
        else
            echo -e "${RED}Failed to extract Rectified Chart ID${NC}"
            exit 1
        fi
    fi
else
    echo -e "\n${GREEN}Using provided Chart IDs:${NC}"
    echo -e "${GREEN}Original Chart ID: $CHART_ID${NC}"
    echo -e "${GREEN}Rectified Chart ID: $RECTIFIED_CHART_ID${NC}"
fi

# Step 4: Retrieve detailed chart data
echo -e "\n${BLUE}=== Retrieving Original Chart Details ===${NC}"
CHART_ENDPOINT="/api/v1/chart/$CHART_ID"
CHART_RESPONSE=$(test_endpoint "$CHART_ENDPOINT" "GET" "" "Original Chart Details")

if [ -n "$CHART_RESPONSE" ]; then
    # Extract birth details
    BIRTH_DATE=$(echo "$CHART_RESPONSE" | grep -o '"date":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    BIRTH_TIME=$(echo "$CHART_RESPONSE" | grep -o '"time":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    LATITUDE=$(echo "$CHART_RESPONSE" | grep -o '"latitude":[^,}]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    LONGITUDE=$(echo "$CHART_RESPONSE" | grep -o '"longitude":[^,}]*' | head -1 | cut -d':' -f2 | tr -d ' ')
    TIMEZONE=$(echo "$CHART_RESPONSE" | grep -o '"timezone":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"')

    echo -e "${GREEN}Birth Details:${NC}"
    echo -e "${GREEN}Date: $BIRTH_DATE${NC}"
    echo -e "${GREEN}Time: $BIRTH_TIME${NC}"
    echo -e "${GREEN}Coordinates: $LATITUDE, $LONGITUDE${NC}"
    echo -e "${GREEN}Timezone: $TIMEZONE${NC}"

    # Extract and display OpenAI verification info
    extract_verification_info "$CHART_RESPONSE" "original"

    # Generate planetary summary
    generate_planet_summary "$CHART_RESPONSE" "original"
else
    echo -e "${RED}Failed to retrieve original chart${NC}"
    exit 1
fi

echo -e "\n${BLUE}=== Retrieving Rectified Chart Details ===${NC}"
RECTIFIED_CHART_ENDPOINT="/api/v1/chart/$RECTIFIED_CHART_ID"
RECTIFIED_CHART_RESPONSE=$(test_endpoint "$RECTIFIED_CHART_ENDPOINT" "GET" "" "Rectified Chart Details")

if [ -n "$RECTIFIED_CHART_RESPONSE" ]; then
    # Extract and display OpenAI verification info
    extract_verification_info "$RECTIFIED_CHART_RESPONSE" "rectified"

    # Generate planetary summary
    generate_planet_summary "$RECTIFIED_CHART_RESPONSE" "rectified"
else
    echo -e "${RED}Failed to retrieve rectified chart${NC}"
    exit 1
fi

# Step 5: Test chart comparison with detailed analysis
echo -e "\n${BLUE}=== Testing Detailed Chart Comparison ===${NC}"
COMPARE_ENDPOINT="/api/v1/chart/compare?chart1=$CHART_ID&chart2=$RECTIFIED_CHART_ID&detailed=true"
COMPARE_RESPONSE=$(test_endpoint "$COMPARE_ENDPOINT" "GET" "" "Detailed Chart Comparison")

if [ -n "$COMPARE_RESPONSE" ]; then
    # Analyze chart comparison results
    analyze_chart_comparison "$COMPARE_RESPONSE"
else
    echo -e "${RED}Failed to compare charts${NC}"
fi

# Step 6: Test interpretation endpoints for both charts
echo -e "\n${BLUE}=== Testing Chart Interpretation (Original) ===${NC}"
INTERPRETATION_ENDPOINT="/api/v1/chart/interpret/$CHART_ID"
INTERPRETATION_RESPONSE=$(test_endpoint "$INTERPRETATION_ENDPOINT" "GET" "" "Original Chart Interpretation")

if [ -n "$INTERPRETATION_RESPONSE" ]; then
    # Analyze interpretation results
    analyze_interpretation "$INTERPRETATION_RESPONSE" "original"
else
    echo -e "${RED}Failed to get original chart interpretation${NC}"
fi

echo -e "\n${BLUE}=== Testing Chart Interpretation (Rectified) ===${NC}"
RECTIFIED_INTERPRETATION_ENDPOINT="/api/v1/chart/interpret/$RECTIFIED_CHART_ID"
RECTIFIED_INTERPRETATION_RESPONSE=$(test_endpoint "$RECTIFIED_INTERPRETATION_ENDPOINT" "GET" "" "Rectified Chart Interpretation")

if [ -n "$RECTIFIED_INTERPRETATION_RESPONSE" ]; then
    # Analyze interpretation results
    analyze_interpretation "$RECTIFIED_INTERPRETATION_RESPONSE" "rectified"
else
    echo -e "${RED}Failed to get rectified chart interpretation${NC}"
fi

# Step 7: Test birth time rectification algorithm details
echo -e "\n${BLUE}=== Testing Rectification Algorithm Details ===${NC}"
ALGORITHM_ENDPOINT="/api/v1/chart/rectification-details/$RECTIFIED_CHART_ID"
ALGORITHM_RESPONSE=$(test_endpoint "$ALGORITHM_ENDPOINT" "GET" "" "Rectification Algorithm Details")

if [ -n "$ALGORITHM_RESPONSE" ]; then
    # Extract algorithm details
    local algorithm_file="$RESULTS_DIR/rectification_algorithm_details.txt"
    local algorithm_name=$(echo "$ALGORITHM_RESPONSE" | grep -o '"algorithm":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    local score=$(echo "$ALGORITHM_RESPONSE" | grep -o '"score":[^,}]*' | cut -d':' -f2 | tr -d ' ')
    local techniques=$(echo "$ALGORITHM_RESPONSE" | grep -o '"techniques":\[.*\]' | sed 's/"techniques":\[//' | sed 's/\]$//')

    echo -e "${MAGENTA}=== Rectification Algorithm Details ===${NC}"
    echo -e "${MAGENTA}Algorithm: $algorithm_name${NC}"
    echo -e "${MAGENTA}Confidence Score: $score${NC}"

    echo "Rectification Algorithm Details" > "$algorithm_file"
    echo "Generated at: $(date)" >> "$algorithm_file"
    echo "----------------------------------------" >> "$algorithm_file"
    echo "Algorithm: $algorithm_name" >> "$algorithm_file"
    echo "Confidence Score: $score" >> "$algorithm_file"
    echo "----------------------------------------" >> "$algorithm_file"
    echo "Techniques Used:" >> "$algorithm_file"

    # Parse and display techniques
    echo -e "${MAGENTA}Techniques Used:${NC}"
    while read -r technique; do
        name=$(echo "$technique" | grep -o '"name":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        description=$(echo "$technique" | grep -o '"description":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        weight=$(echo "$technique" | grep -o '"weight":[^,}]*' | cut -d':' -f2 | tr -d ' ')

        echo -e "${MAGENTA}${name} (Weight: ${weight}):${NC}"
        echo -e "${MAGENTA}  ${description}${NC}"

        echo "${name} (Weight: ${weight}):" >> "$algorithm_file"
        echo "  ${description}" >> "$algorithm_file"
        echo "" >> "$algorithm_file"
    done < <(echo "$techniques" | grep -o '{[^}]*}')

    echo -e "\n${GREEN}Algorithm details saved to ${algorithm_file}${NC}"
else
    echo -e "${RED}Failed to get rectification algorithm details${NC}"
fi

# Step 8: Test chart export functionality
echo -e "\n${BLUE}=== Testing Chart Export Functionality ===${NC}"
echo -e "${YELLOW}Select export format:${NC}"
echo -e "1) PDF"
echo -e "2) JSON"
echo -e "3) PNG"

read -p "Enter format (1-3): " FORMAT_CHOICE

case $FORMAT_CHOICE in
    1)
        format="pdf"
        ;;
    2)
        format="json"
        ;;
    3)
        format="png"
        ;;
    *)
        echo -e "${RED}Invalid choice. Using PDF as default.${NC}"
        format="pdf"
        ;;
esac

# Original chart export
echo -e "\n${BLUE}=== Exporting Original Chart ($format) ===${NC}"
EXPORT_DATA="{\"chart_id\":\"$CHART_ID\",\"session_id\":\"$SESSION_ID\",\"format\":\"$format\"}"
EXPORT_ENDPOINT="/api/v1/chart/export"
EXPORT_RESPONSE=$(test_endpoint "$EXPORT_ENDPOINT" "POST" "$EXPORT_DATA" "Export Original Chart")

if [ -n "$EXPORT_RESPONSE" ]; then
    # Extract export ID
    EXPORT_ID=$(echo "$EXPORT_RESPONSE" | grep -o '"export_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

    if [ -n "$EXPORT_ID" ]; then
        echo -e "${GREEN}Original chart export ID: $EXPORT_ID${NC}"

        # Download the exported original chart
        DOWNLOAD_ENDPOINT="/api/v1/chart/export/$EXPORT_ID/download"
        DOWNLOAD_CMD="curl -s -o $RESULTS_DIR/original_chart.$format $API_URL$DOWNLOAD_ENDPOINT"
        echo -e "${YELLOW}Command: $DOWNLOAD_CMD${NC}"
        eval $DOWNLOAD_CMD

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully downloaded original chart to $RESULTS_DIR/original_chart.$format${NC}"
        else
            echo -e "${RED}Failed to download original chart${NC}"
        fi
    else
        echo -e "${RED}Failed to get export ID for original chart${NC}"
    fi
else
    echo -e "${RED}Failed to export original chart${NC}"
fi

# Rectified chart export
echo -e "\n${BLUE}=== Exporting Rectified Chart ($format) ===${NC}"
EXPORT_DATA="{\"chart_id\":\"$RECTIFIED_CHART_ID\",\"session_id\":\"$SESSION_ID\",\"format\":\"$format\"}"
EXPORT_ENDPOINT="/api/v1/chart/export"
EXPORT_RESPONSE=$(test_endpoint "$EXPORT_ENDPOINT" "POST" "$EXPORT_DATA" "Export Rectified Chart")

if [ -n "$EXPORT_RESPONSE" ]; then
    # Extract export ID
    EXPORT_ID=$(echo "$EXPORT_RESPONSE" | grep -o '"export_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

    if [ -n "$EXPORT_ID" ]; then
        echo -e "${GREEN}Rectified chart export ID: $EXPORT_ID${NC}"

        # Download the exported rectified chart
        DOWNLOAD_ENDPOINT="/api/v1/chart/export/$EXPORT_ID/download"
        DOWNLOAD_CMD="curl -s -o $RESULTS_DIR/rectified_chart.$format $API_URL$DOWNLOAD_ENDPOINT"
        echo -e "${YELLOW}Command: $DOWNLOAD_CMD${NC}"
        eval $DOWNLOAD_CMD

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully downloaded rectified chart to $RESULTS_DIR/rectified_chart.$format${NC}"
        else
            echo -e "${RED}Failed to download rectified chart${NC}"
        fi
    else
        echo -e "${RED}Failed to get export ID for rectified chart${NC}"
    fi
else
    echo -e "${RED}Failed to export rectified chart${NC}"
fi

# Step 9: Test comparison export functionality
echo -e "\n${BLUE}=== Exporting Chart Comparison ===${NC}"
COMPARE_EXPORT_DATA="{\"chart1_id\":\"$CHART_ID\",\"chart2_id\":\"$RECTIFIED_CHART_ID\",\"session_id\":\"$SESSION_ID\",\"format\":\"$format\"}"
COMPARE_EXPORT_ENDPOINT="/api/v1/chart/export-comparison"
COMPARE_EXPORT_RESPONSE=$(test_endpoint "$COMPARE_EXPORT_ENDPOINT" "POST" "$COMPARE_EXPORT_DATA" "Export Chart Comparison")

if [ -n "$COMPARE_EXPORT_RESPONSE" ]; then
    # Extract export ID
    COMPARE_EXPORT_ID=$(echo "$COMPARE_EXPORT_RESPONSE" | grep -o '"export_id":"[^"]*"' | head -1 | cut -d':' -f2 | tr -d '"' | tr -d ',')

    if [ -n "$COMPARE_EXPORT_ID" ]; then
        echo -e "${GREEN}Comparison export ID: $COMPARE_EXPORT_ID${NC}"

        # Download the exported comparison
        DOWNLOAD_ENDPOINT="/api/v1/chart/export/$COMPARE_EXPORT_ID/download"
        DOWNLOAD_CMD="curl -s -o $RESULTS_DIR/chart_comparison.$format $API_URL$DOWNLOAD_ENDPOINT"
        echo -e "${YELLOW}Command: $DOWNLOAD_CMD${NC}"
        eval $DOWNLOAD_CMD

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully downloaded chart comparison to $RESULTS_DIR/chart_comparison.$format${NC}"
        else
            echo -e "${RED}Failed to download chart comparison${NC}"
        fi
    else
        echo -e "${RED}Failed to get export ID for chart comparison${NC}"
    fi
else
    echo -e "${RED}Failed to export chart comparison${NC}"
fi

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}    RECTIFICATION ALGORITHM TEST COMPLETE      ${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "\n${YELLOW}Test Summary:${NC}"
echo -e "Session ID: $SESSION_ID"
echo -e "Original Chart ID: $CHART_ID"
echo -e "Rectified Chart ID: $RECTIFIED_CHART_ID"
echo -e "All results and exports saved to: $RESULTS_DIR/"

echo -e "\n${GREEN}To view all the test results:${NC}"
echo -e "${GREEN}cd $RESULTS_DIR${NC}"
echo -e "${GREEN}ls -la${NC}"
