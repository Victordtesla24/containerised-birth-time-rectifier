#!/usr/bin/env bash

# -----------------------------------------------------
# Perplexity API Testing for Three.js Visualization
# -----------------------------------------------------

# Terminal colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
ITALIC='\033[3m'
UNDERLINE='\033[4m'
BLINK='\033[5m'
REVERSE='\033[7m'
RESET='\033[0m'

# Variables
API_KEY="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"
MODEL="sonar-deep-research"
BASE_URL="https://api.perplexity.ai/chat/completions"
SPINNER_PID=""
API_PID=""
RESPONSE_FILE=$(mktemp)
STATUS_PREFIX="${CYAN}[${RESET}"
STATUS_SUFFIX="${CYAN}]${RESET}"
RUN_MODE="menu" # Default mode: 'menu' or 'command'

# Trap cleanup on exit signals
trap cleanup SIGINT SIGTERM EXIT

# Cleanup function
cleanup() {
  stop_spinner
  if [[ -n "$API_PID" ]]; then
    kill -9 "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -f "$RESPONSE_FILE" ]]; then
    rm -f "$RESPONSE_FILE" >/dev/null 2>&1 || true
  fi
  # Clear line and restore cursor
  echo -en "\033[?25h" # Show cursor
  echo -en "\033[2K\r" # Clear line

  # Only print exit message if not part of menu navigation
  if [[ "$1" != "silent" ]]; then
    echo -e "\n${YELLOW}Exiting Perplexity API Test Suite...${RESET}"
  fi

  exit 0
}

# Unified progress display with spinner and progress bar
# Parameters: message, percent, elapsed_time, estimated_total (optional)
unified_progress() {
  local message="$1"
  local percent="${2:-0}"
  local elapsed="$3"
  local total="${4:-0}"
  local spinner_char="${5:-⠋}"
  local width=20
  local filled_width=$(( percent * width / 100 ))

  # Format times
  local elapsed_fmt=$(printf "%02d:%02d" $((elapsed/60)) $((elapsed%60)))
  local remaining_fmt=""

  if [[ $total -gt 0 && $elapsed -lt $total ]]; then
    local remaining=$(( total - elapsed ))
    remaining_fmt=" / $(printf "%02d:%02d" $((remaining/60)) $((remaining%60)))"
  fi

  # Clear current line
  echo -en "\033[2K\r"

  # Draw spinner and progress bar in a unified format
  echo -en "${STATUS_PREFIX} ${spinner_char} ${STATUS_SUFFIX} "
  echo -en "${CYAN}${message}${RESET} "

  # Always show progress bar regardless of percent
  echo -en "["

  # Draw filled portion
  for ((i=0; i<filled_width; i++)); do
    echo -en "${GREEN}■"
  done

  # Draw unfilled portion
  for ((i=filled_width; i<width; i++)); do
    echo -en "${DIM}□${RESET}"
  done

  echo -en "${RESET}] ${percent}% "

  # Add time display
  echo -en "${DIM}${elapsed_fmt}${remaining_fmt}${RESET}"
}

# Advanced spinner animation with progress display
spinner_frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
spinner_message=""

