#!/bin/bash

# Interactive Birth Chart Script
# Captures user input for birth details and interacts with the Birth Time Rectifier API

# Get the directory of this script
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Use Birth Time Rectifier API v1 endpoints
API_URL="http://localhost:9000/api/v1"
WS_URL="ws://localhost:9000/ws/v1"

# Source library modules
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/api_client.sh"
source "$SCRIPT_DIR/lib/websocket_client.sh"

# Function to display the main menu
display_main_menu() {
  clear
  echo "========================================="
  echo "    Birth Time Rectifier - Main Menu     "
  echo "========================================="
  echo "1. Create a new birth chart"
  echo "2. View existing chart"
  echo "3. Update a chart"
  echo "4. Compare two charts"
  echo "5. Real-time chart monitoring (WebSocket)"
  echo "6. Answer birth time questionnaire"
  echo "0. Exit"
  echo "-----------------------------------------"
  read -p "Enter your choice (0-6): " menu_choice

  case "$menu_choice" in
    1) create_interactive_chart ;;
    2) view_interactive_chart ;;
    3) update_interactive_chart ;;
    4) compare_interactive_charts ;;
    5) realtime_chart_monitoring ;;
    6) birth_time_questionnaire ;;
    0) echo "Exiting program. Goodbye!"; exit 0 ;;
    *) echo "Invalid choice. Press Enter to continue..."; read; display_main_menu ;;
  esac
}

# Function to create a new birth chart with interactive input
create_interactive_chart() {
  clear
  echo "========================================="
  echo "    Create a New Birth Chart             "
  echo "========================================="

  # Collect user input
  read -p "Enter name: " name
  read -p "Enter birth date (YYYY-MM-DD): " birth_date
  read -p "Enter birth time (HH:MM): " birth_time
  read -p "Enter birth location: " location
  read -p "Enter latitude: " latitude
  read -p "Enter longitude: " longitude

  # Create chart data
  local chart_data="{
    \"name\": \"$name\",
    \"birth_date\": \"$birth_date\",
    \"birth_time\": \"$birth_time\",
    \"latitude\": $latitude,
    \"longitude\": $longitude,
    \"location\": \"$location\"
  }"

  # Call the API to create the chart
  echo "Creating chart with the Birth Time Rectifier API..."

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      echo "Failed to initialize session. Press Enter to return to main menu..."
      read
      display_main_menu
      return
    fi
  fi

  # Create the chart using the API
  local response=$(api_request "POST" "/chart" "$chart_data")
  if [[ $? -ne 0 ]]; then
    echo "Failed to create chart. API Error."
    echo "$response"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  # Extract chart ID from response
  local chart_id=$(echo "$response" | jq -r '.chart_id // empty')
  if [[ -z "$chart_id" ]]; then
    echo "Failed to extract chart ID from response."
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  echo "Chart created successfully with ID: $chart_id"
  echo "Press Enter to return to main menu..."
  read
  display_main_menu
}

# Function to view an existing chart
view_interactive_chart() {
  clear
  echo "========================================="
  echo "    View Existing Chart                  "
  echo "========================================="

  read -p "Enter chart ID: " chart_id

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      echo "Failed to initialize session. Press Enter to return to main menu..."
      read
      display_main_menu
      return
    fi
  fi

  # Get the chart data using the API
  local response=$(api_request "GET" "/chart/$chart_id" "{}")
  if [[ $? -ne 0 ]]; then
    echo "Failed to retrieve chart. API Error."
    echo "$response"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  # Display chart data
  echo "Chart Details:"
  echo "------------------------------------------"
  echo "Name: $(echo "$response" | jq -r '.name')"
  echo "Birth Date: $(echo "$response" | jq -r '.birth_date')"
  echo "Birth Time: $(echo "$response" | jq -r '.birth_time')"
  echo "Location: $(echo "$response" | jq -r '.location')"
  echo "Latitude: $(echo "$response" | jq -r '.latitude')"
  echo "Longitude: $(echo "$response" | jq -r '.longitude')"
  echo "------------------------------------------"

  if [[ $(echo "$response" | jq 'has("planetary_positions")') == "true" ]]; then
    echo "Planetary Positions:"
    echo "$response" | jq -r '.planetary_positions[] | "\(.planet): \(.sign) \(.degree)°"'
  fi

  echo "Press Enter to return to main menu..."
  read
  display_main_menu
}

