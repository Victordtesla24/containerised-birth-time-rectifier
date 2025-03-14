#!/bin/bash

# terminal_ui.sh - Advanced Terminal UI Components for Shell Scripts
# Features:
# - Dynamic spinners with multiple styles
# - Progress bars with percentage, elapsed time and ETA
# - Status indicators
# - Color themes and terminal compatibility
# - Single-line display that updates in place

# Ensure script is sourced, not executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "ERROR: This script should be sourced, not executed directly."
  echo "Usage: source ${BASH_SOURCE[0]}"
  exit 1
fi

# Terminal capabilities and settings
# Check if running in a TTY (interactive terminal)
is_tty() {
  # Check for FORCE_TTY environment variable which can be set by the cleanup script
  if [ "$FORCE_TTY" = "true" ]; then
    return 0 # Force TTY mode
  fi

  # Standard TTY detection
  if [ -t 1 ]; then
    return 0  # True - it's a TTY
  else
    return 1  # False - not a TTY
  fi
}

# Handle specific environments (like cleanup script)
if [ "$RUNNING_IN_CLEANUP_SCRIPT" = "true" ]; then
  # When running in cleanup script, adjust terminal detection
  FORCE_ANIMATION=true
  echo "DEBUG: Running in cleanup script - adjusted terminal settings" >&2
fi

# Set terminal capability variables
readonly TERM_SUPPORTS_COLOR=$(tput colors 2>/dev/null || echo 0)
readonly TERM_COLS=$(tput cols 2>/dev/null || echo 80)
readonly CURSOR_UP="\033[1A"
readonly CURSOR_DOWN="\033[1B"
readonly CURSOR_HIDE="\033[?25l"
readonly CURSOR_SHOW="\033[?25h"
readonly ERASE_LINE="\033[2K"

# Color definitions (if terminal supports colors)
if [[ "$TERM_SUPPORTS_COLOR" -ge 8 ]]; then
  readonly COLOR_RESET="\033[0m"
  readonly COLOR_BLACK="\033[0;30m"
  readonly COLOR_RED="\033[0;31m"
  readonly COLOR_GREEN="\033[0;32m"
  readonly COLOR_YELLOW="\033[0;33m"
  readonly COLOR_BLUE="\033[0;34m"
  readonly COLOR_PURPLE="\033[0;35m"
  readonly COLOR_CYAN="\033[0;36m"
  readonly COLOR_WHITE="\033[0;37m"
  readonly COLOR_BOLD="\033[1m"
  readonly COLOR_DIM="\033[2m"
else
  readonly COLOR_RESET=""
  readonly COLOR_BLACK=""
  readonly COLOR_RED=""
  readonly COLOR_GREEN=""
  readonly COLOR_YELLOW=""
  readonly COLOR_BLUE=""
  readonly COLOR_PURPLE=""
  readonly COLOR_CYAN=""
  readonly COLOR_WHITE=""
  readonly COLOR_BOLD=""
  readonly COLOR_DIM=""
fi

# Check if running in a TTY (interactive terminal)
is_tty() {
  # Check for FORCE_TTY environment variable which can be set by the cleanup script
  if [ "$FORCE_TTY" = "true" ]; then
    return 0 # Force TTY mode
  fi

  # Standard TTY detection
  if [ -t 1 ]; then
    return 0  # True - it's a TTY
  else
    return 1  # False - not a TTY
  fi
}

