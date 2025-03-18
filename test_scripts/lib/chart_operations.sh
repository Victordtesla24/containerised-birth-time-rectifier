#!/bin/bash

# Chart operations for Birth Time Rectifier API
# Handles chart creation, retrieval, updating and comparison

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Source API client functions
if [[ -z "$API_URL" ]]; then
  source "$(dirname "$0")/api_client.sh"
fi

# Create a new chart
create_chart() {
  local name="$1"
  local birth_date="$2"
  local birth_time="$3"
  local latitude="$4"
  local longitude="$5"
  local location="$6"

  log_message "INFO" "Creating chart with name: $name"
  echo -e "${CYAN}Creating chart for $name...${NC}"

  # Validate required parameters
  if [[ -z "$name" || -z "$birth_date" || -z "$birth_time" ]]; then
    log_message "ERROR" "Missing required parameters for chart creation"
    echo -e "${RED}Error: Missing required parameters (name, birth_date, birth_time)${NC}" >&2
    return 1
  fi

  # Validate coordinates
  if [[ ! "$latitude" =~ ^-?[0-9]+(\.[0-9]+)?$ || ! "$longitude" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
    log_message "ERROR" "Invalid coordinates format: latitude=$latitude, longitude=$longitude"
    echo -e "${RED}Error: Invalid coordinates format${NC}" >&2
    return 1
  fi

  # Build request payload
  local request_data=$(cat <<EOL
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

  # Call API to create chart
  local api_response=$(api_request "POST" "/chart/generate" "$request_data")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to create chart failed"
    echo -e "${RED}Failed to create chart. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid chart ID in the response
  if ! echo "$api_response" | jq -e '.chart_id' > /dev/null; then
    log_message "ERROR" "Invalid API response: missing chart_id"
    echo -e "${RED}Invalid API response: missing chart ID${NC}"
    return 1
  fi

  local chart_id=$(echo "$api_response" | jq -r '.chart_id')
  log_message "INFO" "Chart created successfully with ID: $chart_id"
  echo -e "${GREEN}Chart created successfully with ID: $chart_id${NC}"

  echo "$api_response"
  return 0
}

# Get chart details by ID
get_chart() {
  local chart_id="$1"

  log_message "INFO" "Getting chart: $chart_id"
  echo -e "${CYAN}Retrieving chart $chart_id...${NC}"

  # Validate chart ID
  if [[ -z "$chart_id" ]]; then
    log_message "ERROR" "Missing chart ID parameter"
    echo -e "${RED}Error: Chart ID is required${NC}" >&2
    return 1
  fi

  # Call API to get chart
  local api_response=$(api_request "GET" "/chart/$chart_id" "{}")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to get chart failed"
    echo -e "${RED}Failed to retrieve chart. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid chart in the response
  if ! echo "$api_response" | jq -e '.chart_id' > /dev/null; then
    log_message "ERROR" "Invalid API response: missing chart_id"
    echo -e "${RED}Invalid API response: missing chart data${NC}"
    return 1
  fi

  log_message "INFO" "Chart retrieved successfully"
  echo -e "${GREEN}Chart retrieved successfully${NC}"

  echo "$api_response"
  return 0
}

# Update an existing chart
update_chart() {
  local chart_id="$1"
  local name="$2"
  local birth_date="$3"
  local birth_time="$4"
  local latitude="$5"
  local longitude="$6"
  local location="$7"

  log_message "INFO" "Updating chart: $chart_id"
  echo -e "${CYAN}Updating chart $chart_id...${NC}"

  # Validate chart ID
  if [[ -z "$chart_id" ]]; then
    log_message "ERROR" "Missing chart ID parameter"
    echo -e "${RED}Error: Chart ID is required${NC}" >&2
    return 1
  fi

  # Build request payload
  local request_data=$(cat <<EOL
{
  "chart_id": "$chart_id",
  "name": "$name",
  "birth_date": "$birth_date",
  "birth_time": "$birth_time",
  "latitude": $latitude,
  "longitude": $longitude,
  "location": "$location"
}
EOL
)

  # Call API to update chart
  local api_response=$(api_request "PUT" "/chart/$chart_id" "$request_data")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to update chart failed"
    echo -e "${RED}Failed to update chart. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid response
  if ! echo "$api_response" | jq -e '.success' > /dev/null; then
    if echo "$api_response" | jq -e '.error' > /dev/null; then
      local error_msg=$(echo "$api_response" | jq -r '.error.message // "Unknown error"')
      log_message "ERROR" "API error updating chart: $error_msg"
      echo -e "${RED}Error updating chart: $error_msg${NC}"
      return 1
    else
      log_message "ERROR" "Invalid API response on chart update"
      echo -e "${RED}Invalid API response on chart update${NC}"
      return 1
    fi
  fi

  log_message "INFO" "Chart updated successfully"
  echo -e "${GREEN}Chart updated successfully${NC}"

  echo "$api_response"
  return 0
}

# Delete a chart
delete_chart() {
  local chart_id="$1"

  log_message "INFO" "Deleting chart: $chart_id"
  echo -e "${CYAN}Deleting chart $chart_id...${NC}"

  # Validate chart ID
  if [[ -z "$chart_id" ]]; then
    log_message "ERROR" "Missing chart ID parameter"
    echo -e "${RED}Error: Chart ID is required${NC}" >&2
    return 1
  fi

  # Call API to delete chart
  local api_response=$(api_request "DELETE" "/chart/$chart_id" "{}")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to delete chart failed"
    echo -e "${RED}Failed to delete chart. API returned an error.${NC}"
    return 1
  fi

  # Verify the deletion was successful
  if ! echo "$api_response" | jq -e '.success' > /dev/null; then
    if echo "$api_response" | jq -e '.error' > /dev/null; then
      local error_msg=$(echo "$api_response" | jq -r '.error.message // "Unknown error"')
      log_message "ERROR" "API error deleting chart: $error_msg"
      echo -e "${RED}Error deleting chart: $error_msg${NC}"
      return 1
    else
      log_message "ERROR" "Invalid API response on chart deletion"
      echo -e "${RED}Invalid API response on chart deletion${NC}"
      return 1
    fi
  fi

  log_message "INFO" "Chart deleted successfully"
  echo -e "${GREEN}Chart deleted successfully${NC}"

  echo "$api_response"
  return 0
}

# Compare two charts
compare_charts() {
  local chart1_id="$1"
  local chart2_id="$2"
  local comparison_type="${3:-synastry}"
  local include_significance="${4:-true}"

  log_message "INFO" "Comparing charts: $chart1_id and $chart2_id (type: $comparison_type)"
  echo -e "${CYAN}Comparing charts $chart1_id and $chart2_id...${NC}"

  # Validate chart IDs
  if [[ -z "$chart1_id" || -z "$chart2_id" ]]; then
    log_message "ERROR" "Missing chart ID parameters"
    echo -e "${RED}Error: Both chart IDs are required${NC}" >&2
    return 1
  fi

  # Validate comparison type
  if [[ "$comparison_type" != "synastry" && "$comparison_type" != "composite" && "$comparison_type" != "transit" ]]; then
    log_message "WARNING" "Unrecognized comparison type: $comparison_type, defaulting to synastry"
    comparison_type="synastry"
  fi

  # Call API to compare charts
  local api_response=$(api_request "GET" "/chart/compare?chart1_id=$chart1_id&chart2_id=$chart2_id&comparison_type=$comparison_type&include_significance=$include_significance" "{}")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to compare charts failed"
    echo -e "${RED}Failed to compare charts. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid comparison in the response
  if echo "$api_response" | jq -e '.error' > /dev/null; then
    local error_msg=$(echo "$api_response" | jq -r '.error.message // "Unknown error"')
    log_message "ERROR" "API error comparing charts: $error_msg"
    echo -e "${RED}Error comparing charts: $error_msg${NC}"
    return 1
  fi

  log_message "INFO" "Chart comparison completed"
  echo -e "${GREEN}Chart comparison completed successfully${NC}"

  echo "$api_response"
  return 0
}

# Create a sample chart with default values
create_sample_chart() {
  # Redirect all output to stderr except for the final chart_id
  {
    log_message "INFO" "Creating sample chart for testing"
    echo -e "${CYAN}Creating sample chart for testing...${NC}"

    local name="Test Person"
    local birth_date="1990-01-01"
    local birth_time="12:00:00"
    local latitude="40.7128"
    local longitude="-74.0060"
    local location="New York, NY, USA"

    # Call API directly to create chart
    local request_data="{
      \"name\": \"$name\",
      \"birth_date\": \"$birth_date\",
      \"birth_time\": \"$birth_time\",
      \"latitude\": $latitude,
      \"longitude\": $longitude,
      \"location\": \"$location\"
    }"

    # Call API to create chart
    local api_response=$(api_request "POST" "/chart/generate" "$request_data")
    local api_status=$?

    if [[ $api_status -ne 0 ]]; then
      log_message "ERROR" "API request to create chart failed"
      echo -e "${RED}Failed to create chart. API returned an error.${NC}"
      return 1
    fi

    # Debug the response
    log_message "DEBUG" "Chart API response: $api_response"

    # Extract and return the chart ID
    local chart_id=$(echo "$api_response" | jq -r '.chart_id // empty')

    if [[ -z "$chart_id" ]]; then
      log_message "ERROR" "Invalid or missing chart ID in response"
      log_message "ERROR" "Response was: $api_response"
      echo -e "${RED}Invalid or missing chart ID in response${NC}"
      return 1
    fi

    log_message "INFO" "Sample chart created with ID: $chart_id"
    echo -e "${GREEN}Sample chart created with ID: $chart_id${NC}"
  } >&2

  # Return only the chart ID to stdout for capture by the caller
  # Make sure there's no other output and no trailing newlines
  local chart_id=$(echo "$api_response" | jq -r '.chart_id // empty')
  echo -n "$chart_id"
  return 0
}

# Rectify a chart based on questionnaire answers
rectify_chart() {
  local chart_id="$1"
  local questionnaire_id="$2"
  local answers="$3"

  log_message "INFO" "Starting chart rectification process for chart: $chart_id with questionnaire: $questionnaire_id"
  echo -e "${CYAN}Starting birth time rectification process...${NC}"

  # Validate parameters
  if [[ -z "$chart_id" || -z "$questionnaire_id" ]]; then
    log_message "ERROR" "Missing required parameters for chart rectification"
    echo -e "${RED}Error: Both chart ID and questionnaire ID are required${NC}" >&2
    return 1
  fi

  # Create default answers array if not provided
  if [[ -z "$answers" ]]; then
    answers='"answers": [
      {"question_id": "default_q1", "answer": "Yes"},
      {"question_id": "default_q2", "answer": "No"}
    ],'
  else
    # If answers is provided, ensure it's properly formatted
    answers="\"answers\": $answers,"
  fi

  # Call API for rectification
  local api_response=$(api_request "POST" "/chart/rectify" "{
    \"chart_id\": \"$chart_id\",
    \"questionnaire_id\": \"$questionnaire_id\",
    $answers
    \"include_details\": true
  }")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to rectify chart failed"
    echo -e "${RED}Failed to start rectification process. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid rectification ID in the response
  if ! echo "$api_response" | jq -e '.rectification_id' > /dev/null; then
    if echo "$api_response" | jq -e '.error' > /dev/null; then
      local error_msg=$(echo "$api_response" | jq -r '.error.message // "Unknown error"')
      log_message "ERROR" "API error initiating rectification: $error_msg"
      echo -e "${RED}Error initiating rectification: $error_msg${NC}"
      return 1
    else
      log_message "ERROR" "Invalid API response: missing rectification_id"
      echo -e "${RED}Invalid API response: missing rectification ID${NC}"
      return 1
    fi
  fi

  local rectification_id=$(echo "$api_response" | jq -r '.rectification_id')
  log_message "INFO" "Chart rectification initiated with ID: $rectification_id"
  echo -e "${GREEN}Rectification process started with ID: $rectification_id${NC}"

  echo "$api_response"
  return 0
}

# Get rectification status
get_rectification_status() {
  local rectification_id="$1"

  log_message "INFO" "Checking rectification status for: $rectification_id"

  # Validate rectification ID
  if [[ -z "$rectification_id" ]]; then
    log_message "ERROR" "Missing rectification ID parameter"
    echo -e "${RED}Error: Rectification ID is required${NC}" >&2
    return 1
  fi

  # Call API for status check
  local api_response=$(api_request "GET" "/chart/rectify/status/$rectification_id" "{}")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to get rectification status failed"
    echo -e "${RED}Failed to get rectification status. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid status in the response
  if ! echo "$api_response" | jq -e '.status' > /dev/null; then
    if echo "$api_response" | jq -e '.error' > /dev/null; then
      local error_msg=$(echo "$api_response" | jq -r '.error.message // "Unknown error"')
      log_message "ERROR" "API error getting rectification status: $error_msg"
      echo -e "${RED}Error getting rectification status: $error_msg${NC}"
      return 1
    else
      log_message "ERROR" "Invalid API response: missing status"
      echo -e "${RED}Invalid API response: missing status information${NC}"
      return 1
    fi
  fi

  local status=$(echo "$api_response" | jq -r '.status')
  log_message "INFO" "Retrieved rectification status: $status"

  # Provide user-friendly status message
  case "$status" in
    "pending")
      echo -e "${YELLOW}Rectification is pending in the queue${NC}"
      ;;
    "processing")
      echo -e "${YELLOW}Rectification is currently being processed${NC}"
      local progress=$(echo "$api_response" | jq -r '.progress // "0"')
      echo -e "${YELLOW}Progress: ${progress}%${NC}"
      ;;
    "completed")
      echo -e "${GREEN}Rectification completed successfully${NC}"
      ;;
    "failed")
      echo -e "${RED}Rectification failed: $(echo "$api_response" | jq -r '.message // "Unknown error"')${NC}"
      ;;
    *)
      echo -e "${YELLOW}Rectification status: $status${NC}"
      ;;
  esac

  echo "$api_response"
  return 0
}

