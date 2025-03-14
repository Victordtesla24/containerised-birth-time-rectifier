#!/bin/bash
#
# SYSTEM AND PROJECT CLEANUP SCRIPT
# High-performance, reliable version for macOS
# NO ANIMATIONS - DIRECT FEEDBACK APPROACH
#

# Version
VERSION="3.0.0"

# Basic constants for formatting output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
MAGENTA="\033[0;35m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

# Log timestamp format
TIMESTAMP_FORMAT="%Y-%m-%d %H:%M:%S"

# File to store performance data
PERF_DATA="/tmp/cleanup_perf_$$.data"

# Flag to track if we're in a subprocess to handle signal trapping properly
IS_SUBPROCESS=false

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

# Print timestamped message
log() {
    local level="$1"
    local message="$2"
    local color=""

    case "$level" in
        "INFO")     color="$BLUE" ;;
        "SUCCESS")  color="$GREEN" ;;
        "WARNING")  color="$YELLOW" ;;
        "ERROR")    color="$RED" ;;
        "STEP")     color="$CYAN" ;;
        *)          color="$RESET" ;;
    esac

    # Print with timestamp and color
    local timestamp=$(date +"$TIMESTAMP_FORMAT")
    echo -e "${color}[${timestamp}] ${level}: ${message}${RESET}"
}

# Print section header
print_header() {
    local title="$1"
    echo ""
    echo -e "${BOLD}${MAGENTA}====== $title ======${RESET}"
    echo ""
}

# Print indented result
print_result() {
    echo -e "       ${CYAN}→ $1${RESET}"
}

# Handle termination signals
cleanup_and_exit() {
    if [ "$IS_SUBPROCESS" = false ]; then
        log "INFO" "Cleaning up temporary files..."
        rm -f "$PERF_DATA" 2>/dev/null

        # Print final message
        log "INFO" "Script terminated."
    fi

    # If parameter is passed, use it as exit code
    exit ${1:-0}
}

# Execute command with timeout and show output
exec_with_timeout() {
    local cmd="$1"
    local timeout="$2"
    local desc="$3"

    log "STEP" "Executing: $desc"

    # Use timeout command if it exists, otherwise fall back to regular execution
    if command -v timeout >/dev/null 2>&1; then
        if ! timeout "$timeout" bash -c "$cmd" 2>&1; then
            log "WARNING" "Command timed out after ${timeout}s: $desc"
            return 1
        fi
    else
        if ! eval "$cmd" 2>&1; then
            log "WARNING" "Command failed: $desc"
            return 1
        fi
    fi

    return 0
}

# Calculate and format size
format_size() {
    local size="$1"

    if [ "$size" -gt 1073741824 ]; then
        echo "$(echo "scale=2; $size / 1073741824" | bc) GB"
    elif [ "$size" -gt 1048576 ]; then
        echo "$(echo "scale=2; $size / 1048576" | bc) MB"
    elif [ "$size" -gt 1024 ]; then
        echo "$(echo "scale=1; $size / 1024" | bc) KB"
    else
        echo "${size} bytes"
    fi
}

# Get CPU load average
get_load_avg() {
    if [ "$(uname)" = "Darwin" ]; then
        sysctl -n vm.loadavg | awk '{print $2, $3, $4}'
    else
        uptime | awk '{print $(NF-2), $(NF-1), $NF}' | sed 's/,//g'
    fi
}

# Get free memory in MB
get_free_mem() {
    if [ "$(uname)" = "Darwin" ]; then
        local vm_stat_output=$(vm_stat)
        local pages_free=$(echo "$vm_stat_output" | grep "Pages free:" | awk '{print $3}' | tr -d '.')
        local pages_speculative=$(echo "$vm_stat_output" | grep "Pages speculative:" | awk '{print $3}' | tr -d '.')
        local total_free=$(( (pages_free + pages_speculative) * 4096 / 1024 / 1024 ))
        echo "$total_free"
    else
        free -m | grep "Mem:" | awk '{print $7}'
    fi
}

# Get disk write speed (MB/s)
test_disk_speed() {
    local test_file="/tmp/cleanup_test_$$"
    local test_size=100 # MB

    if [ "$(uname)" = "Darwin" ]; then
        # Create test file and measure time
        local start_time=$(date +%s.%N)
        if ! dd if=/dev/zero of="$test_file" bs=1m count="$test_size" 2>/dev/null; then
            echo "0" # Return 0 on error
            return
        fi
        local end_time=$(date +%s.%N)
        rm -f "$test_file"

        # Calculate speed with safeguard against division by zero
        local duration=$(echo "$end_time - $start_time" | bc)

        # Check if duration is zero or too small
        if (( $(echo "$duration <= 0.001" | bc -l) )); then
            echo "0" # Return 0 for unreliable measurements
        else
            local speed=$(echo "scale=2; $test_size / $duration" | bc)
            echo "$speed"
        fi
    else
        # Simpler approach for non-macOS
        echo "0"
    fi
}

# ==============================================================================
# MAIN CLEANING FUNCTIONS
# ==============================================================================