# Set terminal capability variables
check_terminal_capabilities() {
  # Default to basic mode (compatible with all shells)
  SHELL_ADVANCED_FEATURES=false
  SHELL_VERSION=""
  ANIMATION_ENABLED=true
  TERMINAL_TYPE=$(printenv TERM 2>/dev/null || echo "unknown")
  SUPPORTS_UNICODE=false

  # Check if we're in a real terminal
  if ! is_tty; then
    # Override animation disabled if FORCE_ANIMATION is set
    if [ "$FORCE_ANIMATION" = "true" ]; then
      ANIMATION_ENABLED=true
      echo "Animation enabled by force" >&2
    else
      ANIMATION_ENABLED=false
      echo "Non-interactive terminal detected - animations disabled" >&2
    fi
    return
  fi

  # Try to detect bash version
  if command -v bash >/dev/null 2>&1; then
    # Get bash version safely
    SHELL_VERSION=$(bash --version | head -n 1 | grep -o '[0-9]\+\.[0-9]\+' | head -n 1 || echo "")

    # Check for bash 4+ for advanced features
    if [[ -n "$SHELL_VERSION" ]]; then
      BASH_MAJOR_VERSION=$(echo "$SHELL_VERSION" | cut -d. -f1)
      if [[ "$BASH_MAJOR_VERSION" -ge 4 ]]; then
        SHELL_ADVANCED_FEATURES=true
      fi
    fi
  fi

  # Check for Unicode support in terminal
  if [[ "$TERMINAL_TYPE" == *"256color"* || "$TERMINAL_TYPE" == "xterm-color" || "$TERMINAL_TYPE" == "screen" ]]; then
    SUPPORTS_UNICODE=true
  fi

  # Detect if we're running under sudo (affects terminal behavior)
  SUDO_ACTIVE=false
  if [[ -n "$SUDO_USER" ]]; then
    SUDO_ACTIVE=true
  fi

  # Detect macOS Terminal.app specifically (has some quirks)
  IS_MACOS_TERMINAL=false
  if [[ "$(uname)" == "Darwin" && -z "$SSH_TTY" ]]; then
    IS_MACOS_TERMINAL=true
  fi

  # Set animation delay based on terminal type - use much longer delays
  SPINNER_DELAY=0.3

  if $SUDO_ACTIVE && $IS_MACOS_TERMINAL; then
    # Under sudo on macOS, use even slower animations
    SPINNER_DELAY=0.5
    echo "SUPER HIGH VISIBILITY MODE ENABLED FOR SUDO"
  fi

  # Output capability info
  echo "Shell version detected: ${SHELL_VERSION:-unknown}"
  if $SHELL_ADVANCED_FEATURES; then
    echo "Advanced shell features available"
  else
    echo "Using basic shell mode for maximum compatibility"
  fi

  # Special case: running under sudo on macOS
  if $SUDO_ACTIVE && $IS_MACOS_TERMINAL; then
    echo "Running under sudo on macOS - using enhanced compatibility mode"
  fi
}

# Run terminal capability detection
check_terminal_capabilities

# Extreme measures for output flushing
# This function will be called repeatedly to ensure unbuffered output
force_terminal_update() {
  # Try different methods to force terminal update
  # Try stdbuf if available
  stdbuf -o0 true 2>/dev/null || true

  # Force flush using printf
  printf "" > /dev/tty 2>/dev/null || true

  # Small sleep to allow terminal to update
  sleep 0.01
}

# Set basic default spinner style that works everywhere
DEFAULT_SPINNER="[>  ] [=>  ] [==>  ] [===> ]"

# Function to get spinner frames based on selected style
get_spinner_frames() {
  # For macOS under sudo, use super simple visible frames
  if $SUDO_ACTIVE && $IS_MACOS_TERMINAL; then
    echo "[>] [->] [-->] [--->] [---->]"
    return
  fi

  # Otherwise use default spinner
  echo "$DEFAULT_SPINNER"
}

# Default settings
SPINNER_STYLE="default"
PROGRESS_BAR_WIDTH=40
PROGRESS_BAR_CHAR="█"
PROGRESS_BAR_BG_CHAR="░"
UI_THEME="default"
UI_LAST_UPDATE=0
UI_MIN_UPDATE_INTERVAL=0.05  # Prevent too frequent updates
UI_ACTIVE=false
UI_COMPONENT=""
UI_START_TIME=0

# Global state variables
declare -i _spinner_idx=0
declare -i _progress_percent=0
declare -i _progress_total=100
declare _spinner_message=""
declare _progress_message=""
declare _spinner_color="$COLOR_CYAN"
declare _progress_color="$COLOR_BLUE"
declare _spinner_pid=""
declare _last_line=""
declare _current_frame=""

