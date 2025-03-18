#!/bin/bash

# Chart Operations
# Handles chart-specific API operations

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Source API client functions if not already sourced
if [[ -z "$API_URL" ]]; then
  source "$(dirname "$0")/api_client.sh"
fi

# Function to create a new chart
create_chart() {
  local chart_data="$1"

  log_message "INFO" "Creating new chart with data: $chart_data"

  # For testing without real API endpoints, we'll use a mock chart ID
  local chart_id="chart-$(date +%s)"

  log_message "INFO" "Chart created successfully with ID: $chart_id"
  echo "$chart_id"
  return 0
}

# Function to retrieve chart data
get_chart() {
  local chart_id="$1"

  log_message "INFO" "Retrieving chart with ID: $chart_id"

  # For testing without real API endpoints, we'll return mock chart data
  local chart_data='{
    "chart_id": "'$chart_id'",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "0.001",
    "price": "50000"
  }'

  log_message "INFO" "Chart retrieved successfully"
  echo "$chart_data"
  return 0
}

# Function to update chart data
update_chart() {
  local chart_id="$1"
  local chart_data="$2"

  log_message "INFO" "Updating chart with ID: $chart_id"

  # For testing without real API endpoints, we'll return mock updated chart data
  local updated_chart='{
    "chart_id": "'$chart_id'",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "0.002",
    "price": "51000",
    "status": "updated"
  }'

  log_message "INFO" "Chart updated successfully"
  echo "$updated_chart"
  return 0
}

# Function to delete a chart
delete_chart() {
  local chart_id="$1"

  log_message "INFO" "Deleting chart with ID: $chart_id"

  # For testing without real API endpoints, we'll just log the deletion
  log_message "INFO" "Chart deleted successfully"
  return 0
}

# Function to validate chart data
validate_chart_data() {
  local chart_data="$1"

  log_message "INFO" "Validating chart data"

  # Basic JSON validation
  if ! echo "$chart_data" | jq empty > /dev/null 2>&1; then
    log_message "ERROR" "Invalid JSON format in chart data"
    return 1
  fi

  # Check for required fields for birth chart
  local name=$(echo "$chart_data" | jq -r '.name // empty')
  if [[ -z "$name" ]]; then
    log_message "ERROR" "Missing required field: name"
    return 1
  fi

  local birth_date=$(echo "$chart_data" | jq -r '.birth_date // empty')
  if [[ -z "$birth_date" ]]; then
    log_message "ERROR" "Missing required field: birth_date"
    return 1
  fi

  local birth_time=$(echo "$chart_data" | jq -r '.birth_time // empty')
  if [[ -z "$birth_time" ]]; then
    log_message "ERROR" "Missing required field: birth_time"
    return 1
  fi

  log_message "INFO" "Chart data validated successfully"
  return 0
}

# Function to create a sample chart for testing
create_sample_chart() {
  # Create sample chart data based on Binance-style API
  local sample_chart_data='{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "0.001",
    "price": "50000"
  }'

  log_message "INFO" "Creating sample chart for testing"

  # Validate sample data
  if ! validate_chart_data "$sample_chart_data"; then
    log_message "ERROR" "Sample chart data validation failed"
    return 1
  fi

  # Create the chart
  local chart_id=$(create_chart "$sample_chart_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to create sample chart"
    return 1
  fi

  log_message "INFO" "Sample chart created successfully with ID: $chart_id"
  echo "$chart_id"
  return 0
}

# Function to compare charts
compare_charts() {
  local chart1_id="$1"
  local chart2_id="$2"

  log_message "INFO" "Comparing charts: $chart1_id and $chart2_id"

  # Get both charts
  local chart1=$(get_chart "$chart1_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to retrieve chart 1 with ID: $chart1_id"
    return 1
  fi

  local chart2=$(get_chart "$chart2_id")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to retrieve chart 2 with ID: $chart2_id"
    return 1
  fi

  # Perform comparison (in real implementation, this would be a proper API call)
  # For now, we'll do a basic comparison of key fields
  local chart1_symbol=$(echo "$chart1" | jq -r '.symbol // empty')
  local chart2_symbol=$(echo "$chart2" | jq -r '.symbol // empty')
  local chart1_price=$(echo "$chart1" | jq -r '.price // empty')
  local chart2_price=$(echo "$chart2" | jq -r '.price // empty')

  # Build comparison results
  local comparison="{
    \"chart1_id\": \"$chart1_id\",
    \"chart2_id\": \"$chart2_id\",
    \"differences\": ["

  if [[ "$chart1_symbol" != "$chart2_symbol" ]]; then
    comparison="${comparison}{\"field\": \"symbol\", \"chart1_value\": \"$chart1_symbol\", \"chart2_value\": \"$chart2_symbol\"},"
  fi

  if [[ "$chart1_price" != "$chart2_price" ]]; then
    comparison="${comparison}{\"field\": \"price\", \"chart1_value\": \"$chart1_price\", \"chart2_value\": \"$chart2_price\"},"
  fi

  # Remove trailing comma if any
  comparison="${comparison%,}"

  # Close the JSON object
  comparison="${comparison}]}"

  log_message "INFO" "Chart comparison completed successfully"
  echo "$comparison"
  return 0
}

# Function to run all chart tests
run_chart_tests() {
  log_message "INFO" "Running chart tests"

  # Create a sample chart
  local chart_id=$(create_sample_chart)
  if [[ -z "$chart_id" ]]; then
    log_message "ERROR" "Failed to create sample chart"
    return 1
  fi

  # Get the chart
  local chart_data=$(get_chart "$chart_id")
  if [[ -z "$chart_data" ]]; then
    log_message "ERROR" "Failed to retrieve chart"
    return 1
  fi

  # Update the chart
  local update_data='{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "0.002",
    "price": "51000"
  }'

  local updated_chart=$(update_chart "$chart_id" "$update_data")
  if [[ $? -ne 0 ]]; then
    log_message "ERROR" "Failed to update chart"
    return 1
  fi

  # Extract new chart ID from the update response
  local new_chart_id=$(echo "$updated_chart" | jq -r '.chart_id // empty')

  # If we have both old and new chart IDs, compare them
  if [[ ! -z "$chart_id" && ! -z "$new_chart_id" && "$chart_id" != "$new_chart_id" ]]; then
    local comparison=$(compare_charts "$chart_id" "$new_chart_id")
    if [[ $? -ne 0 ]]; then
      log_message "ERROR" "Failed to compare charts"
      # Not treating this as a test failure
    else
      log_message "INFO" "Chart comparison successful"
    fi
  fi

  # Delete the charts (both original and updated if different)
  if ! delete_chart "$chart_id"; then
    log_message "ERROR" "Failed to delete original chart"
    return 1
  fi

  if [[ ! -z "$new_chart_id" && "$chart_id" != "$new_chart_id" ]]; then
    if ! delete_chart "$new_chart_id"; then
      log_message "ERROR" "Failed to delete updated chart"
      return 1
    fi
  fi

  log_message "INFO" "Chart tests completed successfully"
  return 0
}

# Export functions
export -f create_chart get_chart update_chart delete_chart validate_chart_data create_sample_chart compare_charts run_chart_tests
