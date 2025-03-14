#!/bin/bash

# terminal_ui_demo.sh - Demonstration of Terminal UI Components
# This script shows all available UI components and their usage

# Source the terminal UI utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$SCRIPT_DIR/terminal_ui.sh" ]]; then
  echo "ERROR: terminal_ui.sh not found in $SCRIPT_DIR"
  exit 1
fi

source "$SCRIPT_DIR/terminal_ui.sh"

# Make demo script executable by default
chmod +x "$0" 2>/dev/null || true

# Function to show section header
section() {
  clear
  echo -e "\n${COLOR_BOLD}${COLOR_CYAN}=== $1 ===${COLOR_RESET}\n"
  sleep 1
}

# Welcome message
section "Terminal UI Components Demo"
echo "This demonstration will show all available UI components."
echo "Press Ctrl+C at any time to exit."
sleep 2

# Show all spinner styles
section "Spinner Styles"
echo "Showing various spinner styles (3 seconds each):"

# Array of all spinner styles
spinner_styles=(
  "dots" "dots2" "dots3" "dots4" "dots5"
  "dots6" "dots7" "dots8" "dots9" "dots10"
  "line" "arrow" "bouncing" "clock" "moon"
  "hearts" "earth"
)

# Show each spinner style
for style in "${spinner_styles[@]}"; do
  # Set the current style
  SPINNER_STYLE="$style"

  # Show spinner with style name
  show_spinner "Demonstrating '$style' spinner style"
  sleep 3
  stop_ui

  # Print newline for separation
  echo ""
done

# Reset to default style
SPINNER_STYLE="dots3"

# Demonstrate all themes
section "Color Themes"
echo "Showing various themes (3 seconds each):"

# List all available themes
themes=("default" "cool" "warm" "minimal" "dramatic")

for theme in "${themes[@]}"; do
  # Apply the theme
  apply_theme "$theme"

  # Show theme with a spinner
  show_spinner "Demonstrating '$theme' theme"
  sleep 3
  stop_ui

  # Print newline for separation
  echo ""
done

# Reset theme
apply_theme "cool"

# Demonstrate Progress Bar
section "Progress Bar"
echo "Demonstrating progress bar:"

# Show a progress bar that fills over time
show_progress_bar 0 100 "Loading data"

# Fill the progress bar gradually
for ((i=0; i<=100; i+=5)); do
  sleep 0.2
  update_progress_bar $i
done

echo ""

# Demonstrate status messages
section "Status Messages"
echo "Demonstrating status messages:"
sleep 1

show_success "Operation completed successfully"
sleep 0.5

show_error "An error occurred"
sleep 0.5

show_warning "Proceed with caution"
sleep 0.5

show_info "System is up to date"
sleep 0.5

echo ""

# Demonstrate spinner_exec
section "Spinner with Command Execution"
echo "Demonstrating spinner_exec (running a command with spinner):"
sleep 1

spinner_exec "Finding large files in current directory" find . -type f -size +1M -exec ls -lh {} \; 2>/dev/null | head -5

echo ""

# Demonstrate progress_exec (simulated)
section "Progress with Command Execution"
echo "Demonstrating progress_exec (simulated command with progress):"
sleep 1

# Simulate a command that outputs progress info
(
  for i in $(seq 0 10 100); do
    echo $i
    sleep 0.3
  done
) | while read -r line; do
  update_progress_bar "$line"
  sleep 0.2
done

echo ""

# Final message
section "Demo Complete"
echo "All Terminal UI components have been demonstrated."
echo "You can use these components in your scripts by sourcing terminal_ui.sh"
echo
echo "For example:"
echo "  source ${SCRIPT_DIR}/terminal_ui.sh"
echo "  show_spinner \"Processing data\""
echo "  # your code here"
echo "  stop_ui"
echo
echo "See the README.md file for more details and examples."
echo

exit 0