# Source the terminal UI utilities
source_terminal_ui() {
    # Skip if terminal UI is disabled
    if [ "$USE_TERMINAL_UI" = false ]; then
        TERMINAL_UI_AVAILABLE=false
        log "INFO" "Terminal UI disabled by user with --no-ui option"
        return
    fi

    local terminal_ui_path="$PROJECT_DIR/scripts/common/utils/terminal_ui.sh"

    # Debug info about environment variables
    log "INFO" "Checking terminal UI environment..."
    log "INFO" "TERM: $TERM"
    log "INFO" "Project directory: $PROJECT_DIR"
    log "INFO" "Terminal UI path: $terminal_ui_path"

    # Check if terminal supports colors
    if [ -t 1 ] && [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
        log "INFO" "Terminal appears to support colors and interactive features"
    else
        log "WARNING" "Terminal may not support interactive features (TERM=$TERM, is TTY: $([ -t 1 ] && echo "yes" || echo "no"))"
    fi

    # Check if terminal UI utilities exist
    if [ -f "$terminal_ui_path" ]; then
        # Set environment variable to tell terminal_ui.sh to adjust for subshell
        export RUNNING_IN_CLEANUP_SCRIPT=true

        # Force TTY detection to be more permissive
        export FORCE_TTY=true

        # Source the utilities with error handling
        if source "$terminal_ui_path" 2>/dev/null; then
            TERMINAL_UI_AVAILABLE=true
            log "SUCCESS" "Terminal UI utilities loaded successfully"

            # Check if key functions exist
            if type show_spinner >/dev/null 2>&1 && type show_progress_bar >/dev/null 2>&1; then
                log "INFO" "Terminal UI functions are available"
            else
                log "WARNING" "Terminal UI functions not properly defined after sourcing"
                TERMINAL_UI_AVAILABLE=false
            fi

            # Set a default theme if the function exists
            if type apply_theme >/dev/null 2>&1; then
                apply_theme "cool"
                log "INFO" "Applied 'cool' theme to terminal UI"
            else
                log "WARNING" "apply_theme function not found in terminal UI utilities"
            fi
        else
            TERMINAL_UI_AVAILABLE=false
            log "ERROR" "Failed to source terminal UI utilities"
        fi
    else
        TERMINAL_UI_AVAILABLE=false
        log "INFO" "Terminal UI utilities not found at $terminal_ui_path, using standard output"
    fi
}

# Wrapper for running a command with spinner
run_with_spinner() {
    local message="$1"
    local func="$2"
    shift 2

    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        # Start the spinner
        show_spinner "$message"

        # Run the function
        "$func" "$@"
        local result=$?

        # Stop the spinner - use stop_ui instead of stop_spinner
        stop_ui

        return $result
    else
        # Run without spinner
        "$func" "$@"
        return $?
    fi
}

# Wrapper for running a command with progress bar
run_with_progress() {
    local total="$1"
    local message="$2"
    local func="$3"
    shift 3

    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        # Start the progress bar
        show_progress_bar 0 "$total" "$message"

        # Run the function with progress updates
        PROGRESS_TOTAL="$total"
        PROGRESS_CURRENT=0
        PROGRESS_FUNC="$func"
        PROGRESS_ARGS="$@"

        # Run the function
        "$func" "$@"
        local result=$?

        # Complete the progress bar
        update_progress_bar "$total"
        # Use stop_ui instead of stop_progress_bar
        stop_ui

        return $result
    else
        # Run without progress bar
        "$func" "$@"
        return $?
    fi
}

# Update progress
update_progress() {
    local increment="${1:-1}"

    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        PROGRESS_CURRENT=$((PROGRESS_CURRENT + increment))
        update_progress_bar "$PROGRESS_CURRENT"
    fi
}

# Safe file cleanup function with size calculation
clean_files() {
    local dir="$1"
    local pattern="$2"
    local description="$3"
    local exclusion="${4:-}"

    if [ ! -d "$dir" ]; then
        log "INFO" "Directory not found: $dir"
        return 0
    fi

    log "STEP" "Cleaning $description in $dir"

    # Build find command
    local find_cmd="find \"$dir\" -type f -name \"$pattern\""
    if [ -n "$exclusion" ]; then
        find_cmd="$find_cmd ! -path \"$exclusion\""
    fi

    # Add size calculation
    if [ "$DRY_RUN" = true ]; then
        # Calculate total size and count in dry run mode
        local temp_size_file="/tmp/cleanup_size_$$"
        eval "$find_cmd -ls 2>/dev/null" | awk '{total_size += $7; count++} END {print total_size, count}' > "$temp_size_file"
        local total_size=$(cut -d' ' -f1 "$temp_size_file")
        local count=$(cut -d' ' -f2 "$temp_size_file")
        rm -f "$temp_size_file"

        if [ -z "$total_size" ]; then total_size=0; fi
        if [ -z "$count" ]; then count=0; fi

        # Show what would be cleaned
        local formatted_size=$(format_size "$total_size")
        print_result "Would remove $count files ($formatted_size)"

        # List some examples if verbose
        if [ "$VERBOSE" = true ] && [ "$count" -gt 0 ]; then
            log "INFO" "Examples of files that would be removed:"
            eval "$find_cmd -print 2>/dev/null | head -5" | sed 's/^/       - /'
            if [ "$count" -gt 5 ]; then
                echo "       - ... and $(($count - 5)) more"
            fi
        fi
    else
        # Calculate total size before deletion
        local temp_size_file="/tmp/cleanup_size_$$"
        eval "$find_cmd -ls 2>/dev/null" | awk '{total_size += $7; count++} END {print total_size, count}' > "$temp_size_file"
        local total_size=$(cut -d' ' -f1 "$temp_size_file")
        local count=$(cut -d' ' -f2 "$temp_size_file")
        rm -f "$temp_size_file"

        if [ -z "$total_size" ]; then total_size=0; fi
        if [ -z "$count" ]; then count=0; fi

        # Perform the actual deletion
        if [ "$count" -gt 0 ]; then
            if [ "$VERBOSE" = true ]; then
                eval "$find_cmd -print -delete 2>/dev/null" | wc -l | xargs -I{} print_result "Removed {} files"
            else
                eval "$find_cmd -delete 2>/dev/null"
                print_result "Removed $count files ($(format_size "$total_size"))"
            fi
        else
            print_result "No matching files found"
        fi
    fi
}

# Safe directory cleanup function with size calculation
clean_directories() {
    local dir="$1"
    local pattern="$2"
    local description="$3"
    local exclusion="${4:-}"

    if [ ! -d "$dir" ]; then
        log "INFO" "Directory not found: $dir"
        return 0
    fi

    log "STEP" "Cleaning $description in $dir"

    # Build find command
    local find_cmd="find \"$dir\" -type d -name \"$pattern\""
    if [ -n "$exclusion" ]; then
        find_cmd="$find_cmd ! -path \"$exclusion\""
    fi

    # Add depth parameter to process deepest directories first
    find_cmd="$find_cmd -depth"

    if [ "$DRY_RUN" = true ]; then
        # Calculate total size and count
        local temp_size_file="/tmp/cleanup_dirsize_$$"
        eval "$find_cmd -exec du -sk {} \; 2>/dev/null" | awk '{total_size += $1 * 1024; count++} END {print total_size, count}' > "$temp_size_file"
        local total_size=$(cut -d' ' -f1 "$temp_size_file")
        local count=$(cut -d' ' -f2 "$temp_size_file")
        rm -f "$temp_size_file"

        if [ -z "$total_size" ]; then total_size=0; fi
        if [ -z "$count" ]; then count=0; fi

        # Show what would be cleaned
        local formatted_size=$(format_size "$total_size")
        print_result "Would remove $count directories ($formatted_size)"

        # List some examples if verbose
        if [ "$VERBOSE" = true ] && [ "$count" -gt 0 ]; then
            log "INFO" "Examples of directories that would be removed:"
            eval "$find_cmd -print 2>/dev/null | head -5" | sed 's/^/       - /'
            if [ "$count" -gt 5 ]; then
                echo "       - ... and $(($count - 5)) more"
            fi
        fi
    else
        # Get list of directories before deletion for size calculation
        local temp_dir_list="/tmp/cleanup_dirlist_$$"
        eval "$find_cmd -print 2>/dev/null" > "$temp_dir_list"
        local count=$(wc -l < "$temp_dir_list")

        # Calculate total size if directories exist
        local total_size=0
        if [ "$count" -gt 0 ]; then
            local temp_size_file="/tmp/cleanup_dirsize_$$"
            cat "$temp_dir_list" | xargs -I{} du -sk {} 2>/dev/null | awk '{total_size += $1 * 1024} END {print total_size}' > "$temp_size_file"
            total_size=$(cat "$temp_size_file")
            rm -f "$temp_size_file"

            if [ -z "$total_size" ]; then total_size=0; fi

            # Delete the directories
            if [ "$VERBOSE" = true ]; then
                cat "$temp_dir_list" | while read dir_to_remove; do
                    log "INFO" "Removing directory: $dir_to_remove"
                    rm -rf "$dir_to_remove" 2>/dev/null
                done
            else
                cat "$temp_dir_list" | xargs -I{} rm -rf {} 2>/dev/null
            fi

            print_result "Removed $count directories ($(format_size "$total_size"))"
        else
            print_result "No matching directories found"
        fi

        rm -f "$temp_dir_list"
    fi
}

# Clean system caches safely
clean_system_caches() {
    print_header "CLEANING SYSTEM CACHES"

    # List of system caches that should not be touched
    local protected_caches=(
        "/Library/Caches/com.apple.coresymbolicationd"
        "/Library/Caches/com.apple.iconservices"
        "/Library/Caches/com.apple.kext.caches"
        "/Library/Caches/com.apple.bootstamps"
        "/Library/Caches/com.apple.kernelcaches"
        "/Library/Caches/com.apple.apsd"
        "/Library/Caches/com.apple.WindowServer"
        "/Library/Caches/com.apple.display"
        "/Library/Caches/com.apple.telemetry"
        "/Library/Caches/com.apple.systemstats"
    )

    # List of user caches that should not be touched
    local protected_user_caches=(
        "$ORIGINAL_HOME/Library/Caches/com.apple.Safari"
        "$ORIGINAL_HOME/Library/Caches/com.apple.Music"
        "$ORIGINAL_HOME/Library/Caches/CloudKit"
        "$ORIGINAL_HOME/Library/Caches/com.apple.icloud"
        "$ORIGINAL_HOME/Library/Caches/com.apple.finder"
        "$ORIGINAL_HOME/Library/Caches/com.apple.appstore"
    )

    # Clean system caches
    if [ -d "/Library/Caches" ]; then
        log "STEP" "Cleaning system caches (with protection for critical files)"

        # Skip in dry run mode
        if [ "$DRY_RUN" = true ]; then
            log "INFO" "DRY RUN: Would clean non-critical system cache files"
            local count=$(find "/Library/Caches" -type f -size -10M -not -path "*/com.apple*" 2>/dev/null | wc -l)
            print_result "Would clean approximately $count non-critical system cache files"
        else
            # Build exclusion pattern
            local exclusion=""
            for path in "${protected_caches[@]}"; do
                exclusion="${exclusion} -not -path \"${path}*\""
            done

            # Use timeout to prevent hanging
            local cmd="find /Library/Caches -type f -size -10M ${exclusion} -user \"$ORIGINAL_USER\" -delete 2>/dev/null"
            if ! exec_with_timeout "$cmd" 60 "Cleaning system caches"; then
                log "WARNING" "System cache cleanup timed out or encountered errors"
            else
                print_result "Safely cleaned user-owned system cache files"
            fi

            # Clean empty directories
            log "INFO" "Cleaning empty cache directories"
            find "/Library/Caches" -type d -empty -user "$ORIGINAL_USER" -delete 2>/dev/null
        fi
    fi

    # Clean user caches
    if [ -d "$ORIGINAL_HOME/Library/Caches" ]; then
        log "STEP" "Cleaning user caches (with protection for app data)"

        if [ "$DRY_RUN" = true ]; then
            log "INFO" "DRY RUN: Would clean user cache files"
            local count=$(find "$ORIGINAL_HOME/Library/Caches" -type f 2>/dev/null | wc -l)
            print_result "Would clean approximately $count user cache files"
        else
            # Build exclusion pattern
            local exclusion=""
            for path in "${protected_user_caches[@]}"; do
                exclusion="${exclusion} -not -path \"${path}*\""
            done

            # Use timeout to prevent hanging
            local cmd="find \"$ORIGINAL_HOME/Library/Caches\" -type f ${exclusion} -user \"$ORIGINAL_USER\" -delete 2>/dev/null"
            if ! exec_with_timeout "$cmd" 60 "Cleaning user caches"; then
                log "WARNING" "User cache cleanup timed out or encountered errors"
            else
                print_result "Safely cleaned user cache files"
            fi

            # Clean empty directories
            log "INFO" "Cleaning empty cache directories"
            find "$ORIGINAL_HOME/Library/Caches" -type d -empty -delete 2>/dev/null
        fi
    fi

    log "SUCCESS" "Cache cleanup completed"
}

# Clean project directory
clean_project_directory() {
    print_header "CLEANING PROJECT DIRECTORY"
    PROJECT_DIR="$(pwd)"

    log "INFO" "Current project directory: $PROJECT_DIR"
    log "INFO" "Identifying project files to clean..."

    # Load terminal UI utilities if available
    source_terminal_ui

    # Use a progress bar for the entire cleaning process if UI is available
    local total_steps=9  # Adjusted based on the total number of major cleaning steps

    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        show_progress_bar 0 $total_steps "Project Cleanup"
    fi

    # Step 1: Clean Python related files
    run_with_spinner "Cleaning Python cache files" clean_files "$PROJECT_DIR" "*.pyc" "Python compiled files"
    run_with_spinner "Cleaning Python optimized files" clean_files "$PROJECT_DIR" "*.pyo" "Python optimized files"
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 1
    fi

    # Step 2: Clean JavaScript/TypeScript build artifacts with spinner
    run_with_spinner "Cleaning Next.js build directory" clean_directories "$PROJECT_DIR" ".next" "Next.js build directory"
    run_with_spinner "Cleaning distribution directories" clean_directories "$PROJECT_DIR" "dist" "Distribution directories"
    run_with_spinner "Cleaning build directories" clean_directories "$PROJECT_DIR" "build" "Build directories" "*node_modules*"
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 2
    fi

    # Step 3: Clean TypeScript build info files with spinner
    run_with_spinner "Cleaning TypeScript build info files" clean_files "$PROJECT_DIR" "tsconfig*.tsbuildinfo" "TypeScript build info files"
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 3
    fi

    # Step 4: Clean cache directories forcefully
    run_with_spinner "Cleaning cache directories" clean_cache_directories
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 4
    fi

    # Step 5: Clean test artifacts
    run_with_spinner "Cleaning test artifacts" clean_files "$PROJECT_DIR" ".coverage" "Coverage files"
    run_with_spinner "Cleaning coverage directories" clean_directories "$PROJECT_DIR" "coverage" "Coverage directories"
    run_with_spinner "Cleaning NYC output" clean_directories "$PROJECT_DIR" ".nyc_output" "NYC output directories"
    run_with_spinner "Cleaning Playwright reports" clean_directories "$PROJECT_DIR" "playwright-report" "Playwright reports"
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 5
    fi

    # Step 6: Clean log files
    run_with_spinner "Cleaning log files" clean_files "$PROJECT_DIR" "*.log" "Log files"
    run_with_spinner "Cleaning NPM debug logs" clean_files "$PROJECT_DIR" "npm-debug.log*" "NPM debug logs"
    run_with_spinner "Cleaning Yarn error logs" clean_files "$PROJECT_DIR" "yarn-error.log" "Yarn error logs"
    run_with_spinner "Cleaning old logs" clean_logs_directory
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 6
    fi

    # Step 7: Clean editor backup files and OS files
    run_with_spinner "Cleaning backup and temporary files" clean_root_temp_files
    run_with_spinner "Cleaning OS metadata files" clean_files "$PROJECT_DIR" ".DS_Store" "macOS directory metadata files"
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 7
    fi

    # Step 8: Organize files from root directory
    run_with_spinner "Organizing files from root directory" organize_root_files
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 8
    fi

    # Step 9: Run JavaScript cleanup scripts if available
    if [ "$RUN_JS_CLEANUP" = true ]; then
        run_with_spinner "Running JavaScript cleanup scripts" run_js_cleanup_scripts
    fi
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        update_progress_bar 9
    fi

    # Stop progress bar if used
    if [ "$TERMINAL_UI_AVAILABLE" = true ] && [ "$DRY_RUN" = false ]; then
        stop_progress_bar
    fi

    log "SUCCESS" "Project directory cleanup completed"
}

# Run system maintenance
run_system_maintenance() {
    print_header "RUNNING SYSTEM MAINTENANCE"

    # Run periodic maintenance scripts
    if command -v periodic >/dev/null 2>&1; then
        log "STEP" "Running system periodic tasks"

        for interval in daily weekly monthly; do
            if [ -d "/etc/periodic/$interval" ] || [ -x "/etc/periodic/$interval" ]; then
                log "INFO" "Running periodic $interval tasks..."

                if [ "$DRY_RUN" = true ]; then
                    log "INFO" "DRY RUN: Would run periodic $interval tasks"
                else
                    if ! exec_with_timeout "periodic $interval >/dev/null 2>&1" 120 "periodic $interval"; then
                        log "WARNING" "Periodic $interval tasks timed out or encountered errors"
                    else
                        log "SUCCESS" "Periodic $interval tasks completed"
                    fi
                fi
            fi
        done
    else
        log "INFO" "Periodic maintenance not available on this system"
    fi

    # Optimize memory
    if command -v purge >/dev/null 2>&1; then
        log "STEP" "Freeing inactive memory"

        if [ "$DRY_RUN" = true ]; then
            log "INFO" "DRY RUN: Would free inactive memory with purge"
        else
            if ! exec_with_timeout "purge" 30 "Memory purge"; then
                log "WARNING" "Memory purge timed out or encountered errors"
            else
                log "SUCCESS" "Memory optimization completed"
            fi
        fi
    fi

    # Flush filesystem buffers
    if [ "$DRY_RUN" = false ]; then
        log "STEP" "Flushing filesystem buffers to ensure write consistency"
        sync
        log "INFO" "Filesystem buffers flushed"
    fi

    # macOS specific maintenance
    if [ "$(uname)" = "Darwin" ] && [ "$DRY_RUN" = false ]; then
        log "STEP" "Running additional macOS maintenance"

        # Clear quicklook cache
        if [ -d "/private/var/folders" ]; then
            log "INFO" "Clearing QuickLook cache"
            qlmanage -r cache >/dev/null 2>&1 || true
        fi

        # Update locate database
        if command -v /usr/libexec/locate.updatedb >/dev/null 2>&1; then
            log "INFO" "Updating locate database (if permissions allow)"
            /usr/libexec/locate.updatedb >/dev/null 2>&1 || true
        fi

        log "SUCCESS" "Additional maintenance completed"
    fi
}

# Collect and print system metrics
collect_metrics() {
    local when="$1"

    print_header "COLLECTING SYSTEM METRICS ($when)"

    # Get CPU load
    local cpu_load=$(get_load_avg)
    log "INFO" "CPU Load Averages: $cpu_load"
    echo "CPU_LOAD_$when=\"$cpu_load\"" >> "$PERF_DATA"

    # Get free memory
    local free_mem=$(get_free_mem)
    log "INFO" "Free RAM: ${free_mem} MB"
    echo "FREE_MEM_$when=$free_mem" >> "$PERF_DATA"

    # Get app launch time
    local app_launch=$( (time -p perl -e "exit") 2>&1 | awk '/real/ {print $2}' )
    log "INFO" "Test App Launch Time: ${app_launch}s"
    echo "APP_LAUNCH_$when=$app_launch" >> "$PERF_DATA"

    # Get disk write speed
    local disk_speed=$(test_disk_speed)
    log "INFO" "Disk Write Speed: ${disk_speed} MB/s"
    echo "DISK_SPEED_$when=$disk_speed" >> "$PERF_DATA"
}

# Compare performance metrics
compare_metrics() {
    print_header "PERFORMANCE COMPARISON"

    # Source the performance data file
    if [ -f "$PERF_DATA" ]; then
        # Process the performance data file to handle N/A values before sourcing
        local temp_perf_data="/tmp/cleanup_perf_processed_$$"
        cat "$PERF_DATA" | sed 's/DISK_SPEED_.*=N\/A/DISK_SPEED_&=0/' | sed 's/ERROR: Test duration too short, cannot calculate disk speed reliably/0/' > "$temp_perf_data"
        source "$temp_perf_data"
        rm -f "$temp_perf_data"

        # Compare CPU load
        log "INFO" "CPU Load (before -> after): $CPU_LOAD_BEFORE -> $CPU_LOAD_AFTER"

        # Compare free memory
        if [ -n "$FREE_MEM_BEFORE" ] && [ -n "$FREE_MEM_AFTER" ]; then
            local mem_diff=$(echo "$FREE_MEM_AFTER - $FREE_MEM_BEFORE" | bc)
            if [ -n "$mem_diff" ]; then
                if [ "$(echo "$mem_diff >= 0" | bc)" -eq 1 ]; then
                    log "SUCCESS" "Free RAM: ${FREE_MEM_BEFORE} MB -> ${FREE_MEM_AFTER} MB (+${mem_diff} MB)"
                else
                    log "WARNING" "Free RAM: ${FREE_MEM_BEFORE} MB -> ${FREE_MEM_AFTER} MB (${mem_diff} MB)"
                fi
            else
                log "INFO" "Free RAM comparison not available"
            fi
        fi

        # Compare app launch time
        if [ -n "$APP_LAUNCH_BEFORE" ] && [ -n "$APP_LAUNCH_AFTER" ]; then
            local launch_diff=$(echo "$APP_LAUNCH_BEFORE - $APP_LAUNCH_AFTER" | bc)
            if [ -n "$launch_diff" ]; then
                if [ "$(echo "$launch_diff >= 0" | bc)" -eq 1 ]; then
                    log "SUCCESS" "App Launch Time: ${APP_LAUNCH_BEFORE}s -> ${APP_LAUNCH_AFTER}s (${launch_diff}s faster)"
                else
                    local abs_diff=$(echo -n "$launch_diff" | sed 's/^-//')
                    log "WARNING" "App Launch Time: ${APP_LAUNCH_BEFORE}s -> ${APP_LAUNCH_AFTER}s (${abs_diff}s slower)"
                fi
            else
                log "INFO" "App launch time comparison not available"
            fi
        fi

        # Compare disk write speed - check for N/A values
        if [ -n "$DISK_SPEED_BEFORE" ] && [ -n "$DISK_SPEED_AFTER" ]; then
            # Handle N/A values
            if [[ "$DISK_SPEED_BEFORE" == *"N/A"* || "$DISK_SPEED_AFTER" == *"N/A"* ||
                  "$DISK_SPEED_BEFORE" == *"ERROR"* || "$DISK_SPEED_AFTER" == *"ERROR"* ]]; then
                log "INFO" "Disk Speed: Comparison not available (unreliable measurements)"
            else
                # Normal comparison for numeric values
                local speed_diff=$(echo "$DISK_SPEED_AFTER - $DISK_SPEED_BEFORE" | bc)
                if [ -n "$speed_diff" ]; then
                    if [ "$(echo "$speed_diff >= 0" | bc)" -eq 1 ]; then
                        log "SUCCESS" "Disk Write Speed: ${DISK_SPEED_BEFORE} MB/s -> ${DISK_SPEED_AFTER} MB/s (+${speed_diff} MB/s)"
                    else
                        log "WARNING" "Disk Write Speed: ${DISK_SPEED_BEFORE} MB/s -> ${DISK_SPEED_AFTER} MB/s (${speed_diff} MB/s)"
                    fi
                else
                    log "INFO" "Disk speed comparison not available"
                fi
            fi
        else
            log "INFO" "Disk speed data not available for comparison"
        fi
    else
        log "WARNING" "Performance data not available for comparison"
    fi
}

# NEW: Add dead code reporting function
detect_redundant_files() {
    print_header "DETECTING REDUNDANT FILES"

    PROJECT_DIR="$(pwd)"
    REDUNDANT_FILES_REPORT="$PROJECT_DIR/reports/redundant_files_report.txt"

    log "INFO" "Scanning for potentially redundant files..."

    # Create reports directory if it doesn't exist
    if [ "$DRY_RUN" = false ] && [ ! -d "$PROJECT_DIR/reports" ]; then
        mkdir -p "$PROJECT_DIR/reports"
    fi

    if [ "$DRY_RUN" = true ]; then
        log "INFO" "Would generate a report of potential redundant files"
    else
        echo "Potentially Redundant Files Report ($(date))" > "$REDUNDANT_FILES_REPORT"
        echo "----------------------------------------" >> "$REDUNDANT_FILES_REPORT"
        echo "" >> "$REDUNDANT_FILES_REPORT"

        # 1. Multiple configuration files for the same tool
        echo "## Multiple Configuration Files" >> "$REDUNDANT_FILES_REPORT"
        echo "" >> "$REDUNDANT_FILES_REPORT"

        # Check for multiple package.json files
        PKG_FILES=$(find "$PROJECT_DIR" -maxdepth 1 -name "package*.json" | grep -v "package-lock.json" | wc -l)
        if [ "$PKG_FILES" -gt 1 ]; then
            echo "### Multiple package.json files:" >> "$REDUNDANT_FILES_REPORT"
            find "$PROJECT_DIR" -maxdepth 1 -name "package*.json" | grep -v "package-lock.json" | sort | sed 's|^.*/||' >> "$REDUNDANT_FILES_REPORT"
            echo "" >> "$REDUNDANT_FILES_REPORT"
        fi

        # Check for multiple docker-compose files
        DOCKER_FILES=$(find "$PROJECT_DIR" -maxdepth 1 -name "docker-compose*.yml" | wc -l)
        if [ "$DOCKER_FILES" -gt 1 ]; then
            echo "### Multiple docker-compose files:" >> "$REDUNDANT_FILES_REPORT"
            find "$PROJECT_DIR" -maxdepth 1 -name "docker-compose*.yml" | sort | sed 's|^.*/||' >> "$REDUNDANT_FILES_REPORT"
            echo "" >> "$REDUNDANT_FILES_REPORT"
        fi

        # Check for multiple next.config files
        NEXT_FILES=$(find "$PROJECT_DIR" -maxdepth 1 -name "next.config*.js" | wc -l)
        if [ "$NEXT_FILES" -gt 1 ]; then
            echo "### Multiple Next.js config files:" >> "$REDUNDANT_FILES_REPORT"
            find "$PROJECT_DIR" -maxdepth 1 -name "next.config*.js" | sort | sed 's|^.*/||' >> "$REDUNDANT_FILES_REPORT"
            echo "" >> "$REDUNDANT_FILES_REPORT"
        fi

        # 2. Check for test files in the root that should be in tests/ directory
        echo "## Test Files Outside Test Directory" >> "$REDUNDANT_FILES_REPORT"
        echo "" >> "$REDUNDANT_FILES_REPORT"
        find "$PROJECT_DIR" -maxdepth 1 -name "test_*.py" -o -name "*_test.py" -o -name "test_*.js" -o -name "*_test.js" | sort | sed 's|^.*/||' >> "$REDUNDANT_FILES_REPORT"
        echo "" >> "$REDUNDANT_FILES_REPORT"

        # 3. Check for documentation outside docs directory
        echo "## Documentation Outside Docs Directory" >> "$REDUNDANT_FILES_REPORT"
        echo "" >> "$REDUNDANT_FILES_REPORT"
        find "$PROJECT_DIR" -maxdepth 1 -name "*.md" | grep -v "README.md" | sort | sed 's|^.*/||' >> "$REDUNDANT_FILES_REPORT"

        # 4. Check for redundant env files
        echo "## Multiple Environment Files" >> "$REDUNDANT_FILES_REPORT"
        echo "" >> "$REDUNDANT_FILES_REPORT"
        find "$PROJECT_DIR" -maxdepth 1 -name ".env*" | sort | sed 's|^.*/||' >> "$REDUNDANT_FILES_REPORT"

        # Add a note at the end
        echo "" >> "$REDUNDANT_FILES_REPORT"
        echo "NOTE: This is an automated report. Please manually review these files before removing or consolidating them." >> "$REDUNDANT_FILES_REPORT"

        log "SUCCESS" "Redundant files report generated at: $REDUNDANT_FILES_REPORT"
    fi
}

# NEW: Add function to run the project-specific JavaScript cleanup scripts
run_js_cleanup_scripts() {
    print_header "RUNNING JAVASCRIPT CLEANUP SCRIPTS"

    PROJECT_DIR="$(pwd)"

    # Check for the cleanup-temp-files.js script
    TEMP_FILES_SCRIPT="$PROJECT_DIR/scripts/cleanup-temp-files.js"

    if [ -f "$TEMP_FILES_SCRIPT" ]; then
        log "STEP" "Running JavaScript temp files cleanup script"

        if [ "$DRY_RUN" = true ]; then
            log "INFO" "Would run: node $TEMP_FILES_SCRIPT"
        else
            if command -v node >/dev/null 2>&1; then
                if node "$TEMP_FILES_SCRIPT"; then
                    log "SUCCESS" "JavaScript temp files cleanup completed"
                else
                    log "ERROR" "JavaScript temp files cleanup failed"
                fi
            else
                log "WARNING" "Node.js not found, skipping JavaScript cleanup script"
            fi
        fi
    else
        log "INFO" "JavaScript temp files cleanup script not found, skipping"
    fi

    # Check for the consolidate-directories.js script - but don't run automatically
    CONSOLIDATE_SCRIPT="$PROJECT_DIR/scripts/consolidate-directories.js"

    if [ -f "$CONSOLIDATE_SCRIPT" ]; then
        log "INFO" "Directory consolidation script found: $CONSOLIDATE_SCRIPT"
        log "WARNING" "Directory consolidation is potentially destructive and requires manual review"
        log "INFO" "To run directory consolidation: node $CONSOLIDATE_SCRIPT"
    fi
}

# Clean cache directories with forceful removal
clean_cache_directories() {
    log "STEP" "Forcefully cleaning cache directories"

    # Define common cache directories to clean
    local cache_dirs=(
        ".ruff_cache"
        ".mypy_cache"
        ".pytest_cache"
        ".swc"
        "__pycache__"
    )

    if [ "$DRY_RUN" = true ]; then
        local total_size=0
        local total_count=0

        for cache_dir in "${cache_dirs[@]}"; do
            # Calculate size
            local dir_size=$(find "$PROJECT_DIR" -type d -name "$cache_dir" -exec du -sk {} \; 2>/dev/null | awk '{sum += $1} END {print sum}')
            local dir_count=$(find "$PROJECT_DIR" -type d -name "$cache_dir" | wc -l | tr -d ' ')

            if [ -n "$dir_size" ] && [ "$dir_size" -gt 0 ]; then
                log "INFO" "Would clean $dir_count $cache_dir directories ($(($dir_size * 1024)) bytes)"
                total_size=$(($total_size + $dir_size))
                total_count=$(($total_count + $dir_count))
            fi
        done

        log "INFO" "Would clean total of $total_count cache directories ($(($total_size * 1024)) bytes)"
    else
        local total_removed=0

        for cache_dir in "${cache_dirs[@]}"; do
            local dir_count=$(find "$PROJECT_DIR" -type d -name "$cache_dir" | wc -l | tr -d ' ')

            if [ "$dir_count" -gt 0 ]; then
                # Get size before deletion
                local dir_size=$(find "$PROJECT_DIR" -type d -name "$cache_dir" -exec du -sk {} \; 2>/dev/null | awk '{sum += $1} END {print sum}')

                # Delete with force flag
                find "$PROJECT_DIR" -type d -name "$cache_dir" -exec rm -rf {} \; 2>/dev/null || true

                log "SUCCESS" "Removed $dir_count $cache_dir directories ($(($dir_size * 1024)) bytes)"
                total_removed=$(($total_removed + $dir_count))
            fi
        done

        if [ "$total_removed" -gt 0 ]; then
            log "SUCCESS" "Cleaned $total_removed cache directories successfully"
        else
            log "INFO" "No cache directories found to clean"
        fi
    fi
}

# Clean temporary root files specifically
clean_root_temp_files() {
    log "STEP" "Cleaning temporary files from root directory"

    # List of specific files to target
    local temp_patterns=(
        "all_*_files.txt"
        "*_endpoints.txt"
        "*-files.txt"
        "*_summary.md"
        "*_summary.txt"
        "*.temp"
        "*.tmp"
        "*.bak"
    )

    # List of specific files to clean directly
    local specific_files=(
        "all_py_files.txt"
        "successful_endpoints.txt"
        "vercel-deployment-files.txt"
        "integration-test-summary.md"
    )

    if [ "$DRY_RUN" = true ]; then
        local total_matches=0

        # Check patterns
        for pattern in "${temp_patterns[@]}"; do
            local count=$(find "$PROJECT_DIR" -maxdepth 1 -name "$pattern" | wc -l | tr -d ' ')
            total_matches=$((total_matches + count))
        done

        # Check specific files
        for file in "${specific_files[@]}"; do
            if [ -f "$PROJECT_DIR/$file" ]; then
                total_matches=$((total_matches + 1))
            fi
        done

        log "INFO" "Would remove $total_matches temporary files from root directory"
    else
        local removed_count=0

        # Remove pattern matches
        for pattern in "${temp_patterns[@]}"; do
            local matches=$(find "$PROJECT_DIR" -maxdepth 1 -name "$pattern")
            for file in $matches; do
                if [ -f "$file" ]; then
                    rm -f "$file"
                    log "INFO" "Removed temporary file: $(basename "$file")"
                    removed_count=$((removed_count + 1))
                fi
            done
        done

        # Remove specific files
        for file in "${specific_files[@]}"; do
            if [ -f "$PROJECT_DIR/$file" ]; then
                rm -f "$PROJECT_DIR/$file"
                log "INFO" "Removed specific temporary file: $file"
                removed_count=$((removed_count + 1))
            fi
        done

        if [ "$removed_count" -gt 0 ]; then
            log "SUCCESS" "Removed $removed_count temporary files from root directory"
        else
            log "INFO" "No temporary files found in root directory"
        fi
    fi
}

# Move files from root to appropriate directories following directory management protocol
organize_root_files() {
    log "STEP" "Organizing files from root directory to appropriate locations"

    # Define directory mappings [file_pattern, target_directory]
    local dir_mappings=(
        # Python files -> src or scripts directory
        "*.py|src"
        # Python test files -> tests directory
        "test_*.py|tests"
        # JavaScript/TypeScript files -> src directory
        "*.js|src"
        "*.ts|src"
        "*.tsx|src"
        # Shell scripts -> scripts directory
        "*.sh|scripts"
        # Research JSON files -> docs/research
        "*_research.json|docs/research"
        # Chart exports -> logs/chart_exports
        "chart_*.pdf|logs/chart_exports"
        # Chart exports directory -> logs/chart_exports
        "chart_exports|logs"
        # Documentation -> docs
        "*.md|docs/project_docs"
        # Configuration files -> config
        "*.config.js|config"
        # Docker related files -> docker
        "docker-compose*.yml|docker"
        # Playwright configurations -> tests/e2e
        "playwright*.config.*|tests/e2e"
    )

    # Special handling for chart_exports directory
    if [ -d "$PROJECT_DIR/chart_exports" ] && [ ! "$DRY_RUN" = true ]; then
        # Check if it's empty
        if [ -z "$(ls -A "$PROJECT_DIR/chart_exports" 2>/dev/null)" ]; then
            # Remove empty directory
            rmdir "$PROJECT_DIR/chart_exports" 2>/dev/null || rm -rf "$PROJECT_DIR/chart_exports" 2>/dev/null
            log "INFO" "Removed empty chart_exports directory from root"
        fi
    fi

    if [ "$DRY_RUN" = true ]; then
        local total_to_move=0

        # Check mappings
        for mapping in "${dir_mappings[@]}"; do
            IFS='|' read -r pattern target_dir <<< "$mapping"

            # Handle directory patterns
            if [[ "$pattern" != *"*"* && -d "$PROJECT_DIR/$pattern" ]]; then
                log "INFO" "Would move directory '$pattern' to $target_dir/"
                total_to_move=$((total_to_move + 1))
                continue
            fi

            # Handle file patterns
            local matches=$(find "$PROJECT_DIR" -maxdepth 1 -name "$pattern" | wc -l | tr -d ' ')

            if [ "$matches" -gt 0 ]; then
                log "INFO" "Would move $matches files matching '$pattern' to $target_dir/"
                total_to_move=$((total_to_move + matches))
            fi
        done

        # Handle specific files
        if [ -f "$PROJECT_DIR/README.md" ]; then
            log "INFO" "Would keep README.md in root directory"
        fi

        if [ -f "$PROJECT_DIR/LICENSE" ]; then
            log "INFO" "Would keep LICENSE in root directory"
        fi

        log "INFO" "Would organize total of $total_to_move files from root directory"
    else
        local moved_count=0

        # Process mappings
        for mapping in "${dir_mappings[@]}"; do
            IFS='|' read -r pattern target_dir <<< "$mapping"

            # Create target directory if it doesn't exist
            if [ ! -d "$PROJECT_DIR/$target_dir" ]; then
                mkdir -p "$PROJECT_DIR/$target_dir"
                log "INFO" "Created directory: $target_dir"
            fi

            # Handle directory patterns - for specific named directories
            if [[ "$pattern" != *"*"* && -d "$PROJECT_DIR/$pattern" ]]; then
                # Special case for chart_exports directory
                if [ "$pattern" = "chart_exports" ]; then
                    # Create the target directory
                    mkdir -p "$PROJECT_DIR/$target_dir/$pattern"

                    # Move all content instead of the directory itself
                    # This preserves the chart_exports directory structure
                    if [ -d "$PROJECT_DIR/$pattern" ] && [ "$(ls -A "$PROJECT_DIR/$pattern" 2>/dev/null)" ]; then
                        cp -r "$PROJECT_DIR/$pattern"/* "$PROJECT_DIR/$target_dir/$pattern"/ 2>/dev/null
                        rm -rf "$PROJECT_DIR/$pattern"/* 2>/dev/null
                        log "INFO" "Moved contents of $pattern directory to $target_dir/$pattern/"
                        moved_count=$((moved_count + 1))
                    fi
                    continue
                fi

                # For other directories, move the directory itself
                if [ -d "$PROJECT_DIR/$pattern" ]; then
                    mv "$PROJECT_DIR/$pattern" "$PROJECT_DIR/$target_dir/"
                    log "INFO" "Moved directory $pattern to $target_dir/"
                    moved_count=$((moved_count + 1))
                fi
                continue
            fi

            # Find and move files
            local matches=$(find "$PROJECT_DIR" -maxdepth 1 -name "$pattern")
            for file in $matches; do
                if [ -f "$file" ]; then
                    # Skip README.md and LICENSE
                    filename=$(basename "$file")
                    if [ "$filename" = "README.md" ] || [ "$filename" = "LICENSE" ]; then
                        log "INFO" "Keeping $filename in root directory"
                        continue
                    fi

                    # Move the file
                    mv "$file" "$PROJECT_DIR/$target_dir/"
                    log "INFO" "Moved $filename to $target_dir/"
                    moved_count=$((moved_count + 1))
                fi
            done
        done

        if [ "$moved_count" -gt 0 ]; then
            log "SUCCESS" "Organized $moved_count files from root directory"
        else
            log "INFO" "No files to organize from root directory"
        fi
    fi
}

# Clean logs directory to prevent disk space issues
clean_logs_directory() {
    log "STEP" "Cleaning old logs to free up disk space"

    # Define log directories to clean
    local log_dirs=(
        "logs"
        "logs/chart_exports"
    )

    # Define log file patterns to clean
    local log_patterns=(
        "*.log"
        "*_report.txt"
        "cleanup_*.log"
        "macos_cleanup_*.log"
    )

    # Keep logs from last 7 days
    local days_to_keep=7

    if [ "$DRY_RUN" = true ]; then
        local total_logs=0

        for dir in "${log_dirs[@]}"; do
            if [ -d "$PROJECT_DIR/$dir" ]; then
                for pattern in "${log_patterns[@]}"; do
                    local count=$(find "$PROJECT_DIR/$dir" -type f -name "$pattern" -mtime +$days_to_keep 2>/dev/null | wc -l | tr -d ' ')
                    if [ "$count" -gt 0 ]; then
                        local size=$(find "$PROJECT_DIR/$dir" -type f -name "$pattern" -mtime +$days_to_keep -ls 2>/dev/null | awk '{sum += $7} END {print sum}')
                        log "INFO" "Would remove $count old $pattern files from $dir (older than $days_to_keep days, $(format_size $size))"
                        total_logs=$((total_logs + count))
                    fi
                done
            fi
        done

        log "INFO" "Would clean total of $total_logs old log files"
    else
        local removed_count=0
        local total_size=0

        for dir in "${log_dirs[@]}"; do
            if [ -d "$PROJECT_DIR/$dir" ]; then
                for pattern in "${log_patterns[@]}"; do
                    # Calculate size before deletion
                    local size=$(find "$PROJECT_DIR/$dir" -type f -name "$pattern" -mtime +$days_to_keep -ls 2>/dev/null | awk '{sum += $7} END {print sum}')
                    if [ -z "$size" ]; then size=0; fi
                    total_size=$((total_size + size))

                    # Delete old logs
                    local count=$(find "$PROJECT_DIR/$dir" -type f -name "$pattern" -mtime +$days_to_keep -delete -print 2>/dev/null | wc -l | tr -d ' ')

                    if [ "$count" -gt 0 ]; then
                        log "INFO" "Removed $count old $pattern files from $dir (older than $days_to_keep days)"
                        removed_count=$((removed_count + count))
                    fi
                done
            fi
        done

        if [ "$removed_count" -gt 0 ]; then
            log "SUCCESS" "Cleaned $removed_count old log files ($(format_size $total_size))"
        else
            log "INFO" "No old log files to clean"
        fi
    fi
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

# Default options
CLEAN_PROJECT=true
DRY_RUN=false
VERBOSE=false
SKIP_SYSTEM_CACHE=false
DETECT_REDUNDANT=true
RUN_JS_CLEANUP=true
ORGANIZE_RESEARCH=true
TERMINAL_UI_AVAILABLE=false  # Will be set to true if terminal_ui.sh is found
USE_TERMINAL_UI=true         # Whether to attempt to use terminal UI

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --help)
            echo "Usage: sudo $0 [OPTIONS]"
            echo ""
            echo "High-performance cleanup script for macOS. Cleans system caches and project directories."
            echo ""
            echo "OPTIONS:"
            echo "  --help              Display this help message and exit"
            echo "  --dry-run           Show what would be deleted without actually deleting"
            echo "  --verbose           Show detailed output of operations"
            echo "  --skip-system-cache Skip system cache cleanup (avoids permission errors)"
            echo "  --no-project        Skip project directory cleanup"
            echo "  --safe              Run in safe mode (skip system cache + dry run)"
            echo "  --no-redundant      Skip redundant file detection"
            echo "  --no-js-cleanup     Skip JavaScript cleanup scripts"
            echo "  --no-organize       Skip organizing research files"
            echo "  --no-ui             Disable terminal UI (spinner and progress bar)"
            echo ""
            echo "EXAMPLES:"
            echo "  sudo $0                       Run full cleanup"
            echo "  sudo $0 --skip-system-cache   Skip system caches (avoids permission issues)"
            echo "  sudo $0 --safe                Run in safe mode (preview what would be cleaned)"
            echo "  sudo $0 --no-redundant        Skip redundant file detection"
            exit 0
            ;;
        --no-ui)
            USE_TERMINAL_UI=false
            shift
            ;;
        --safe)
            DRY_RUN=true
            SKIP_SYSTEM_CACHE=true
            shift
            ;;
        --no-project)
            CLEAN_PROJECT=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --skip-system-cache)
            SKIP_SYSTEM_CACHE=true
            shift
            ;;
        --no-redundant)
            DETECT_REDUNDANT=false
            shift
            ;;
        --no-js-cleanup)
            RUN_JS_CLEANUP=false
            shift
            ;;
        --no-organize)
            ORGANIZE_RESEARCH=false
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Store original user info
ORIGINAL_USER=${SUDO_USER:-$USER}
ORIGINAL_HOME=$(eval echo ~$ORIGINAL_USER)

# Check if running as root for system operations
if [ "$(id -u)" -ne 0 ]; then
    log "ERROR" "Please run this script as root (using sudo)."
    exit 1
fi

# Set up trap for cleanup
trap 'cleanup_and_exit' EXIT INT TERM

# Create log file and start logging
LOGFILE="$ORIGINAL_HOME/macos_cleanup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOGFILE") 2>&1

# Print startup information
print_header "CLEANUP SCRIPT v$VERSION"
log "INFO" "Started at $(date)"
log "INFO" "Logging to $LOGFILE"
log "INFO" "Running in $(if [ "$DRY_RUN" = true ]; then echo "DRY RUN"; else echo "ACTUAL CLEANUP"; fi) mode"
log "INFO" "System cache cleanup: $(if [ "$SKIP_SYSTEM_CACHE" = true ]; then echo "DISABLED"; else echo "ENABLED"; fi)"
log "INFO" "Project directory cleanup: $(if [ "$CLEAN_PROJECT" = true ]; then echo "ENABLED"; else echo "DISABLED"; fi)"

# Collect metrics before cleanup
collect_metrics "BEFORE"

# Run system cache cleanup if enabled
if [ "$SKIP_SYSTEM_CACHE" = false ]; then
    IS_SUBPROCESS=true
    clean_system_caches
    IS_SUBPROCESS=false
fi

# Run project directory cleanup if enabled
if [ "$CLEAN_PROJECT" = true ]; then
    IS_SUBPROCESS=true
    clean_project_directory
    IS_SUBPROCESS=false

    # Run the new detection of redundant files
    if [ "$DETECT_REDUNDANT" = true ]; then
        IS_SUBPROCESS=true
        detect_redundant_files
        IS_SUBPROCESS=false
    fi

    # The JavaScript cleanup scripts are already run inside clean_project_directory
    # No need to run them again here
fi

# Run system maintenance
IS_SUBPROCESS=true
run_system_maintenance
IS_SUBPROCESS=false

# Collect metrics after cleanup
collect_metrics "AFTER"

# Compare before and after metrics
compare_metrics

# Print completion message
print_header "CLEANUP COMPLETED"
log "SUCCESS" "Cleanup process completed successfully"
