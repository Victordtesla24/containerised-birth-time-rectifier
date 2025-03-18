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

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to create chart failed"
    return 1
  fi

  log_message "INFO" "Chart created successfully"
  echo "$api_response"
  return 0
}

# Get chart details by ID
get_chart() {
  local chart_id="$1"

  log_message "INFO" "Getting chart: $chart_id"

  # Call API to get chart
  local api_response=$(api_request "GET" "/chart/$chart_id" "{}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to get chart failed"
    return 1
  fi

  log_message "INFO" "Chart retrieved successfully"
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

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to update chart failed"
    return 1
  fi

  log_message "INFO" "Chart updated successfully"
  echo "$api_response"
  return 0
}

# Delete a chart
delete_chart() {
  local chart_id="$1"

  log_message "INFO" "Deleting chart: $chart_id"

  # Call API to delete chart
  local api_response=$(api_request "DELETE" "/chart/$chart_id" "{}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to delete chart failed"
    return 1
  fi

  log_message "INFO" "Chart deleted successfully"
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

  # Call API to compare charts
  local api_response=$(api_request "GET" "/chart/compare?chart1_id=$chart1_id&chart2_id=$chart2_id&comparison_type=$comparison_type&include_significance=$include_significance" "{}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to compare charts failed"
    return 1
  fi

  log_message "INFO" "Chart comparison completed"
  echo "$api_response"
  return 0
}

# Create a sample chart with default values
create_sample_chart() {
  log_message "INFO" "Creating sample chart for testing"

  local name="Test Person"
  local birth_date="1990-01-01"
  local birth_time="12:00:00"
  local latitude="40.7128"
  local longitude="-74.0060"
  local location="New York, NY, USA"

  # Create the chart using the main function
  local chart_data=$(create_chart "$name" "$birth_date" "$birth_time" "$latitude" "$longitude" "$location")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create sample chart"
    return 1
  fi

  # Extract and return the chart ID
  local chart_id=$(echo "$chart_data" | jq -r '.chart_id')

  if [[ -z "$chart_id" || "$chart_id" == "null" ]]; then
    log_message "ERROR" "Invalid or missing chart ID in response"
    return 1
  fi

  echo "$chart_id"
  return 0
}

# Rectify a chart based on questionnaire answers
rectify_chart() {
  local chart_id="$1"
  local questionnaire_id="$2"

  log_message "INFO" "Starting chart rectification process for chart: $chart_id with questionnaire: $questionnaire_id"

  # Call API for rectification
  local api_response=$(api_request "POST" "/chart/rectify" "{\"chart_id\": \"$chart_id\", \"questionnaire_id\": \"$questionnaire_id\"}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to rectify chart failed"
    return 1
  fi

  log_message "INFO" "Chart rectification initiated"
  echo "$api_response"
  return 0
}

# Get rectification status
get_rectification_status() {
  local rectification_id="$1"

  log_message "INFO" "Checking rectification status for: $rectification_id"

  # Call API for status check
  local api_response=$(api_request "GET" "/chart/rectify/status/$rectification_id" "{}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to get rectification status failed"
    return 1
  fi

  log_message "INFO" "Retrieved rectification status"
  echo "$api_response"
  return 0
}

# Export a chart to PDF or other formats
export_chart() {
  local chart_id="$1"
  local format="${2:-pdf}"

  log_message "INFO" "Exporting chart: $chart_id to format: $format"

  # Call API for export
  local api_response=$(api_request "POST" "/chart/export" "{\"chart_id\": \"$chart_id\", \"format\": \"$format\"}")

  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "API request to export chart failed"
    return 1
  fi

  log_message "INFO" "Chart exported successfully"
  echo "$api_response"
  return 0
}

# Export functions
export -f create_chart get_chart update_chart delete_chart compare_charts
export -f create_sample_chart rectify_chart get_rectification_status export_chart