start_spinner() {
  spinner_message="$1"
  local total_time="${2:-0}"

  # Hide cursor
  echo -en "\033[?25l"

  # Initialize spinner
  unified_progress "$spinner_message" 0 0 "$total_time" "${spinner_frames[0]}"

  # Start spinner in background with enhanced display
  {
    local i=0
    local start_time=$(date +%s)

    while true; do
      # Calculate elapsed time
      local current_time=$(date +%s)
      local elapsed=$((current_time - start_time))

      # Calculate percent if total_time is provided
      local percent=0
      if [[ $total_time -gt 0 ]]; then
        percent=$(( elapsed * 100 / total_time ))
        if [[ $percent -gt 100 ]]; then
          percent=100
        fi
      fi

      unified_progress "$spinner_message" "$percent" "$elapsed" "$total_time" "${spinner_frames[i]}"

      i=$(( (i+1) % ${#spinner_frames[@]} ))
      sleep 0.1
    done
  } &

  SPINNER_PID=$!
  disown
}

stop_spinner() {
  if [[ -n "$SPINNER_PID" ]]; then
    kill -9 "$SPINNER_PID" >/dev/null 2>&1 || true
    SPINNER_PID=""

    # Clear line
    echo -en "\033[2K\r"

    # Show cursor
    echo -en "\033[?25h"
  fi
}

update_spinner_message() {
  spinner_message="$1"
}

# Professional progress bar with percentage and elapsed time
show_progress_bar() {
  local duration=$1
  local message=$2
  local start_time=$(date +%s)

  # Start spinner with progress tracking
  start_spinner "$message" "$duration"

  # Sleep for the specified duration with small increments to ensure
  # smooth progress bar updates and responsive spinner animation
  local step=0.1
  local total_steps=$(echo "scale=0; $duration / $step" | bc 2>/dev/null || echo $(($duration * 10)))

  for ((i=1; i<=total_steps; i++)); do
    # Calculate current progress for updating spinner
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    local percent=$((i * 100 / total_steps))

    # Update spinner message with current progress - use arithmetic to check modulo
    if (( i % 5 == 0 )); then  # Update less frequently to reduce flicker
      stop_spinner
      unified_progress "$message" "$percent" "$elapsed" "$duration" "${spinner_frames[$((i % 10))]}"
      # Don't sleep here as the stop/start process takes time already
      start_spinner "$message" "$duration"
    fi

    sleep $step
  done

  # Stop spinner
  stop_spinner

  # Show final status
  local elapsed=$(($(date +%s) - start_time))
  unified_progress "$message" 100 "$elapsed" "$duration" "✓"
  echo # Move to next line
}

# Enhanced API response display with sections and formatting
format_api_response() {
  local response_file=$1
  local title=$2

  if [[ ! -f "$response_file" || ! -s "$response_file" ]]; then
    echo -e "\n${RED}✗${RESET} ${BOLD}API call failed or returned empty response${RESET}"
    return 1
  fi

  # Display header
  echo -e "\n${BLUE}╒═════════════════════════════════════════════════════════════════════════════╕${RESET}"
  echo -e "${BLUE}│${RESET} ${BOLD}${title}${RESET}${BLUE}${RESET}"
  echo -e "${BLUE}╘═════════════════════════════════════════════════════════════════════════════╛${RESET}"

  # Check if jq is available for formatting
  if command -v jq &>/dev/null; then
    # Extract and display content
    echo -e "\n${GREEN}●${RESET} ${BOLD}Response:${RESET}\n"

    # Format main content with simpler formatting to avoid escaping issues
    jq -r '.choices[0].message.content' "$response_file" 2>/dev/null |
      sed 's/^#/\x1b[0;35m#/g' |
      sed 's/```/\x1b[0;33m```/g' |
      sed "s/\*\*/\x1b[1m/g" |
      sed "s/\*\*/\x1b[0m/g" |
      fold -s -w 100 | sed 's/^/   /'

    # Show citations if available
    if jq -e '.citations' "$response_file" >/dev/null 2>&1; then
      echo -e "\n${BLUE}●${RESET} ${BOLD}Citations:${RESET}"
      jq -r '.citations[]' "$response_file" 2>/dev/null | sed 's/^/   - /'
    fi

    # Show token usage if available
    if jq -e '.usage' "$response_file" >/dev/null 2>&1; then
      echo -e "\n${YELLOW}●${RESET} ${BOLD}Token Usage:${RESET}"
      echo -e "   - Prompt tokens: $(jq -r '.usage.prompt_tokens // "N/A"' "$response_file")"
      echo -e "   - Completion tokens: $(jq -r '.usage.completion_tokens // "N/A"' "$response_file")"
      echo -e "   - Total tokens: $(jq -r '.usage.total_tokens // "N/A"' "$response_file")"
    fi
  else
    # Fallback for when jq is not available
    echo -e "\n${YELLOW}⚠️${RESET} ${BOLD}Using basic formatting (install jq for better output)${RESET}\n"
    grep -o '"content":"[^"]*"' "$response_file" | sed 's/"content":"//; s/"$//' | fold -s -w 100 | sed 's/^/   /'
  fi

  echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════════${RESET}"
}

# API call with enhanced progress tracking
call_api() {
  local data=$1
  local message=$2
  local title=$3
  local api_call_complete=false
  local cancel_requested=false
  local start_time=$(date +%s)
  local estimated_time=30 # Estimated time in seconds for API call

  # Start spinner with progress tracking
  start_spinner "$message" "$estimated_time"

  # Make API call in background
  {
    # Send API request
    curl --location "$BASE_URL" \
      --header 'accept: application/json' \
      --header 'content-type: application/json' \
      --header "Authorization: Bearer $API_KEY" \
      --data "$data" \
      --silent \
      --output "$RESPONSE_FILE"

    local curl_exit=$?
    local end_time=$(date +%s)

    # Mark call as complete
    api_call_complete=true

    # Save metadata for display
    echo "$((end_time - start_time))" > "${RESPONSE_FILE}.time"
    echo "$curl_exit" > "${RESPONSE_FILE}.exit"
  } &

  API_PID=$!

  # Allow user to cancel API call
  echo -e "\n${DIM}Press 'q' to cancel the API call${RESET}"

  # Wait for API to complete, checking for user cancellation
  while ! $api_call_complete && kill -0 $API_PID 2>/dev/null; do
    # Check if user pressed 'q' to cancel (non-blocking)
    if read -t 0 -n 1 key; then
      if [[ "$key" == "q" || "$key" == "Q" ]]; then
        cancel_requested=true
        kill -9 $API_PID 2>/dev/null
        break
      fi
    fi

    # Update spinner message with elapsed time
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    update_spinner_message "$message"

    sleep 0.5
  done

  # Stop spinner
  stop_spinner

  # Handle cancellation
  if $cancel_requested; then
    echo -e "\n${YELLOW}⚠️${RESET} ${BOLD}API call cancelled by user${RESET}"
    return 1
  fi

  # Get API call duration and exit code
  local duration=0
  local exit_code=0

  if [[ -f "${RESPONSE_FILE}.time" ]]; then
    duration=$(cat "${RESPONSE_FILE}.time")
  fi

  if [[ -f "${RESPONSE_FILE}.exit" ]]; then
    exit_code=$(cat "${RESPONSE_FILE}.exit")
  fi

  # Display API call summary
  echo -e "\n${GREEN}✓${RESET} ${BOLD}API call completed in ${duration}s with exit code ${exit_code}${RESET}"

  # Format and display the response
  format_api_response "$RESPONSE_FILE" "$title"

  # Clean up metadata files
  rm -f "${RESPONSE_FILE}.time" "${RESPONSE_FILE}.exit" 2>/dev/null

  # Reset API PID
  API_PID=""
}

# Function for initial validation and design patterns
validate_design_patterns() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Running Design Patterns Analysis...${RESET}\n"

  local data='{
  "model": "'$MODEL'",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Three.js developer specializing in high-performance 3D visualizations with a focus on astronomical and celestial rendering. Provide detailed technical solutions that balance visual quality with performance."
    },
    {
      "role": "user",
      "content": "I'm working on enhancing a 3D celestial visualization using Three.js and React Three Fiber. I need to implement high-quality space backgrounds with realistic 3D depth, parallax effects, and optimized performance for planetary systems. Specifically, I'm looking for techniques to create realistic nebula effects with volumetric rendering, improved shooting star/meteor shower systems, and physically accurate planetary rendering with dynamic lighting. Provide code examples with shader implementations that balance visual quality with performance, focusing on techniques like instancing, texture compression, and efficient particle systems."
    }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Analyzing design patterns" "Three.js Design Patterns Analysis"
}

# Function for component-specific error fixing
component_error_fixing() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Running Component Error Analysis...${RESET}\n"

  local data='{
  "model": "'$MODEL'",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Three.js and WebGL developer specializing in shader programming and advanced visual effects. Provide precise technical implementations with code examples."
    },
    {
      "role": "user",
      "content": "I need to implement advanced shader-based effects for a space visualization including: 1) Realistic nebula with volumetric clouds and light scattering, 2) HDR-like glow effects for stars and planets with proper bloom without post-processing, 3) Physically-based atmospheric scattering for planets with day/night transitions, and 4) Advanced particle systems for meteor showers with realistic trails and lighting. Please provide GLSL shader code examples and implementation strategies that work efficiently with Three.js and React Three Fiber, focusing on techniques that don't require heavy post-processing but still achieve high visual quality."
    }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Analyzing component errors" "Three.js Error Resolution Analysis"
}