# Function to update an existing chart
update_interactive_chart() {
  clear
  echo "========================================="
  echo "    Update Existing Chart                "
  echo "========================================="

  read -p "Enter chart ID to update: " chart_id

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      echo "Failed to initialize session. Press Enter to return to main menu..."
      read
      display_main_menu
      return
    fi
  fi

  # Get the current chart data
  local current_data=$(api_request "GET" "/chart/$chart_id" "{}")
  if [[ $? -ne 0 ]]; then
    echo "Failed to retrieve chart. API Error."
    echo "$current_data"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  # Extract current values
  local current_name=$(echo "$current_data" | jq -r '.name')
  local current_birth_date=$(echo "$current_data" | jq -r '.birth_date')
  local current_birth_time=$(echo "$current_data" | jq -r '.birth_time')
  local current_location=$(echo "$current_data" | jq -r '.location')
  local current_latitude=$(echo "$current_data" | jq -r '.latitude')
  local current_longitude=$(echo "$current_data" | jq -r '.longitude')

  # Display current values and get new values
  echo "Current name: $current_name"
  read -p "Enter new name (leave empty to keep current): " name
  name=${name:-"$current_name"}

  echo "Current birth date: $current_birth_date"
  read -p "Enter new birth date (YYYY-MM-DD) (leave empty to keep current): " birth_date
  birth_date=${birth_date:-"$current_birth_date"}

  echo "Current birth time: $current_birth_time"
  read -p "Enter new birth time (HH:MM) (leave empty to keep current): " birth_time
  birth_time=${birth_time:-"$current_birth_time"}

  echo "Current location: $current_location"
  read -p "Enter new location (leave empty to keep current): " location
  location=${location:-"$current_location"}

  echo "Current latitude: $current_latitude"
  read -p "Enter new latitude (leave empty to keep current): " latitude
  latitude=${latitude:-"$current_latitude"}

  echo "Current longitude: $current_longitude"
  read -p "Enter new longitude (leave empty to keep current): " longitude
  longitude=${longitude:-"$current_longitude"}

  # Create update data
  local update_data="{
    \"name\": \"$name\",
    \"birth_date\": \"$birth_date\",
    \"birth_time\": \"$birth_time\",
    \"latitude\": $latitude,
    \"longitude\": $longitude,
    \"location\": \"$location\"
  }"

  # Update the chart using the API
  local response=$(api_request "PUT" "/chart/$chart_id" "$update_data")
  if [[ $? -ne 0 ]]; then
    echo "Failed to update chart. API Error."
    echo "$response"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  echo "Chart updated successfully."
  echo "Press Enter to return to main menu..."
  read
  display_main_menu
}

# Function to compare two charts
compare_interactive_charts() {
  clear
  echo "========================================="
  echo "    Compare Two Charts                   "
  echo "========================================="

  read -p "Enter first chart ID: " chart1_id
  read -p "Enter second chart ID: " chart2_id
  read -p "Enter comparison type (synastry/composite): " comparison_type

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      echo "Failed to initialize session. Press Enter to return to main menu..."
      read
      display_main_menu
      return
    fi
  fi

  # Call the API to compare the charts
  local response=$(api_request "GET" "/chart/compare?chart1_id=$chart1_id&chart2_id=$chart2_id&comparison_type=$comparison_type" "{}")
  if [[ $? -ne 0 ]]; then
    echo "Failed to compare charts. API Error."
    echo "$response"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  # Display comparison results
  echo "Chart Comparison Results:"
  echo "------------------------------------------"
  if [[ $(echo "$response" | jq 'has("aspects")') == "true" ]]; then
    echo "Significant Aspects:"
    echo "$response" | jq -r '.aspects[] | "\(.planet1) \(.aspect) \(.planet2) (\(.orb)°)"'
  fi

  if [[ $(echo "$response" | jq 'has("compatibility_score")') == "true" ]]; then
    echo "Compatibility Score: $(echo "$response" | jq -r '.compatibility_score') / 10"
  fi

  echo "------------------------------------------"
  echo "Press Enter to return to main menu..."
  read
  display_main_menu
}

# Function for real-time chart monitoring using WebSocket
realtime_chart_monitoring() {
  clear
  echo "========================================="
  echo "    Real-time Chart Monitoring           "
  echo "========================================="

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      echo "Failed to initialize session. Press Enter to return to main menu..."
      read
      display_main_menu
      return
    fi
  fi

  echo "Establishing WebSocket connection for real-time updates..."

  # Connect to the WebSocket
  if ! connect_websocket "charts"; then
    echo "Failed to establish WebSocket connection."
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  echo "WebSocket connection established."
  echo "Subscribing to chart updates..."

  # Subscribe to chart updates
  local subscribe_msg="{\"action\":\"subscribe\",\"channel\":\"chart_updates\"}"
  if ! send_websocket_message "$subscribe_msg"; then
    echo "Failed to subscribe to chart updates."
    close_websocket
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  echo "Subscribed to chart updates."
  echo "Waiting for real-time updates... (Press Ctrl+C to stop)"

  # Monitor for WebSocket messages
  trap "echo 'Closing WebSocket connection...'; close_websocket; echo 'Press Enter to return to main menu...'; read; display_main_menu; return" INT

  while true; do
    read_websocket_messages 10
    sleep 1
  done
}