# Export a chart to PDF or other formats
export_chart() {
  local chart_id="$1"
  local format="${2:-pdf}"

  log_message "INFO" "Exporting chart: $chart_id to format: $format"
  echo -e "${CYAN}Exporting chart to $format format...${NC}"

  # Validate chart ID
  if [[ -z "$chart_id" ]]; then
    log_message "ERROR" "Missing chart ID parameter"
    echo -e "${RED}Error: Chart ID is required${NC}" >&2
    return 1
  fi

  # Validate format
  if [[ "$format" != "pdf" && "$format" != "png" && "$format" != "jpg" && "$format" != "svg" ]]; then
    log_message "WARNING" "Unrecognized export format: $format, defaulting to pdf"
    format="pdf"
  fi

  # Call API for export
  local api_response=$(api_request "POST" "/chart/export" "{\"chart_id\": \"$chart_id\", \"format\": \"$format\"}")
  local api_status=$?

  if [[ $api_status -ne 0 ]]; then
    log_message "ERROR" "API request to export chart failed"
    echo -e "${RED}Failed to export chart. API returned an error.${NC}"
    return 1
  fi

  # Verify we have a valid download URL in the response
  if ! echo "$api_response" | jq -e '.download_url' > /dev/null; then
    if echo "$api_response" | jq -e '.error' > /dev/null; then
      local error_msg=$(echo "$api_response" | jq -r '.error.message // "Unknown error"')
      log_message "ERROR" "API error exporting chart: $error_msg"
      echo -e "${RED}Error exporting chart: $error_msg${NC}"
      return 1
    else
      log_message "ERROR" "Invalid API response: missing download_url"
      echo -e "${RED}Invalid API response: missing download URL${NC}"
      return 1
    fi
  fi

  local download_url=$(echo "$api_response" | jq -r '.download_url')
  log_message "INFO" "Chart exported successfully with download URL: $download_url"
  echo -e "${GREEN}Chart exported successfully${NC}"
  echo -e "${GREEN}Download URL: $download_url${NC}"

  echo "$api_response"
  return 0
}

# Export functions
export -f create_chart get_chart update_chart delete_chart compare_charts
export -f create_sample_chart rectify_chart get_rectification_status export_chart
