#!/bin/bash

# Main entry point for the modular test script
# This script orchestrates the testing process for the Birth Time Rectifier API

# Get the directory of this script
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Set API and WebSocket URLs
API_URL="http://localhost:9000/api/v1"
WS_URL="ws://localhost:9000/ws"

# Source configuration
# Check if test_scripts/config exists, otherwise use current dir
if [ -d "test_scripts/config" ]; then
  source "test_scripts/config/defaults.conf"
elif [ -d "$SCRIPT_DIR/config" ]; then
  source "$SCRIPT_DIR/config/defaults.conf"
else
  echo "Error: Cannot find config directory"
  exit 1
fi

# Source library modules from test_scripts/lib
if [ -d "test_scripts/lib" ]; then
  source "test_scripts/lib/common.sh"
  source "test_scripts/lib/api_client.sh"
  source "test_scripts/lib/websocket_client.sh"
  source "test_scripts/lib/chart_operations.sh"
  source "test_scripts/lib/questionnaire_operations.sh"
  source "test_scripts/lib/validation.sh"
else
  echo "Error: Cannot find test_scripts/lib directory"
  exit 1
fi

# Print banner
print_banner() {

  echo -e "${BOLD}${CYAN}"
  echo -e "========================================================"
  echo -e "               Birth Time Rectifier Test Runner         "
  echo -e "========================================================"
  echo -e "${NC}"
  echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
  echo -e "API URL: ${BLUE}${API_URL}${NC}"
  echo -e "WebSocket URL: ${BLUE}${WS_URL}${NC}"
  echo -e "Log File: ${LOG_FILE}"
  echo -e ""
}

# Function to validate API service health
check_api_health() {
  log_message "INFO" "Checking API health..."

  local health_response=$(curl -s "$API_URL/health")

  if [[ -z "$health_response" ]]; then
    log_message "ERROR" "API health check failed: No response from server"
    return 1
  fi

  if echo "$health_response" | jq -e '.status' > /dev/null; then
    local status=$(echo "$health_response" | jq -r '.status')
    if [[ "$status" == "healthy" ]]; then
      log_message "INFO" "API is healthy: $(echo "$health_response" | jq -r '.service') - $(echo "$health_response" | jq -r '.timestamp')"

      # Display GPU information if available
      if echo "$health_response" | jq -e '.gpu' > /dev/null; then
        log_message "INFO" "GPU: $(echo "$health_response" | jq -r '.gpu.device // "N/A"') - $(echo "$health_response" | jq -r '.gpu.message // "N/A"')"
      fi

      return 0
    else
      log_message "ERROR" "API health check failed: Status is '$status'"
      return 1
    fi
  else
    log_message "ERROR" "API health check failed: Invalid health response format"
    return 1
  fi
}

