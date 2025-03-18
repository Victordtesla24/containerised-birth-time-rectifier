#!/bin/bash

# Validation functions
# Handles input and output validation

# Source common functions if not already sourced
if [[ -z "$LOG_FILE" ]]; then
  source "$(dirname "$0")/common.sh"
fi

# Function to validate JSON data
validate_json() {
  local json_data="$1"
  local schema_file="${2:-}"  # Optional schema file for validation

  # Basic JSON syntax validation
  if ! echo "$json_data" | jq empty >/dev/null 2>&1; then
    log_message "ERROR" "Invalid JSON data: syntax error"
    return 1
  fi

  # Schema validation if a schema file is provided
  if [[ ! -z "$schema_file" && -f "$schema_file" ]]; then
    # This would require ajv-cli or another JSON schema validator
    # For now, just log that we would do schema validation
    log_message "INFO" "Schema validation would be performed with: $schema_file"
  fi

  return 0
}

# Function to validate a date string
validate_date() {
  local date_string="$1"
  local format="${2:-%Y-%m-%dT%H:%M:%S}"  # Default ISO format

  # Try to parse the date
  if ! date -jf "$format" "$date_string" >/dev/null 2>&1; then
    log_message "ERROR" "Invalid date format: $date_string (expected format: $format)"
    return 1
  fi

  return 0
}

# Function to validate a URL
validate_url() {
  local url="$1"

  # Basic URL format validation using a simpler regex to avoid bash issues
  if [[ ! "$url" =~ ^https?:// ]]; then
    log_message "ERROR" "Invalid URL format: $url"
    return 1
  fi

  return 0
}

# Function to validate an email address
validate_email() {
  local email="$1"

  # Basic email format validation using regex
  if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    log_message "ERROR" "Invalid email format: $email"
    return 1
  fi

  return 0
}

# Function to validate geographic coordinates
validate_coordinates() {
  local latitude="$1"
  local longitude="$2"

  # Validate latitude (-90 to 90)
  if ! awk -v lat="$latitude" 'BEGIN {exit !(lat >= -90 && lat <= 90)}'; then
    log_message "ERROR" "Invalid latitude: $latitude (must be between -90 and 90)"
    return 1
  fi

  # Validate longitude (-180 to 180)
  if ! awk -v lon="$longitude" 'BEGIN {exit !(lon >= -180 && lon <= 180)}'; then
    log_message "ERROR" "Invalid longitude: $longitude (must be between -180 and 180)"
    return 1
  fi

  return 0
}

# Function to validate API response against expected schema
validate_api_response() {
  local response="$1"
  local endpoint="$2"

  # Basic validation - check if the response is valid JSON
  if ! validate_json "$response"; then
    return 1
  fi

  # Check for error field in response
  local error=$(echo "$response" | jq -r '.error // empty')
  if [[ ! -z "$error" ]]; then
    log_message "ERROR" "API error in response: $error"
    return 1
  fi

  # Endpoint-specific validation could be added here
  case "$endpoint" in
    "/session/init")
      # Check for session_id field
      local session_id=$(echo "$response" | jq -r '.session_id // empty')
      if [[ -z "$session_id" ]]; then
        log_message "ERROR" "Missing session_id in response"
        return 1
      fi
      ;;
    "/chart/create")
      # Check for chart_id field
      local chart_id=$(echo "$response" | jq -r '.chart_id // empty')
      if [[ -z "$chart_id" ]]; then
        log_message "ERROR" "Missing chart_id in response"
        return 1
      fi
      ;;
    "/questionnaire/create")
      # Check for questionnaire_id field
      local questionnaire_id=$(echo "$response" | jq -r '.questionnaire_id // empty')
      if [[ -z "$questionnaire_id" ]]; then
        log_message "ERROR" "Missing questionnaire_id in response"
        return 1
      fi
      ;;
  esac

  log_message "INFO" "API response validation successful for endpoint: $endpoint"
  return 0
}

# Function to validate command line arguments
validate_arguments() {
  local arg_name="$1"
  local arg_value="$2"
  local arg_type="$3"  # string, number, boolean, etc.

  case "$arg_type" in
    "string")
      # For strings, just check if it's empty
      if [[ -z "$arg_value" ]]; then
        log_message "ERROR" "Argument $arg_name cannot be empty"
        return 1
      fi
      ;;
    "number")
      # Check if it's a valid number
      if ! [[ "$arg_value" =~ ^[0-9]+$ ]]; then
        log_message "ERROR" "Argument $arg_name must be a number"
        return 1
      fi
      ;;
    "boolean")
      # Check if it's a valid boolean
      if [[ "$arg_value" != "true" && "$arg_value" != "false" ]]; then
        log_message "ERROR" "Argument $arg_name must be 'true' or 'false'"
        return 1
      fi
      ;;
    "file")
      # Check if the file exists
      if [[ ! -f "$arg_value" ]]; then
        log_message "ERROR" "File $arg_value does not exist"
        return 1
      fi
      ;;
    "directory")
      # Check if the directory exists
      if [[ ! -d "$arg_value" ]]; then
        log_message "ERROR" "Directory $arg_value does not exist"
        return 1
      fi
      ;;
    *)
      log_message "ERROR" "Unknown argument type: $arg_type"
      return 1
      ;;
  esac

  return 0
}

# Function to validate environment
validate_environment() {
  log_message "INFO" "Validating environment..."

  # Validate required environment variables
  local required_vars=("API_URL")
  local missing_vars=0

  for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
      log_message "ERROR" "Required environment variable $var is not set"
      missing_vars=$((missing_vars + 1))
    fi
  done

  if [[ $missing_vars -gt 0 ]]; then
    log_message "ERROR" "$missing_vars required environment variables are not set"
    return 1
  fi

  log_message "INFO" "Environment validation successful"
  return 0
}

# Export functions
export -f validate_json validate_date validate_url validate_email validate_coordinates validate_api_response validate_arguments validate_environment