# Function for parallax background and depth effect research
advanced_background_techniques() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Researching Advanced Background Techniques...${RESET}\n"

  local data='{
    "model": "'$MODEL'",
    "messages": [
      {
        "role": "system",
        "content": "You are an expert Three.js developer specializing in advanced visual effects and rendering techniques. Provide precise, implementation-ready code examples."
      },
      {
        "role": "user",
        "content": "How can I implement layered parallax backgrounds with depth effects using Three.js for a space visualization? I need to create a multi-layered cosmic background using existing space/galaxy images as textures and create realistic depth perception. Focus on techniques that:
        1. Allow multiple background layers with independent movement
        2. Create true 3D depth impression even with 2D image assets
        3. Smoothly integrate with other scene elements like planets and particles
        4. Have minimal performance impact
        5. Can be implemented within an existing React + Three.js (react-three-fiber) application
        Include specific shader code or component implementation examples."
      }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Researching parallax and depth techniques" "Advanced Background & Depth Effects Research"
}

# Function for realistic celestial body rendering research
realistic_celestial_rendering() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Researching Realistic Celestial Rendering...${RESET}\n"

  local data='{
    "model": "'$MODEL'",
    "messages": [
      {
        "role": "system",
        "content": "You are an expert Three.js developer specializing in physically-based rendering and astronomical visualization. Provide precise, implementation-ready code examples."
      },
      {
        "role": "user",
        "content": "What are the most efficient shader techniques for realistic celestial body rendering in Three.js? I need to enhance my existing planet and star visualization with:
        1. More realistic atmospheric effects for planets (scattering, glow, etc.)
        2. Improved surface details with normal/bump mapping
        3. Scientifically accurate lighting models for celestial bodies
        4. Optimized implementations that work well across devices
        5. Integration with existing post-processing effects
        Include specific shader code examples for atmospheres, surface details, and lighting that I can adapt to my existing planet components."
      }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Researching celestial rendering techniques" "Realistic Celestial Body Rendering Research"
}