# Theme settings - modified to work without associative arrays
THEME_DEFAULT="${COLOR_CYAN}|${COLOR_BLUE}|${COLOR_GREEN}|${COLOR_WHITE}"
THEME_COOL="${COLOR_BLUE}|${COLOR_CYAN}|${COLOR_PURPLE}|${COLOR_WHITE}"
THEME_WARM="${COLOR_RED}|${COLOR_YELLOW}|${COLOR_GREEN}|${COLOR_WHITE}"
THEME_MINIMAL="${COLOR_WHITE}|${COLOR_WHITE}|${COLOR_WHITE}|${COLOR_WHITE}"
THEME_DRAMATIC="${COLOR_RED}|${COLOR_YELLOW}|${COLOR_RED}|${COLOR_YELLOW}"

# Apply a theme
apply_theme() {
  local theme="${1:-default}"
  local theme_value=""

  # Select the theme based on name
  case "$theme" in
    cool)
      theme_value="$THEME_COOL"
      ;;
    warm)
      theme_value="$THEME_WARM"
      ;;
    minimal)
      theme_value="$THEME_MINIMAL"
      ;;
    dramatic)
      theme_value="$THEME_DRAMATIC"
      ;;
    *)
      # Default theme
      theme_value="$THEME_DEFAULT"
      ;;
  esac

  IFS='|' read -r _spinner_color _progress_color _success_color _message_color <<< "$theme_value"
  UI_THEME="$theme"
}

# Helper function to get current time in milliseconds
get_current_time_ms() {
  echo $(($(date +%s%N)/1000000))
}

# Helper function to format time (seconds) to MM:SS
format_time() {
  local total_seconds=$1
  local minutes=$((total_seconds / 60))
  local seconds=$((total_seconds % 60))
  printf "%02d:%02d" "$minutes" "$seconds"
}

# Force terminal to use unbuffered output - multiple techniques
force_unbuffered_output() {
  # Try to disable local echoing
  stty -echo 2>/dev/null || true

  # Force stdout to be line-buffered
  stdbuf -oL true >/dev/null 2>&1 || true

  # For macOS, try to force immediate output
  if $IS_MACOS_TERMINAL; then
    # Force flush the output buffer
    printf "" > /dev/tty 2>/dev/null || true
  fi

  # Force short delay to allow terminal to update
  sleep 0.05
}

# Override standard echo with direct terminal output
# This helps with animations in subshells
direct_echo() {
  # First try to write directly to terminal
  echo -ne "$1" > /dev/tty 2>/dev/null || echo -ne "$1"

  # Force update to ensure animation works in all terminals
  force_terminal_update
}

