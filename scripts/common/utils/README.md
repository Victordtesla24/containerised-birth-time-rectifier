# Shell Script Terminal UI Library

This directory contains a reusable terminal UI library for shell scripts that provides dynamic, animated progress indicators and visual feedback.

## Overview

The terminal UI library enables shell scripts to display:
- Animated spinners with multiple styles
- Progress bars with percentage and ETA
- Color-coded status messages
- Dynamic themes

All components are designed to be backward compatible with older shell versions and degrade gracefully when advanced features aren't available.

## Components

- **terminal_ui.sh** - The core UI library
- **terminal_ui_demo.sh** - Demonstration script showing all components in action

## Features

### Animated Spinners
- 17 different spinner styles (Unicode and ASCII)
- Dynamic elapsed time display
- Automatic compatibility with older shells

### Progress Bars
- Percentage indication
- Customizable appearance
- ETA calculation

### Status Messages
- Success (✓) - green
- Error (✗) - red
- Warning (!) - yellow
- Info (i) - blue

### Color Themes
- default - cyan/blue/green
- cool - blue/cyan/purple
- warm - red/yellow/green
- minimal - white
- dramatic - red/yellow

## Usage

### Basic Usage

```bash
#!/bin/bash

# Source the terminal UI library
source /path/to/scripts/common/utils/terminal_ui.sh

# Show a spinner during a long operation
show_spinner "Downloading updates"
sleep 5 # Your long operation here
stop_ui

# Display a progress bar
show_progress_bar 0 100 "Installing packages"
for i in {1..100}; do
  # Your code here
  update_progress_bar $i
  sleep 0.1
done

# Show status messages
show_success "Operation completed successfully"
show_error "An error occurred"
show_warning "Proceed with caution"
show_info "System is up to date"
```

### Advanced Usage

```bash
# Execute a command with a spinner
spinner_exec "Finding large files" find / -type f -size +1G

# Apply a different theme
apply_theme "cool" # or "warm", "minimal", "dramatic"

# Set spinner style
SPINNER_STYLE="earth" # See terminal_ui_demo.sh for all styles

# Customize progress bar appearance
PROGRESS_BAR_WIDTH=50
PROGRESS_BAR_CHAR="█"
PROGRESS_BAR_BG_CHAR="░"
```

## Shell Compatibility

The library automatically detects shell capabilities and adjusts functionality:
- Full features in Bash 4+ (associative arrays, etc.)
- Basic compatibility mode in older shells
- Graceful degradation of advanced features

## See It In Action

Run the demo script to see all components and features:

```bash
./terminal_ui_demo.sh
```

## Integration with cleanup.sh

The `test_scripts/cleanup.sh` script integrates this UI library to provide:
- Animated spinners during long-running operations
- Progress bars for project directory cleanup
- Visual performance comparisons for before/after metrics
- Color-coded status messages throughout the script