# Function for Three.js lifecycle management research
threejs_lifecycle_management() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Researching Three.js Lifecycle Management...${RESET}\n"

  local data='{
    "model": "'$MODEL'",
    "messages": [
      {
        "role": "system",
        "content": "You are an expert in Three.js and React integration with deep knowledge of WebGL optimization. Provide precise, implementation-ready code examples."
      },
      {
        "role": "user",
        "content": "What are the best practices for managing Three.js component lifecycles within React to prevent memory leaks and ensure proper cleanup? Focus on:
        1. Proper texture loading, caching, and disposal patterns
        2. Geometry and material cleanup strategies
        3. WebGL context management
        4. Efficient handling of window resize events
        5. Optimized render loop implementation
        Include specific code patterns for React useEffect hooks and cleanup functions that ensure proper resource management within a Three.js visualization."
      }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Researching Three.js lifecycle management" "Three.js React Lifecycle Management Research"
}

# Function for performance testing and optimization
performance_optimization() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Running Performance Optimization Analysis...${RESET}\n"

  local data='{
  "model": "'$MODEL'",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Three.js performance optimization specialist with extensive experience in complex astronomical visualizations. Provide detailed technical implementations with measurable improvements."
    },
    {
      "role": "user",
      "content": "I need to optimize a complex Three.js celestial visualization featuring multiple planets with realistic textures and atmospheres, particle-based nebula clouds, and dynamic shooting star systems. The application currently suffers from frame rate drops on mid-range devices. Provide specific optimization techniques for: 1) Efficient instancing for particle systems, 2) Level-of-detail strategies for planets at different distances, 3) Smart texture loading and management with progressive enhancement, 4) Advanced culling techniques for off-screen objects, and 5) GPU-efficient shader approaches for nebula effects. Include code examples and metrics for measuring improvements at each stage."
    }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Analyzing performance strategies" "Three.js Performance Optimization"
}