# Function for birth time questionnaire
birth_time_questionnaire() {
  clear
  echo "========================================="
  echo "    Birth Time Questionnaire             "
  echo "========================================="

  # Initialize session if not already done
  if [[ -z "$SESSION_TOKEN" ]]; then
    if ! init_session; then
      echo "Failed to initialize session. Press Enter to return to main menu..."
      read
      display_main_menu
      return
    fi
  fi

  # Get the questionnaire structure from the API
  local questionnaire=$(api_request "GET" "/questionnaire/birth-time" "{}")
  if [[ $? -ne 0 ]]; then
    echo "Failed to retrieve questionnaire. API Error."
    echo "$questionnaire"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  # Initialize answers object
  local answers="{\"answers\":["

  # Parse questions and get user answers
  local questions_count=$(echo "$questionnaire" | jq '.questions | length')

  for (( i=0; i<questions_count; i++ )); do
    local question_id=$(echo "$questionnaire" | jq -r ".questions[$i].id")
    local question_text=$(echo "$questionnaire" | jq -r ".questions[$i].label")
    local question_type=$(echo "$questionnaire" | jq -r ".questions[$i].type")
    local required=$(echo "$questionnaire" | jq -r ".questions[$i].required")

    echo "Question $((i+1))/$questions_count: $question_text"
    if [[ "$required" == "true" ]]; then
      echo "(Required)"
    fi

    case "$question_type" in
      "date")
        read -p "Enter date (YYYY-MM-DD): " date_answer
        answers="${answers}{\"questionId\":\"$question_id\",\"date\":\"$date_answer\"},"
        ;;
      "time")
        read -p "Enter time (HH:MM): " time_answer
        answers="${answers}{\"questionId\":\"$question_id\",\"time\":\"$time_answer\"},"
        ;;
      "location")
        read -p "Enter location name: " location_name
        read -p "Enter latitude: " lat
        read -p "Enter longitude: " lng
        answers="${answers}{\"questionId\":\"$question_id\",\"latitude\":$lat,\"longitude\":$lng,\"name\":\"$location_name\"},"
        ;;
      "multiple_choice")
        # Get and display options
        local options_count=$(echo "$questionnaire" | jq ".questions[$i].options | length")
        for (( j=0; j<options_count; j++ )); do
          local option_id=$(echo "$questionnaire" | jq -r ".questions[$i].options[$j].id")
          local option_label=$(echo "$questionnaire" | jq -r ".questions[$i].options[$j].label")
          echo "$((j+1)). $option_label"
        done

        read -p "Enter your choice (1-$options_count): " choice_num
        local choice_index=$((choice_num-1))
        if [[ $choice_index -ge 0 && $choice_index -lt $options_count ]]; then
          local option_id=$(echo "$questionnaire" | jq -r ".questions[$i].options[$choice_index].id")
          answers="${answers}{\"questionId\":\"$question_id\",\"answerId\":\"$option_id\"},"
        else
          echo "Invalid choice. Skipping question."
          continue
        fi
        ;;
      "text")
        read -p "Enter your answer: " text_answer
        answers="${answers}{\"questionId\":\"$question_id\",\"text\":\"$text_answer\"},"
        ;;
      *)
        read -p "Enter your answer: " generic_answer
        answers="${answers}{\"questionId\":\"$question_id\",\"value\":\"$generic_answer\"},"
        ;;
    esac

    echo "------------------------------------------"
  done

  # Remove trailing comma and close the JSON object
  answers="${answers%,}]}"

  # Submit answers to the API
  echo "Submitting your answers..."
  local submission_response=$(api_request "POST" "/questionnaire/birth-time/submit" "$answers")
  if [[ $? -ne 0 ]]; then
    echo "Failed to submit answers. API Error."
    echo "$submission_response"
    echo "Press Enter to return to main menu..."
    read
    display_main_menu
    return
  fi

  # Check for recommendation
  if [[ $(echo "$submission_response" | jq 'has("recommendation")') == "true" ]]; then
    echo "Based on your answers, we recommend the following birth time:"
    echo "Recommended birth time: $(echo "$submission_response" | jq -r '.recommendation.birth_time')"
    echo "Confidence level: $(echo "$submission_response" | jq -r '.recommendation.confidence') / 10"
  fi

  echo "Thank you for completing the questionnaire."
  echo "Press Enter to return to main menu..."
  read
  display_main_menu
}

# Main function
main() {
  # Welcome message
  clear
  echo "========================================="
  echo "  Welcome to Birth Time Rectifier Tool   "
  echo "========================================="
  echo "This interactive tool allows you to work with"
  echo "birth charts and birth time rectification."
  echo ""

  # Start the main menu
  display_main_menu
}

# Run the main function
main