# Interactive function to get birth details from the user with enhanced UI
get_birth_details() {
  # Title and introduction with styling
  echo -e "\n${BOLD}${CYAN}┌───────────────────────────────────────────────────┐${NC}"
  echo -e "${BOLD}${CYAN}│           BIRTH CHART DETAILS INPUT                │${NC}"
  echo -e "${BOLD}${CYAN}└───────────────────────────────────────────────────┘${NC}\n"

  echo -e "${CYAN}Please provide the following details for accurate chart calculation:${NC}"
  echo -e "${CYAN}All fields marked with ${RED}*${NC} ${CYAN}are required${NC}"
  echo -e "${CYAN}Tips will be provided for each field${NC}\n"

  # Get name with proper validation
  local valid_name=false
  local name=""
  while [[ "$valid_name" != "true" ]]; do
    echo -e "\n${YELLOW}┌─ PERSONAL DETAILS ───────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  This information helps personalize your chart        │${NC}"
    echo -e "${YELLOW}└───────────────────────────────────────────────────────┘${NC}\n"

    echo -e "${BOLD}${RED}*${NC} ${BOLD}FULL NAME:${NC}"
    echo -e "  ${CYAN}• Enter your full birth name if possible${NC}"
    echo -e "  ${CYAN}• This name will appear on your chart and reports${NC}"
    read -p "  → " name

    if [[ -z "$name" ]]; then
      echo -e "  ${RED}× Name cannot be empty${NC}"
      echo -e "  ${YELLOW}ℹ️ Your name is used to identify your chart in the system${NC}"
      continue
    elif [[ ${#name} -lt 2 ]]; then
      echo -e "  ${RED}× Name must be at least 2 characters${NC}"
      continue
    fi

    echo -e "  ${GREEN}✓ Name accepted${NC}"
    valid_name=true
  done

  # Get birth date with validation
  local valid_date=false
  local birth_date=""
  while [[ "$valid_date" != "true" ]]; do
    echo -e "\n${YELLOW}┌─ BIRTH DATE ──────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  The exact date you were born is crucial for accuracy  │${NC}"
    echo -e "${YELLOW}└───────────────────────────────────────────────────────┘${NC}\n"

    echo -e "${BOLD}${RED}*${NC} ${BOLD}DATE OF BIRTH:${NC} ${CYAN}(Format: YYYY-MM-DD)${NC}"
    echo -e "  ${CYAN}• Example: 1990-05-21 for May 21, 1990${NC}"
    echo -e "  ${CYAN}• This determines your Sun sign and other planetary positions${NC}"
    echo -e "  ${CYAN}• Enter the date as it appears on your birth certificate${NC}"
    read -p "  → " birth_date

    # Validate date format
    if [[ ! "$birth_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
      echo -e "  ${RED}× Invalid date format. Please use YYYY-MM-DD format${NC}"
      echo -e "  ${YELLOW}ℹ️ Four-digit year, then month (01-12), then day (01-31)${NC}"
      continue
    fi

    # Additional validation for realistic values
    local year=$(echo "$birth_date" | cut -d'-' -f1)
    local month=$(echo "$birth_date" | cut -d'-' -f2)
    local day=$(echo "$birth_date" | cut -d'-' -f3)

    if [[ $year -lt 1900 || $year -gt $(date +%Y) ]]; then
      echo -e "  ${RED}× Year must be between 1900 and $(date +%Y)${NC}"
      continue
    fi

    if [[ $month -lt 1 || $month -gt 12 ]]; then
      echo -e "  ${RED}× Month must be between 01 and 12${NC}"
      continue
    fi

    # Simple day validation (not accounting for month-specific days)
    if [[ $day -lt 1 || $day -gt 31 ]]; then
      echo -e "  ${RED}× Day must be between 01 and 31${NC}"
      continue
    fi

    echo -e "  ${GREEN}✓ Birth date accepted${NC}"
    valid_date=true
  done

  # Get birth time with validation
  local valid_time=false
  local birth_time=""
  while [[ "$valid_time" != "true" ]]; do
    echo -e "\n${YELLOW}┌─ BIRTH TIME ──────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  The time you were born defines your Ascendant and    │${NC}"
    echo -e "${YELLOW}│  house placements - critical for accurate readings    │${NC}"
    echo -e "${YELLOW}└───────────────────────────────────────────────────────┘${NC}\n"

    echo -e "${BOLD}${RED}*${NC} ${BOLD}TIME OF BIRTH:${NC} ${CYAN}(Format: HH:MM 24-hour format)${NC}"
    echo -e "  ${CYAN}• Example: 14:30 for 2:30 PM or 09:15 for 9:15 AM${NC}"
    echo -e "  ${CYAN}• If you don't know your exact birth time, use your best estimate${NC}"
    echo -e "  ${CYAN}• The birth time rectification process can help refine this later${NC}"
    read -p "  → " birth_time

    # Validate time format
    if [[ ! "$birth_time" =~ ^[0-9]{2}:[0-9]{2}$ ]]; then
      echo -e "  ${RED}× Invalid time format. Please use HH:MM format${NC}"
      echo -e "  ${YELLOW}ℹ️ Hours (00-23), then minutes (00-59)${NC}"
      continue
    fi

    # Additional validation for realistic values
    local hour=$(echo "$birth_time" | cut -d':' -f1)
    local minute=$(echo "$birth_time" | cut -d':' -f2)

    if [[ $hour -lt 0 || $hour -gt 23 ]]; then
      echo -e "  ${RED}× Hour must be between 00 and 23${NC}"
      echo -e "  ${YELLOW}ℹ️ Use 24-hour format (14 for 2 PM, 00 for midnight)${NC}"
      continue
    fi

    if [[ $minute -lt 0 || $minute -gt 59 ]]; then
      echo -e "  ${RED}× Minute must be between 00 and 59${NC}"
      continue
    fi

    # Add seconds for API compatibility
    birth_time="${birth_time}:00"

    echo -e "  ${GREEN}✓ Birth time accepted${NC}"
    valid_time=true
  done

  # Location section
  echo -e "\n${BOLD}${CYAN}┌───────────────────────────────────────────────────┐${NC}"
  echo -e "${BOLD}${CYAN}│                BIRTH LOCATION                      │${NC}"
  echo -e "${BOLD}${CYAN}└───────────────────────────────────────────────────┘${NC}\n"

  echo -e "${CYAN}Your birth location determines the geographical perspective${NC}"
  echo -e "${CYAN}of your chart and influences house placements${NC}\n"

  # Get location name
  local location=""
  local valid_location=false
  while [[ "$valid_location" != "true" ]]; do
    echo -e "${YELLOW}┌─ LOCATION DETAILS ─────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  The exact location affects planetary house placements │${NC}"
    echo -e "${YELLOW}└───────────────────────────────────────────────────────┘${NC}\n"

    echo -e "${BOLD}${RED}*${NC} ${BOLD}PLACE OF BIRTH:${NC} ${CYAN}(City, Country)${NC}"
    echo -e "  ${CYAN}• Example: New York, USA or Mumbai, India${NC}"
    echo -e "  ${CYAN}• Be as specific as possible (include city and country)${NC}"
    echo -e "  ${CYAN}• The system will try to find the coordinates automatically${NC}"
    read -p "  → " location

    if [[ -z "$location" ]]; then
      echo -e "  ${RED}× Birth place cannot be empty${NC}"
      echo -e "  ${YELLOW}ℹ️ Your birthplace is essential for accurate chart calculation${NC}"
      continue
    elif [[ ${#location} -lt 3 ]]; then
      echo -e "  ${RED}× Birth place must be at least 3 characters${NC}"
      continue
    fi

    echo -e "  ${GREEN}✓ Birth place accepted${NC}"
    valid_location=true
  done

  # Get coordinates with more user-friendly interface
  echo -e "\n${YELLOW}┌─ ADVANCED: COORDINATES ──────────────────────────────┐${NC}"
  echo -e "${YELLOW}│  Optional but recommended for maximum precision       │${NC}"
  echo -e "${YELLOW}└───────────────────────────────────────────────────────┘${NC}\n"

  echo -e "${CYAN}If you know the exact coordinates, enter them below.${NC}"
  echo -e "${CYAN}Otherwise, leave blank and we'll calculate them from your birth place.${NC}\n"

  # Get coordinates
  local latitude=""
  echo -e "${BOLD}LATITUDE:${NC} ${CYAN}(Optional)${NC}"
  echo -e "  ${CYAN}• Example: 40.7128 for New York${NC}"
  echo -e "  ${CYAN}• North of equator: positive values (e.g., 51.5074 for London)${NC}"
  echo -e "  ${CYAN}• South of equator: negative values (e.g., -33.8688 for Sydney)${NC}"
  read -p "  → " latitude

  # Default to 0 if empty
  if [[ -z "$latitude" ]]; then
    latitude="0"
    echo -e "  ${YELLOW}ℹ️ Using default latitude (will be calculated from location)${NC}"
  elif [[ ! "$latitude" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
    echo -e "  ${RED}× Invalid latitude format. Using default value 0${NC}"
    echo -e "  ${YELLOW}ℹ️ Correct format example: 40.7128 or -33.8688${NC}"
    latitude="0"
  elif (( $(echo "$latitude < -90 || $latitude > 90" | bc -l) )); then
    echo -e "  ${RED}× Latitude must be between -90 and 90. Using default value 0${NC}"
    echo -e "  ${YELLOW}ℹ️ Valid range: -90 (South Pole) to 90 (North Pole)${NC}"
    latitude="0"
  else
    echo -e "  ${GREEN}✓ Latitude accepted${NC}"
  fi

  local longitude=""
  echo -e "\n${BOLD}LONGITUDE:${NC} ${CYAN}(Optional)${NC}"
  echo -e "  ${CYAN}• Example: -74.0060 for New York${NC}"
  echo -e "  ${CYAN}• East of Greenwich: positive values (e.g., 0.1278 for London)${NC}"
  echo -e "  ${CYAN}• West of Greenwich: negative values (e.g., -74.0060 for New York)${NC}"
  read -p "  → " longitude

  # Default to 0 if empty
  if [[ -z "$longitude" ]]; then
    longitude="0"
    echo -e "  ${YELLOW}ℹ️ Using default longitude (will be calculated from location)${NC}"
  elif [[ ! "$longitude" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
    echo -e "  ${RED}× Invalid longitude format. Using default value 0${NC}"
    echo -e "  ${YELLOW}ℹ️ Correct format example: 0.1278 or -74.0060${NC}"
    longitude="0"
  elif (( $(echo "$longitude < -180 || $longitude > 180" | bc -l) )); then
    echo -e "  ${RED}× Longitude must be between -180 and 180. Using default value 0${NC}"
    echo -e "  ${YELLOW}ℹ️ Valid range: -180 to 180 (around the globe)${NC}"
    longitude="0"
  else
    echo -e "  ${GREEN}✓ Longitude accepted${NC}"
  fi

  # Summary of inputs with enhanced styling
  echo -e "\n${BOLD}${CYAN}┌───────────────────────────────────────────────────┐${NC}"
  echo -e "${BOLD}${CYAN}│               INPUT SUMMARY                        │${NC}"
  echo -e "${BOLD}${CYAN}└───────────────────────────────────────────────────┘${NC}\n"

  echo -e "${CYAN}Please review your birth chart information:${NC}\n"

  echo -e "  ${BOLD}${YELLOW}Full Name:${NC}     $name"
  echo -e "  ${BOLD}${YELLOW}Birth Date:${NC}    $birth_date"
  echo -e "  ${BOLD}${YELLOW}Birth Time:${NC}    ${birth_time%:00} (24-hour format)"
  echo -e "  ${BOLD}${YELLOW}Birth Place:${NC}   $location"

  if [[ "$latitude" != "0" || "$longitude" != "0" ]]; then
    echo -e "  ${BOLD}${YELLOW}Coordinates:${NC}   $latitude, $longitude"
  else
    echo -e "  ${BOLD}${YELLOW}Coordinates:${NC}   Will be determined from birth place"
  fi

  echo -e "\n${YELLOW}This information will be used to generate your astrological chart.${NC}"
  echo -e "${YELLOW}The accuracy of your chart depends on the precision of this data.${NC}\n"

  echo -e "${BOLD}${CYAN}Is this information correct? (Y/n)${NC}"
  read -p "  → " confirm

  if [[ "$confirm" == "n" || "$confirm" == "N" ]]; then
    echo -e "${YELLOW}Let's try again...${NC}\n"
    get_birth_details
    return
  fi

  echo -e "\n${CYAN}Preparing data for chart calculation...${NC}"
  echo -e "${YELLOW}Please wait while we process your information...${NC}\n"

  # Build validation request
  local validation_data=$(cat <<EOL
{
  "name": "$name",
  "birth_date": "$birth_date",
  "birth_time": "$birth_time",
  "latitude": $latitude,
  "longitude": $longitude,
  "location": "$location"
}
EOL
)

  echo "$validation_data"
}

# Function to handle questionnaire process
handle_questionnaire() {
  local chart_id="$1"

  log_message "INFO" "Creating questionnaire for chart ID: $chart_id"

  # Try to create questionnaire
  local questionnaire_response=$(curl -s -X POST "$API_URL/questionnaire" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}" -d "{\"chart_id\": \"$chart_id\"}")

  # Check for API error
  if echo "$questionnaire_response" | jq -e '.detail' > /dev/null; then
    local error_detail=$(echo "$questionnaire_response" | jq -r '.detail')
    log_message "ERROR" "Questionnaire API error: $error_detail"

    if [[ "$error_detail" == "Error connecting to backend service" ]]; then
      log_message "DIAGNOSTIC" "The questionnaire backend service appears to be unavailable"
      log_message "DIAGNOSTIC" "Please check that all required services are running"

      echo -e "${RED}Questionnaire service is unavailable. Testing cannot proceed.${NC}"
      echo -e "${YELLOW}Would you like to manually enter questionnaire answers for testing? (y/n)${NC}"
      read use_mock

      if [[ "$use_mock" == "y" ]]; then
        log_message "INFO" "User opted to manually simulate questionnaire responses"
        # Generate mock questionnaire ID
        local questionnaire_id="quest_manual_$(date +%s)"
        echo "Using manual questionnaire ID: $questionnaire_id"
        return "$questionnaire_id"
      else
        return ""
      fi
    else
      return ""
    fi
  fi

  # Extract questionnaire ID
  local questionnaire_id=$(echo "$questionnaire_response" | jq -r '.id // .questionnaire_id')

  if [[ -z "$questionnaire_id" || "$questionnaire_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing questionnaire ID in response"
    return ""
  fi

  log_message "INFO" "Questionnaire created successfully with ID: $questionnaire_id"
  echo "$questionnaire_id"
}

# Main test function with improved error handling and diagnostics
run_sequence_test() {
  local test_start_time=$(date +%s)
  log_message "INFO" "Starting full sequence flow test according to sequence diagram"
  log_message "INFO" "Test started at $(date)"

  # Step 0: Service Health Check
  log_message "INFO" "Step 0: API Health Check"

  if ! check_api_health; then
    log_message "FATAL" "API health check failed. Cannot proceed with testing."
    return 1
  fi

  # Step 1: Session Initialization
  log_message "INFO" "Step 1: Session Initialization"

  if ! init_session; then
    log_message "FATAL" "Failed to initialize session, exiting"
    return 1
  fi

  log_message "INFO" "Session initialized successfully with token: ${SESSION_TOKEN:0:10}..."

  # Step 2: Chart Creation - Interactive
  log_message "INFO" "Step 2: Interactive Chart Creation"

  # Add a small delay to ensure terminal is ready
  sleep 0.5

  # Instead of clearing the screen which might cause issues, use a visual separator
  echo -e "\n\n${CYAN}=============================================================${NC}"
  echo -e "${BOLD}${CYAN}                BIRTH CHART CALCULATOR                   ${NC}"
  echo -e "${CYAN}=============================================================${NC}\n"

  echo -e "${YELLOW}This tool will create your personalized astrological birth chart.${NC}"
  echo -e "${YELLOW}Please provide accurate birth information for best results.${NC}"
  echo -e "${YELLOW}You can press Ctrl+C at any time to cancel the process.${NC}\n"
  echo -e "${CYAN}Press ENTER to start...${NC}"
  read

  # Get birth details interactively with enhanced UI
  local validation_data=$(get_birth_details)

  # Use a visual separator instead of clearing
  echo -e "\n${CYAN}=============================================================${NC}"

  log_message "INFO" "Validating birth details..."
  echo -e "${CYAN}Validating birth details...${NC}"

  # Call API to validate birth details
  local validation_response=$(curl -s -X POST "$API_URL/chart/validate" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}" -d "$validation_data")

  if ! echo "$validation_response" | jq -e '.valid' > /dev/null || [ "$(echo "$validation_response" | jq -r '.valid')" != "true" ]; then
    log_message "ERROR" "Birth details validation failed: $(echo "$validation_response" | jq -r '.message // "Unknown error"')"
    echo -e "${RED}The birth details you provided failed validation. Please fix the issues and try again:${NC}"
    echo -e "${RED}$(echo "$validation_response" | jq -r '.message // "Unknown error"')${NC}"
    return 1
  fi

  log_message "INFO" "Birth details validation successful"
  echo -e "${GREEN}Birth details validated successfully${NC}"

  # Step 3: Chart Generation
  log_message "INFO" "Step 3: Chart Generation"
  echo -e "${CYAN}Generating chart...${NC}"

  # Call API to generate chart
  local chart_response=$(curl -s -X POST "$API_URL/chart/generate" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}" -d "$validation_data")

  if ! echo "$chart_response" | jq -e '.chart_id' > /dev/null; then
    log_message "ERROR" "Chart generation failed: $(echo "$chart_response" | jq -r '.detail // "Unknown error"')"
    echo -e "${RED}Chart generation failed:${NC}"
    echo -e "${RED}$(echo "$chart_response" | jq -r '.detail // "Unknown error"')${NC}"
    return 1
  fi

  # Extract chart ID
  local chart_id=$(echo "$chart_response" | jq -r '.chart_id')

  if [[ -z "$chart_id" || "$chart_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing chart ID in response"
    return 1
  fi

  log_message "INFO" "Chart generated successfully with ID: $chart_id"
  echo -e "${GREEN}Chart generated successfully with ID: $chart_id${NC}"

  # Save chart details to file for reference
  echo "$chart_response" > "${TEST_OUTPUT_DIR:-test_output}/chart_$chart_id.json"
  log_message "INFO" "Chart details saved to ${TEST_OUTPUT_DIR:-test_output}/chart_$chart_id.json"

  # Step 4: Questionnaire
  log_message "INFO" "Step 4: Questionnaire"
  echo -e "${CYAN}=== Interactive Questionnaire ===${NC}"

  local questionnaire_id=$(handle_questionnaire "$chart_id")

  if [[ -z "$questionnaire_id" ]]; then
    log_message "ERROR" "Failed to create or handle questionnaire"
    echo -e "${RED}Cannot proceed with the questionnaire. Testing will stop here.${NC}"
    return 1
  fi

  log_message "INFO" "Using questionnaire ID: $questionnaire_id"
  echo -e "${GREEN}Questionnaire prepared with ID: $questionnaire_id${NC}"

  # Step 5: Birth Time Rectification
  log_message "INFO" "Step 5: Birth Time Rectification"
  echo -e "${CYAN}=== Birth Time Rectification ===${NC}"

  # Call API to start rectification
  local rectification_response=$(curl -s -X POST "$API_URL/chart/rectify" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}" -d "{\"chart_id\": \"$chart_id\", \"questionnaire_id\": \"$questionnaire_id\"}")

  if echo "$rectification_response" | jq -e '.error' > /dev/null; then
    log_message "ERROR" "Birth time rectification failed: $(echo "$rectification_response" | jq -r '.error.message // "Unknown error"')"
    echo -e "${RED}Birth time rectification failed:${NC}"
    echo -e "${RED}$(echo "$rectification_response" | jq -r '.error.message // "Unknown error"')${NC}"

    # Save the error response for debugging
    echo "$rectification_response" > "${TEST_OUTPUT_DIR:-test_output}/rectification_error.json"
    log_message "INFO" "Error details saved to ${TEST_OUTPUT_DIR:-test_output}/rectification_error.json"

    return 1
  fi

  # Extract rectification ID
  local rectification_id=$(echo "$rectification_response" | jq -r '.rectification_id')

  if [[ -z "$rectification_id" || "$rectification_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing rectification ID in response"
    return 1
  fi

  log_message "INFO" "Birth time rectification initiated with ID: $rectification_id"
  echo -e "${GREEN}Birth time rectification process started with ID: $rectification_id${NC}"
  echo -e "${YELLOW}Waiting for rectification to complete...${NC}"

  # Poll for rectification status with progress indicator
  local rectification_complete=false
  local max_attempts=30
  local attempt=0
  local progress=0

  while [[ "$rectification_complete" != "true" && $attempt -lt $max_attempts ]]; do
    log_message "INFO" "Checking rectification status (attempt $((attempt+1))/$max_attempts)..."

    # Show a simple progress indicator
    echo -ne "${YELLOW}Processing: ["
    for ((i=0; i<progress; i++)); do
      echo -ne "#"
    done
    for ((i=progress; i<10; i++)); do
      echo -ne " "
    done
    echo -ne "] $((progress*10))%\r${NC}"

    local status_response=$(curl -s "$API_URL/chart/rectify/status/$rectification_id" -H "Content-Type: application/json" -H "Authorization: Bearer ${SESSION_TOKEN}")

    if echo "$status_response" | jq -e '.error' > /dev/null; then
      echo -e "\n"  # Clear progress line
      log_message "ERROR" "Failed to get rectification status: $(echo "$status_response" | jq -r '.error.message // "Unknown error"')"
      echo -e "${RED}Failed to get rectification status:${NC}"
      echo -e "${RED}$(echo "$status_response" | jq -r '.error.message // "Unknown error"')${NC}"
      return 1
    fi

    local status=$(echo "$status_response" | jq -r '.status')

    if [[ "$status" == "completed" ]]; then
      rectification_complete=true
      progress=10
      # Show completed progress
      echo -ne "${GREEN}Processing: ["
      for ((i=0; i<10; i++)); do
        echo -ne "#"
      done
      echo -e "] 100%${NC}"
    elif [[ "$status" == "failed" ]]; then
      echo -e "\n"  # Clear progress line
      log_message "ERROR" "Rectification failed: $(echo "$status_response" | jq -r '.message // "Unknown error"')"
      echo -e "${RED}Rectification failed:${NC}"
      echo -e "${RED}$(echo "$status_response" | jq -r '.message // "Unknown error"')${NC}"
      return 1
    else
      # Update progress based on current attempt
      progress=$((attempt * 10 / max_attempts))
      # Wait before checking again
      sleep 2
      ((attempt++))
    fi
  done

  if [[ "$rectification_complete" != "true" ]]; then
    echo -e "\n"  # Clear progress line
    log_message "ERROR" "Rectification timed out after $max_attempts attempts"
    echo -e "${RED}Rectification process timed out. The operation took too long to complete.${NC}"
    return 1
  fi

  # Get rectified chart ID and time
  local rectified_chart_id=$(echo "$status_response" | jq -r '.rectified_chart_id')
  local rectified_time=$(echo "$status_response" | jq -r '.rectified_time')

  log_message "INFO" "Birth time rectification completed with rectified chart ID: $rectified_chart_id"
  log_message "INFO" "Rectified birth time: $rectified_time"

  echo -e "${GREEN}Birth time rectification completed successfully!${NC}"
  echo -e "${GREEN}Original birth time vs. Rectified birth time:${NC}"
  echo -e "${CYAN}Original: $(echo "$chart_response" | jq -r '.birth_details.birth_time')${NC}"
  echo -e "${CYAN}Rectified: $rectified_time${NC}"

  # Save rectification results
  echo "$status_response" > "${TEST_OUTPUT_DIR:-test_output}/rectification_results.json"
  log_message "INFO" "Rectification results saved to ${TEST_OUTPUT_DIR:-test_output}/rectification_results.json"

  # Test completed successfully
  local test_end_time=$(date +%s)
  local test_duration=$((test_end_time - test_start_time))

  log_message "INFO" "Full sequence flow test completed successfully in $test_duration seconds"
  echo -e "\n${GREEN}All tests completed successfully in $test_duration seconds${NC}"
  return 0
}

# URL encode function
urlencode() {
  local string="$1"
  local strlen=${#string}
  local encoded=""
  local pos c o

  for (( pos=0 ; pos<strlen ; pos++ )); do
    c=${string:$pos:1}
    case "$c" in
      [-_.~a-zA-Z0-9] ) o="${c}" ;;
      * )               printf -v o '%%%02x' "'$c"
    esac
    encoded+="${o}"
  done
  echo "${encoded}"
}

# Run chart test
run_chart_test() {
  log_message "INFO" "Running chart tests..."

  # Create a sample chart
  log_message "INFO" "Creating sample chart..."
  local chart_result=$(create_chart "Sample Test Chart" "1990-01-01" "12:00" 0 0 "Test Location")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create sample chart"
    return 1
  fi

  # Extract chart ID
  local chart_id=$(echo "$chart_result" | jq -r '.id')
  log_message "INFO" "Sample chart created with ID: $chart_id"

  # Get the chart
  log_message "INFO" "Retrieving chart..."
  local get_result=$(get_chart "$chart_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to retrieve chart"
    return 1
  fi
  log_message "INFO" "Chart retrieved successfully"

  # Update the chart
  log_message "INFO" "Updating chart..."
  local update_result=$(update_chart "$chart_id" "Updated Chart" "1990-01-01" "14:00" 10 10 "Updated Location")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to update chart"
    return 1
  fi
  log_message "INFO" "Chart updated successfully"

  # Create a second chart for comparison
  log_message "INFO" "Creating second chart for comparison..."
  local chart2_result=$(create_chart "Comparison Chart" "1995-05-05" "15:30" 20 20 "Another Location")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create second chart"
    return 1
  fi

  # Extract second chart ID
  local chart2_id=$(echo "$chart2_result" | jq -r '.id')
  log_message "INFO" "Second chart created with ID: $chart2_id"

  # Compare charts
  log_message "INFO" "Comparing charts..."
  local compare_result=$(compare_charts "$chart_id" "$chart2_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to compare charts"
    return 1
  fi
  log_message "INFO" "Charts compared successfully"

  # Delete charts
  log_message "INFO" "Deleting charts..."
  delete_chart "$chart_id"
  delete_chart "$chart2_id"
  log_message "INFO" "Charts deleted successfully"

  log_message "INFO" "Chart tests completed successfully"
  return 0
}

# Run WebSocket test
run_websocket_test() {
  log_message "INFO" "Running WebSocket tests..."

  # Create a temporary file for WebSocket output
  local ws_output=$(mktemp)

  # Connect to realtime endpoint
  log_message "INFO" "Connecting to realtime endpoint..."
  ws_connect "/realtime" "{}" "$ws_output" 10
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to connect to WebSocket"
    rm -f "$ws_output"
    return 1
  fi

  # Read initial response
  local response=$(cat "$ws_output")
  if [[ -z "$response" ]]; then
    log_message "ERROR" "No response received from WebSocket"
    ws_close
    rm -f "$ws_output"
    return 1
  fi

  log_message "INFO" "WebSocket connection established"

  # Send a ping message
  log_message "INFO" "Sending ping message..."
  ws_send "{\"type\":\"ping\",\"timestamp\":$(date +%s)}"

  # Wait for response
  sleep 2
  local response=$(cat "$ws_output")

  # Close connection
  ws_close
  rm -f "$ws_output"

  log_message "INFO" "WebSocket tests completed successfully"
  return 0
}

# Main execution
main() {
  # Print banner
  print_banner

  # Create the test output directory
  mkdir -p "${TEST_OUTPUT_DIR:-test_output}"

  # Parse command line arguments
  while getopts ":t:v" opt; do
    case ${opt} in
      t )
        TEST_TYPE=$OPTARG
        ;;
      v )
        VERBOSE=true
        export VERBOSE
        ;;
      \? )
        echo "Invalid option: -$OPTARG" 1>&2
        exit 1
        ;;
      : )
        echo "Option -$OPTARG requires an argument" 1>&2
        exit 1
        ;;
    esac
  done

  # Set default test type to sequence
  TEST_TYPE=${TEST_TYPE:-"sequence"}

  # Check dependencies
  if ! check_dependencies; then
    echo -e "${RED}Required dependencies missing. Please install them and try again.${NC}"
    exit 1
  fi

  # Initialize API client
  log_message "INFO" "Initializing API client"
  if ! init_session; then
    log_message "FATAL" "Session initialization failed. API must be available to run tests."
    echo -e "${RED}Failed to initialize a session with the API. Please make sure the API server is running.${NC}"
    exit 1
  fi

  # Run tests based on type
  case "$TEST_TYPE" in
    "unit")
      log_message "INFO" "Running unit tests"
      run_unit_tests
      ;;
    "interactive")
      log_message "INFO" "Running interactive test flow"
      run_sequence_test
      ;;
    "sequence")
      log_message "INFO" "Running sequence diagram test flow"
      run_sequence_test
      ;;
    *)
      log_message "ERROR" "Unknown test type: $TEST_TYPE"
      echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
      echo -e "${YELLOW}Valid options are: unit, interactive, sequence${NC}"
      exit 1
      ;;
  esac

  log_message "INFO" "All tests completed successfully"
  exit 0
}

# Run main function
main "$@"