# Function for cross-browser compatibility validation
cross_browser_compatibility() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Running Cross-Browser Compatibility Analysis...${RESET}\n"

  local data='{
  "model": "'$MODEL'",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert in WebGL, Three.js and React Three Fiber. Provide innovative solutions for advanced 3D effects with a focus on astronomical visualizations."
    },
    {
      "role": "user",
      "content": "I'm creating an immersive space visualization and need techniques for implementing these advanced effects: 1) Parallax star fields where distant stars move differently than closer ones when the camera moves, 2) Realistic celestial lens flares without using sprites, implemented in GLSL, 3) Physically accurate planetary rings with proper transparency and light scattering, 4) Animated aurora effects for Earth-like planets using vertex displacement and color shifting in shaders, and 5) Gas giant atmosphere simulation with dynamic cloud band movement. Provide implementation approaches with React Three Fiber code examples and shader code that balance visual quality with performance, especially for techniques that create depth and immersion."
    }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.9,
    "frequency_penalty": 1
  }'

  call_api "$data" "Analyzing cross-browser strategies" "Three.js Cross-Browser Compatibility"
}

# Run all tests sequentially
run_all_tests() {
  clear
  echo -e "\n${MAGENTA}${BOLD}Running All Tests Sequentially...${RESET}\n"

  validate_design_patterns
  component_error_fixing
  performance_optimization
  cross_browser_compatibility
  advanced_background_techniques
  realistic_celestial_rendering
  threejs_lifecycle_management
}

# Enhanced interactive menu with dynamic highlighting
show_menu() {
  local running=true

  while $running; do
    # Reset selected option
    local selected=1
    local options=(
      "Design Patterns Analysis"
      "Component Error Analysis"
      "Performance Optimization"
      "Cross-Browser Compatibility"
      "Advanced Background Techniques"
      "Realistic Celestial Rendering"
      "Three.js Lifecycle Management"
      "Run All Tests"
      "Quit"
    )
    local option_count=${#options[@]}

    # Function to render menu
    render_menu() {
      local idx=$1
      clear

      # Draw header
      echo -e "${BLUE}╒═════════════════════════════════════════════════════════════════════════════╕${RESET}"
      echo -e "${BLUE}│${RESET} ${BOLD}${CYAN}           Perplexity API Testing for Three.js Visualization           ${RESET}${BLUE}│${RESET}"
      echo -e "${BLUE}╘═════════════════════════════════════════════════════════════════════════════╛${RESET}"

      echo -e "\n${BOLD}Choose an option:${RESET}\n"

      # Draw options
      for i in "${!options[@]}"; do
        if [[ $i -eq $((idx-1)) ]]; then
          # Highlighted option
          echo -e "  ${REVERSE}${BOLD}[$((i+1))] ${options[$i]}${RESET}"
        else
          # Normal option
          echo -e "  ${CYAN}[$((i+1))]${RESET} ${options[$i]}"
        fi
      done

      # Draw footer
      echo -e "\n${BLUE}═════════════════════════════════════════════════════════════════════════════${RESET}"
      echo -e "${DIM}Use arrow keys ↑/↓ to navigate, Enter to select, or press 1-6 directly${RESET}"
    }

    # Initial menu render
    render_menu $selected

    # Wait for user input
    local key_pressed=false
    while ! $key_pressed; do
      read -rsn1 key

      # Handle input
      case "$key" in
        $'\x1b') # Arrow keys sequence start
          read -rsn1 -t 0.1 key
          if [[ "$key" == "[" ]]; then
            read -rsn1 -t 0.1 key
            case "$key" in
              A) # Up arrow
                ((selected--))
                if [[ $selected -lt 1 ]]; then
                  selected=$option_count
                fi
                render_menu $selected
                ;;
              B) # Down arrow
                ((selected++))
                if [[ $selected -gt $option_count ]]; then
                  selected=1
                fi
                render_menu $selected
                ;;
            esac
          fi
          ;;
        "") # Enter key
          key_pressed=true
          ;;
        [1-6]) # Direct number selection
          selected=$key
          render_menu $selected
          key_pressed=true
          ;;
      esac
    done

    # Process selection
    case $selected in
      1)
        validate_design_patterns
        ;;
      2)
        component_error_fixing
        ;;
      3)
        performance_optimization
        ;;
      4)
        cross_browser_compatibility
        ;;
      5)
        advanced_background_techniques
        ;;
      6)
        realistic_celestial_rendering
        ;;
      7)
        threejs_lifecycle_management
        ;;
      8)
        run_all_tests
        ;;
      9)
        running=false
        cleanup "silent"
        break
        ;;
      *)
        echo -e "\n${RED}Invalid option.${RESET}"
        sleep 1
        continue
        ;;
    esac

    # After running a test, wait for user to press a key before returning to menu
    if $running; then
      echo -e "\n${YELLOW}Press any key to return to the menu...${RESET}"
      read -rsn1
    fi
  done
}

