#!/bin/bash

# Source library modules
source "$(dirname "$0")/lib/common.sh"
source "$(dirname "$0")/lib/api_client.sh"
source "$(dirname "$0")/lib/chart_operations.sh"

# Initialize session
init_session

# Create a sample chart and print the raw output
echo "=== Testing create_sample_chart ==="
chart_id=$(create_sample_chart)
echo "Raw chart_id output: '$chart_id'"
echo "Length: ${#chart_id}"

# Validate the chart_id format
if [[ "$chart_id" =~ ^chrt_[a-zA-Z0-9]+$ ]]; then
  echo "Chart ID format is valid: $chart_id"
else
  echo "Chart ID format is INVALID: $chart_id"
fi

# Try to create a questionnaire with this chart_id
echo -e "\n=== Testing questionnaire creation ==="
questionnaire_data="{\"chart_id\": \"$chart_id\"}"
echo "Request data: $questionnaire_data"
questionnaire_response=$(api_request "POST" "/questionnaire" "$questionnaire_data")
echo "Response: $questionnaire_response"

# Try to extract questionnaire ID
questionnaire_id=$(echo "$questionnaire_response" | jq -r '.id // .questionnaire_id // empty')
if [[ -z "$questionnaire_id" ]]; then
  echo "Failed to extract questionnaire ID"
  echo "Available fields: $(echo "$questionnaire_response" | jq 'keys')"
else
  echo "Questionnaire ID: $questionnaire_id"
fi