# Display a spinner with optional message - completely rewritten for extreme visibility
# Usage: show_spinner "Loading..."
show_spinner() {
  UI_ACTIVE=true
  UI_COMPONENT="spinner"
  _spinner_message="${1:-Processing...}"
  UI_START_TIME=$(date +%s)

  # No animation in non-interactive mode, but check for force override
  if ! $ANIMATION_ENABLED && [ "$FORCE_ANIMATION" != "true" ]; then
    echo ">> $_spinner_message"
    return
  fi

  # Force unbuffered output for better animation
  force_unbuffered_output

  # Hide cursor (only in TTY)
  direct_echo "$CURSOR_HIDE"

  # Ensure we're not already running a spinner
  if [[ -n "$_spinner_pid" ]]; then
    kill $_spinner_pid &>/dev/null || true
    wait $_spinner_pid &>/dev/null || true
    _spinner_pid=""
  fi

  # Reset state
  _spinner_idx=0
  _last_line=""
  _current_frame=""

  # DIRECT ANIMATION - no background processes, much more reliable
  # Get frames for spinner - simplified
  local frames_str=$(get_spinner_frames)
  local all_frames=()

  # Split frames by space
  for frame in $frames_str; do
    all_frames+=("$frame")
  done

  # If no frames, use basic spinner
  if [[ ${#all_frames[@]} -eq 0 ]]; then
    all_frames=("[>]" "[->]" "[-->]" "[--->]")
  fi

  local frame_count=${#all_frames[@]}

  # Immediate feedback
  echo "$_spinner_message - Animation starting..."

  # Use direct animation with simple background process
  (
    # When the script exits or is interrupted, make sure we clean up
    trap 'exit 0' TERM INT

    while true; do
      local frame="${all_frames[_spinner_idx % frame_count]}"
      local elapsed=$(($(date +%s) - UI_START_TIME))
      local elapsed_str=$(format_time $elapsed)

      # Very simple animation line - maximum compatibility
      local line="${frame} ${_spinner_message} (${elapsed_str})"

      # Force a carriage return, erase the line, and print new frame
      direct_echo "\r${ERASE_LINE}${line}"

      # Force display
      force_terminal_update

      # Update the frame index
      _spinner_idx=$((_spinner_idx + 1))

      # Force longer delay for visibility
      sleep $SPINNER_DELAY || break
    done
  ) &
  _spinner_pid=$!

  # Trap to ensure cleanup
  trap 'stop_ui' EXIT INT TERM
}

# Display a progress bar with percentage - completely rewritten for extreme visibility
# Usage: show_progress_bar [current] [total] [message]
show_progress_bar() {
  UI_ACTIVE=true
  UI_COMPONENT="progress"
  local current="${1:-0}"
  _progress_total="${2:-100}"
  _progress_message="${3:-Progress:}"
  UI_START_TIME=$(date +%s)

  # Force unbuffered output for better animation
  force_unbuffered_output

  # No animation in non-interactive mode
  if ! $ANIMATION_ENABLED; then
    echo ">> $_progress_message (starting at $current/$_progress_total)"
    return
  fi

  # Initial update
  _progress_percent=$current

  # Hide cursor (only in TTY)
  direct_echo "$CURSOR_HIDE"

  # Ensure we're not already running a progress bar
  if [[ -n "$_spinner_pid" ]]; then
    kill $_spinner_pid &>/dev/null || true
    wait $_spinner_pid &>/dev/null || true
    _spinner_pid=""
  fi

  # Reset state
  _last_line=""

  # Immediate feedback
  echo "$_progress_message - Progress bar starting..."

  # Simplified background process
  (
    # When the script exits or is interrupted, make sure we clean up
    trap 'exit 0' TERM INT

    while true; do
      local elapsed=$(($(date +%s) - UI_START_TIME))
      local elapsed_str=$(format_time $elapsed)

      # Ensure we don't divide by zero
      if [[ $_progress_total -eq 0 ]]; then
        _progress_total=1
      fi

      # Calculate percentage
      local percent=$((_progress_percent * 100 / _progress_total))

      # Ensure percent is within range
      if [[ $percent -lt 0 ]]; then percent=0; fi
      if [[ $percent -gt 100 ]]; then percent=100; fi

      # Calculate ETA
      local eta_str="--:--"
      if [[ $_progress_percent -gt 0 && $_progress_percent -lt $_progress_total ]]; then
        local eta=$(( (elapsed * _progress_total / _progress_percent) - elapsed ))
        eta_str=$(format_time $eta)
      fi

      # SUPER SIMPLE progress bar for maximum visibility
      local progress_count=$((percent * 20 / 100))
      local progress_bar="["
      local i

      # Create progress bar using repeated characters
      for ((i=0; i<progress_count; i++)); do
        progress_bar+="#"
      done

      # Fill rest with spaces
      for ((i=progress_count; i<20; i++)); do
        progress_bar+="-"
      done

      progress_bar+="]"

      # Create final line
      local line="${_progress_message} ${progress_bar} ${percent}% (${elapsed_str} / ETA ${eta_str})"

      # Update display with maximum compatibility approach
      direct_echo "\r${ERASE_LINE}${line}"

      # Force display
      force_terminal_update

      # Sleep with longer delay for visibility
      sleep $SPINNER_DELAY || break
    done
  ) &
  _spinner_pid=$!

  # Trap to ensure cleanup
  trap 'stop_ui' EXIT INT TERM
}

# Update progress bar value
# Usage: update_progress_bar [current]
update_progress_bar() {
  local current="${1:-0}"

  # Validate input
  if [[ "$current" =~ ^[0-9]+$ ]]; then
    _progress_percent=$current

    # Cap at total
    if [[ $_progress_percent -gt $_progress_total ]]; then
      _progress_percent=$_progress_total
    fi
  fi

  # If progress complete, stop the UI
  if [[ $_progress_percent -ge $_progress_total ]]; then
    stop_ui
    show_success "Completed: ${_progress_message}"
  fi
}

# Increment progress bar by given amount
# Usage: increment_progress [amount]
increment_progress() {
  local amount="${1:-1}"

  # Validate input
  if [[ "$amount" =~ ^[0-9]+$ ]]; then
    update_progress_bar $((_progress_percent + amount))
  fi
}

# Show a success message
# Usage: show_success "Operation completed successfully"
show_success() {
  local message="${1:-Success!}"
  stop_ui
  echo -e "${COLOR_GREEN}✓${COLOR_RESET} ${message}"
}

# Show an error message
# Usage: show_error "Operation failed"
show_error() {
  local message="${1:-Failed!}"
  stop_ui
  echo -e "${COLOR_RED}✗${COLOR_RESET} ${message}"
}

# Show a warning message
# Usage: show_warning "Proceed with caution"
show_warning() {
  local message="${1:-Warning!}"
  stop_ui
  echo -e "${COLOR_YELLOW}!${COLOR_RESET} ${message}"
}

# Show an info message
# Usage: show_info "Operation in progress"
show_info() {
  local message="${1:-Info:}"
  stop_ui
  echo -e "${COLOR_BLUE}i${COLOR_RESET} ${message}"
}

# Stop any active UI component
stop_ui() {
  if [[ $UI_ACTIVE == true ]]; then
    # Kill the background spinner/progress process
    if [[ -n "$_spinner_pid" ]]; then
      kill $_spinner_pid &>/dev/null || true
      wait $_spinner_pid &>/dev/null || true
    fi

    # Clear line and show cursor
    direct_echo "\r${ERASE_LINE}${CURSOR_SHOW}"

    UI_ACTIVE=false
    UI_COMPONENT=""
    _spinner_pid=""
  fi
}

# Wait for a command to finish while showing a spinner
# Usage: spinner_exec "Loading data..." sleep 5
spinner_exec() {
  local message="$1"
  shift

  show_spinner "$message"

  # Run the command and capture its output in real-time
  "$@" > >(while IFS= read -r line; do
    # Stop the spinner temporarily
    if [[ -n "$_spinner_pid" ]]; then
      kill -STOP $_spinner_pid 2>/dev/null || true
    fi
    # Display the output
    echo "$line"
    # Resume the spinner
    if [[ -n "$_spinner_pid" ]]; then
      kill -CONT $_spinner_pid 2>/dev/null || true
    fi
  done) 2>&1

  local exit_code=$?
  stop_ui
  return $exit_code
}

# Run a command with progress updates based on its output
# Usage: progress_exec "command with progress output" [total_items]
# The command must output numbers or percentages that can be parsed
progress_exec() {
  local cmd="$1"
  local total="${2:-100}"

  show_progress_bar 0 "$total" "Running..."

  # Run command and capture progress updates
  eval "$cmd" | while read -r line; do
    if [[ "$line" =~ ^[0-9]+$ ]]; then
      update_progress_bar "$line"
    elif [[ "$line" =~ ([0-9]+)%$ ]]; then
      local percent="${BASH_REMATCH[1]}"
      update_progress_bar $((percent * total / 100))
    fi
    # Echo the line for visibility
    echo "$line"
  done

  local exit_code=${PIPESTATUS[0]}
  stop_ui
  return $exit_code
}

# Check if running in terminal or pipe
is_terminal() {
  [[ -t 1 ]]
}

# Clean up on exit
cleanup() {
  stop_ui
}

# Set default theme
apply_theme "default"

# Trap cleanup
trap cleanup EXIT

# Initialization message
if is_terminal; then
  echo -e "${COLOR_DIM}Terminal UI utilities loaded. Use 'show_spinner', 'show_progress_bar', etc.${COLOR_RESET}"
fi