# Run a specific test by name (for command line arguments)
run_test() {
  case "$1" in
    "design")
      validate_design_patterns
      ;;
    "error")
      component_error_fixing
      ;;
    "performance")
      performance_optimization
      ;;
    "browser")
      cross_browser_compatibility
      ;;
    *)
      echo -e "${RED}Unknown test: $1${RESET}"
      echo -e "${YELLOW}Available tests: design, error, performance, browser${RESET}"
      exit 1
      ;;
  esac
}

# Check for required tools
check_dependencies() {
  local missing_tools=()

  # Check for curl
  if ! command -v curl &>/dev/null; then
    missing_tools+=("curl")
  fi

  # Check for optional dependencies
  if ! command -v jq &>/dev/null; then
    echo -e "${YELLOW}⚠️  jq is not installed. API responses will have limited formatting.${RESET}"
    echo -e "${DIM}Install jq for better output: brew install jq${RESET}"
  fi

  if ! command -v bc &>/dev/null; then
    echo -e "${YELLOW}⚠️  bc is not installed. Using integer math fallbacks.${RESET}"
    echo -e "${DIM}Install bc for better progress calculations: brew install bc${RESET}"
  fi

  # Exit if essential tools are missing
  if [[ ${#missing_tools[@]} -gt 0 ]]; then
    echo -e "${RED}Error: The following required tools are missing:${RESET}"
    for tool in "${missing_tools[@]}"; do
      echo -e "${RED}  - $tool${RESET}"
    done
    echo -e "${YELLOW}Please install these tools and try again.${RESET}"
    exit 1
  fi
}

# Display welcome splash screen
show_splash() {
  clear
  echo -e "${BLUE}╒═════════════════════════════════════════════════════════════════════════════╕${RESET}"
  echo -e "${BLUE}│${RESET}                                                                         ${BLUE}│${RESET}"
  echo -e "${BLUE}│${RESET}  ${BOLD}${CYAN}  Perplexity API Testing for Three.js Visualization  ${RESET}              ${BLUE}│${RESET}"
  echo -e "${BLUE}│${RESET}                                                                         ${BLUE}│${RESET}"
  echo -e "${BLUE}│${RESET}  ${DIM}A comprehensive testing suite for Three.js components using Perplexity API${RESET}  ${BLUE}│${RESET}"
  echo -e "${BLUE}│${RESET}                                                                         ${BLUE}│${RESET}"
  echo -e "${BLUE}╘═════════════════════════════════════════════════════════════════════════════╛${RESET}"

  echo -e "\n${DIM}Initializing...${RESET}"

  # Simulate loading with the unified progress display
  show_progress_bar 2 "Loading API Testing Environment"

  echo -e "\n${GREEN}✓${RESET} ${BOLD}Testing environment ready!${RESET}"
  sleep 0.5
}

# Main entry point
main() {
  # Check dependencies
  check_dependencies

  # Process arguments
  if [ $# -eq 0 ]; then
    # Show splash screen with shortened initialization time
    show_splash

    # No arguments, show interactive menu without making API calls yet
    RUN_MODE="menu"
    show_menu
  else
    # Show splash screen
    show_splash

    # Run specific test from command line
    RUN_MODE="command"
    run_test "$1"
  fi
}

# Launch the script
main "$@"
