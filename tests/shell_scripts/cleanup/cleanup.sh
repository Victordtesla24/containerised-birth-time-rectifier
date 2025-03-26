#!/bin/bash
#
# Enhanced Project Cleanup Script
# Purpose: Free up disk space and organize project files
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Set strict mode
set -eo pipefail

# Version
VERSION="3.1.0"

# Script directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Include helper scripts
DUPLICATION_IDENTIFIER="${SCRIPT_DIR}/duplication_identifier.sh"

# Log file and directories
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/cleanup_${TIMESTAMP}.log"
REPORT_DIR="${PROJECT_ROOT}/reports"
REPORT_FILE="${REPORT_DIR}/cleanup_report_${TIMESTAMP}.txt"
DUPLICATION_REPORT="${REPORT_DIR}/duplication_report_${TIMESTAMP}.txt"

# Basic constants for formatting output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
MAGENTA="\033[0;35m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

# Default options
DRY_RUN=false
VERBOSE=false
CLEAN_PROJECT=true
CLEAN_ROOT_DIR=true
ANALYZE_DUPLICATES=false
SKIP_SYSTEM_CACHE=true
ORGANIZE_FILES=true
DAYS_TO_KEEP=7

# Define file mappings for relocating files in the root directory
# Format: "pattern|target_directory|description"
FILE_MAPPINGS=(
    "*.py|python|Python scripts"
    "*.js|src/scripts|JavaScript scripts"
    "*.ts|src/scripts|TypeScript scripts"
    "*.json|config/json|JSON configuration files"
    "*.md|docs|Markdown documentation"
    "*.yml|config|YAML configuration files"
    "*.yaml|config|YAML configuration files"
    "*.conf|config|Configuration files"
    "*.css|src/styles|CSS style files"
    "*.scss|src/styles|SCSS style files"
    "*.html|src/templates|HTML template files"
    "*.sh|scripts|Shell scripts"
    "Dockerfile*|docker|Docker files"
    "docker-compose*.yml|docker|Docker Compose files"
    ".env*|env|Environment files"
    ".babelrc|config|Babel configuration"
    ".eslintrc*|config/eslint|ESLint configuration"
    "*.Dockerfile|docker|Docker files"
    "tsconfig*.json|config|TypeScript configuration"
    "jest.config.js|config|Jest configuration"
    "next.config.js|config|Next.js configuration"
    "babel.config.js|config|Babel configuration"
    "postcss.config.js|config|PostCSS configuration"
    "tailwind.config.js|config|Tailwind configuration"
    ".dockerignore|config/dockerfiles|Docker ignore file"
    ".gitignore|config/git|Git ignore file"
    ".npmignore|config/npm|NPM ignore file"
    ".npmrc|config/npm|NPM configuration file"
)

# Files to always keep in the root directory
ROOT_KEEP_FILES=(
    "README.md"
    "LICENSE"
    "package.json"
    "package-lock.json"
    ".cursorignore"
    ".service_config.json"
    "cleanup.sh"
)

# Files to strictly remove from root directory (no symlinks or copies)
ROOT_REMOVE_FILES=(
    ".eslintrc.json"
    ".gitignore"
    ".dockerignore"
    ".npmrc"
    ".npmignore"
)

# Directories for organizing files (keep only one version)
CONFIG_DIRS=(
    "config/eslint"
    "config/git"
    "config/dockerfiles"
    "config/npm"
    "config/json"
)

# Directories to clean
CLEANABLE_DIRS=(
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    "__pycache__"
    ".swc"
    ".parcel-cache"
    ".next"
    "node_modules" # Be careful with this!
)

# File patterns to clean
CLEANABLE_FILES=(
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".coverage"
    "*.egg-info"
    "*.log"
    "*.tmp"
    "*.temp"
    "*.bak"
    "*.orig"
    ".DS_Store"
)

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
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${color}[${timestamp}] ${level}: ${message}${RESET}" | tee -a "$LOG_FILE"
}

# Print section header
print_header() {
    local title="$1"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BOLD}${MAGENTA}====== $title ======${RESET}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

# Print usage
print_usage() {
    echo -e "${BOLD}${MAGENTA}Birth Time Rectifier - Project Cleanup Utility v${VERSION}${RESET}"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --dry-run               Show what would be deleted without actually deleting"
    echo "  --verbose               Show detailed output of operations"
    echo "  --no-project            Skip project directory cleanup"
    echo "  --no-root-cleanup       Skip root directory reorganization"
    echo "  --analyze-duplicates    Analyze code duplication"
    echo "  --no-organize           Skip organizing project files"
    echo "  --keep-days DAYS        Days to keep logs (default: 7)"
    echo "  --keep-in-root FILE     Add a file to keep in root directory"
    echo "  --help                  Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                              # Run standard cleanup"
    echo "  $0 --dry-run                    # Preview what would be cleaned"
    echo "  $0 --analyze-duplicates         # Also analyze code duplication"
    echo "  $0 --keep-days 14               # Keep logs for 14 days"
}

# Check if a file should be kept in root
should_keep_in_root() {
    local file="$1"
    local basename=$(basename "$file")

    for keep_file in "${ROOT_KEEP_FILES[@]}"; do
        if [[ "$basename" == "$keep_file" ]]; then
            return 0
        fi
    done

            return 1
}

# Calculate and format size
format_size() {
    local size="$1"

    if [[ -z "$size" || "$size" == "0" ]]; then
        echo "0 bytes"
        return
    fi

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

# Create directories if they don't exist
create_directories() {
    log "INFO" "Creating necessary directories"

    mkdir -p "$LOG_DIR" 2>/dev/null || true
    mkdir -p "$REPORT_DIR" 2>/dev/null || true

    for mapping in "${FILE_MAPPINGS[@]}"; do
        IFS='|' read -r pattern target_dir description <<< "$mapping"
        mkdir -p "${PROJECT_ROOT}/${target_dir}" 2>/dev/null || true
    done
}

# ==============================================================================
# MAIN CLEANING FUNCTIONS
# ==============================================================================

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
        local total_size=$(cut -d' ' -f1 "$temp_size_file" 2>/dev/null || echo "0")
        local count=$(cut -d' ' -f2 "$temp_size_file" 2>/dev/null || echo "0")
        rm -f "$temp_size_file"

        if [ -z "$total_size" ]; then total_size=0; fi
        if [ -z "$count" ]; then count=0; fi

        # Show what would be cleaned
        local formatted_size=$(format_size "$total_size")
        log "INFO" "Would remove $count files ($formatted_size)"

        # List some examples if verbose
        if [ "$VERBOSE" = true ] && [ "$count" -gt 0 ]; then
            eval "$find_cmd -print 2>/dev/null | head -5" | while read file; do
                log "INFO" "Would remove: $file"
            done

            if [ "$count" -gt 5 ]; then
                log "INFO" "... and $(($count - 5)) more"
            fi
        fi
    else
        # Calculate total size before deletion
        local temp_size_file="/tmp/cleanup_size_$$"
        eval "$find_cmd -ls 2>/dev/null" | awk '{total_size += $7; count++} END {print total_size, count}' > "$temp_size_file"
        local total_size=$(cut -d' ' -f1 "$temp_size_file" 2>/dev/null || echo "0")
        local count=$(cut -d' ' -f2 "$temp_size_file" 2>/dev/null || echo "0")
        rm -f "$temp_size_file"

        if [ -z "$total_size" ]; then total_size=0; fi
        if [ -z "$count" ]; then count=0; fi

        # Perform the actual deletion
        if [ "$count" -gt 0 ]; then
            if [ "$VERBOSE" = true ]; then
                eval "$find_cmd -print -delete 2>/dev/null" | wc -l | xargs -I{} log "INFO" "Removed {} files"
            else
                eval "$find_cmd -delete 2>/dev/null"
                log "SUCCESS" "Removed $count files ($(format_size "$total_size"))"
            fi
        else
            log "INFO" "No matching files found"
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

    # Build find command with depth to process deepest directories first
    local find_cmd="find \"$dir\" -type d -name \"$pattern\" -depth"
    if [ -n "$exclusion" ]; then
        find_cmd="$find_cmd ! -path \"$exclusion\""
    fi

    if [ "$DRY_RUN" = true ]; then
        # Calculate total size and count
        local temp_size_file="/tmp/cleanup_dirsize_$$"
        eval "$find_cmd -exec du -sk {} \; 2>/dev/null" | awk '{total_size += $1 * 1024; count++} END {print total_size, count}' > "$temp_size_file"
        local total_size=$(cut -d' ' -f1 "$temp_size_file" 2>/dev/null || echo "0")
        local count=$(cut -d' ' -f2 "$temp_size_file" 2>/dev/null || echo "0")
        rm -f "$temp_size_file"

        if [ -z "$total_size" ]; then total_size=0; fi
        if [ -z "$count" ]; then count=0; fi

        # Show what would be cleaned
        local formatted_size=$(format_size "$total_size")
        log "INFO" "Would remove $count directories ($formatted_size)"

        # List some examples if verbose
        if [ "$VERBOSE" = true ] && [ "$count" -gt 0 ]; then
            eval "$find_cmd -print 2>/dev/null | head -5" | while read dir; do
                log "INFO" "Would remove: $dir"
            done

            if [ "$count" -gt 5 ]; then
                log "INFO" "... and $(($count - 5)) more"
            fi
        fi
    else
        # Get list of directories before deletion for size calculation
        local temp_dir_list="/tmp/cleanup_dirlist_$$"
        eval "$find_cmd -print 2>/dev/null" > "$temp_dir_list"
        local count=$(wc -l < "$temp_dir_list" 2>/dev/null || echo "0")

        # Calculate total size if directories exist
        local total_size=0
        if [ "$count" -gt 0 ] && [ "$count" != "0" ]; then
            local temp_size_file="/tmp/cleanup_dirsize_$$"
            cat "$temp_dir_list" | xargs -I{} du -sk {} 2>/dev/null | awk '{total_size += $1 * 1024} END {print total_size}' > "$temp_size_file"
            total_size=$(cat "$temp_size_file" 2>/dev/null || echo "0")
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

            log "SUCCESS" "Removed $count directories ($(format_size "$total_size"))"
        else
            log "INFO" "No matching directories found"
        fi

        rm -f "$temp_dir_list"
    fi
}

# Clean log files
clean_logs() {
    local log_dir="$1"
    local days="$2"

    if [ ! -d "$log_dir" ]; then
        log "INFO" "Log directory not found: $log_dir"
        return 0
    fi

    log "STEP" "Cleaning log files older than $days days in $log_dir"

        if [ "$DRY_RUN" = true ]; then
        local count=$(find "$log_dir" -type f -name "*.log" -mtime +$days | wc -l | tr -d ' ')
        local size=$(find "$log_dir" -type f -name "*.log" -mtime +$days -ls | awk '{total += $7} END {print total}')

        log "INFO" "Would remove $count log files ($(format_size "$size"))"
    else
        local count=$(find "$log_dir" -type f -name "*.log" -mtime +$days | wc -l | tr -d ' ')
        local size=$(find "$log_dir" -type f -name "*.log" -mtime +$days -ls | awk '{total += $7} END {print total}')

        if [ "$count" -gt 0 ]; then
            find "$log_dir" -type f -name "*.log" -mtime +$days -delete
            log "SUCCESS" "Removed $count log files older than $days days ($(format_size "$size"))"
        else
            log "INFO" "No old log files to remove"
        fi
    fi
}

# Clean project directory
clean_project_directory() {
    print_header "CLEANING PROJECT DIRECTORY"
    log "INFO" "Starting project directory cleanup"

    # Clean Python cache files
    for dir in "${CLEANABLE_DIRS[@]}"; do
        clean_directories "$PROJECT_ROOT" "$dir" "$dir directories"
    done

    # Clean temporary and compiled files
    for pattern in "${CLEANABLE_FILES[@]}"; do
        clean_files "$PROJECT_ROOT" "$pattern" "$pattern files"
    done

    # Clean old logs
    clean_logs "$LOG_DIR" "$DAYS_TO_KEEP"

    log "SUCCESS" "Project directory cleanup completed"
}

# Organize files in the root directory
organize_root_directory() {
    print_header "ORGANIZING ROOT DIRECTORY"
    log "INFO" "Starting root directory organization"

    # Create target directories if they don't exist
    create_directories

    local total_moved=0
    local total_size=0

    # Create a list of files in the root directory
    local temp_file_list="/tmp/cleanup_root_files_$$"
    find "$PROJECT_ROOT" -maxdepth 1 -type f > "$temp_file_list"

    # Process each file mapping
    for mapping in "${FILE_MAPPINGS[@]}"; do
        IFS='|' read -r pattern target_dir description <<< "$mapping"
        local target_path="${PROJECT_ROOT}/${target_dir}"

        # Find matching files
        local matched_files=()
        local matched_sizes=()

        while read -r file; do
            local basename=$(basename "$file")

            # Check if file matches pattern and shouldn't be kept in root
            if [[ "$basename" == $pattern ]] && ! should_keep_in_root "$file"; then
                matched_files+=("$file")

                # Get file size
                local size=$(stat -f %z "$file" 2>/dev/null || stat -c %s "$file" 2>/dev/null || echo "0")
                matched_sizes+=("$size")
                total_size=$((total_size + size))
            fi
        done < "$temp_file_list"

        # Process matched files
        if [ ${#matched_files[@]} -gt 0 ]; then
            log "INFO" "Found ${#matched_files[@]} $description to organize"

            # Create target directory if it doesn't exist
            mkdir -p "$target_path" 2>/dev/null || true

            # Move or copy files
            for i in "${!matched_files[@]}"; do
                local file="${matched_files[$i]}"
                local basename=$(basename "$file")
                local size="${matched_sizes[$i]}"

                if [ "$DRY_RUN" = true ]; then
                    log "INFO" "Would move '$basename' to '${target_dir}/' ($(format_size "$size"))"
                else
                    # Move the file to the target directory
                    if cp "$file" "${target_path}/" 2>/dev/null; then
                        # Remove the file from root (no symlinks)
                        rm -f "$file"
                        log "INFO" "Moved '$basename' to '${target_dir}/' ($(format_size "$size"))"
                        total_moved=$((total_moved + 1))
                    else
                        log "WARNING" "Failed to organize '$basename'"
                fi
            fi
        done
    fi
    done

    rm -f "$temp_file_list"

        if [ "$DRY_RUN" = true ]; then
        log "INFO" "Would organize $total_moved files ($(format_size "$total_size"))"
    else
        if [ "$total_moved" -gt 0 ]; then
            log "SUCCESS" "Organized $total_moved files ($(format_size "$total_size"))"
        else
            log "INFO" "No files to organize"
        fi
    fi
}

# Analyze code duplication
analyze_code_duplication() {
    print_header "ANALYZING CODE DUPLICATION"

    if [ ! -f "$DUPLICATION_IDENTIFIER" ]; then
        log "ERROR" "Duplication identifier script not found at: $DUPLICATION_IDENTIFIER"
        return 1
    fi

    log "INFO" "Starting code duplication analysis"

    # Target directories for analysis
    local target_dirs=(
        "ai_service"
        "api_gateway"
        "src"
    )

    # Check directories exist
    local valid_dirs=()
    for dir in "${target_dirs[@]}"; do
        if [ -d "${PROJECT_ROOT}/${dir}" ]; then
            valid_dirs+=("${PROJECT_ROOT}/${dir}")
        fi
    done

    if [ ${#valid_dirs[@]} -eq 0 ]; then
        log "WARNING" "No valid directories to analyze"
        return 1
    fi

    # Run the duplication analysis
    log "STEP" "Running duplication identifier on ${#valid_dirs[@]} directories"

    local duplication_args=(
        "--output" "$DUPLICATION_REPORT"
        "--threshold" "0.7"
    )

    if [ "$VERBOSE" = true ]; then
        duplication_args+=("--verbose")
    fi

        if [ "$DRY_RUN" = true ]; then
        log "INFO" "Would run duplication analysis on: ${valid_dirs[*]}"
        log "INFO" "Command: $DUPLICATION_IDENTIFIER ${duplication_args[*]} ${valid_dirs[*]}"
    else
        log "INFO" "Running duplication analysis, this may take a while..."

        if ! "$DUPLICATION_IDENTIFIER" "${duplication_args[@]}" "${valid_dirs[@]}" >> "$LOG_FILE" 2>&1; then
            log "ERROR" "Duplication analysis failed"
            return 1
        fi

        log "SUCCESS" "Duplication analysis completed"
        log "INFO" "Report saved to: $DUPLICATION_REPORT"
    fi
}

# Generate cleanup report
generate_report() {
    log "STEP" "Generating cleanup report"

    {
        echo "========================================================"
        echo "           PROJECT CLEANUP REPORT"
        echo "========================================================"
        echo
        echo "Generated on: $(date)"
        echo "Mode: $([ "$DRY_RUN" = true ] && echo "Dry Run (no changes made)" || echo "Actual Cleanup")"
        echo

        echo "DIRECTORIES CLEANED:"
        echo "------------------"
        for dir in "${CLEANABLE_DIRS[@]}"; do
            echo "* $dir"
        done
        echo

        echo "FILE PATTERNS CLEANED:"
        echo "-------------------"
        for pattern in "${CLEANABLE_FILES[@]}"; do
            echo "* $pattern"
        done
        echo

        if [ "$ORGANIZE_FILES" = true ]; then
            echo "FILE ORGANIZATION:"
            echo "-----------------"
            for mapping in "${FILE_MAPPINGS[@]}"; do
                IFS='|' read -r pattern target_dir description <<< "$mapping"
                echo "* $pattern -> $target_dir/ ($description)"
            done
            echo
        fi

        echo "KEPT IN ROOT DIRECTORY:"
        echo "--------------------"
        for file in "${ROOT_KEEP_FILES[@]}"; do
            echo "* $file"
        done
        echo

        echo "ADDITIONAL INFORMATION:"
        echo "---------------------"
        echo "* Log files older than $DAYS_TO_KEEP days were cleaned"
        if [ "$ANALYZE_DUPLICATES" = true ]; then
            echo "* Code duplication analysis was performed"
            if [ -f "$DUPLICATION_REPORT" ]; then
                echo "* Duplication report is available at: $DUPLICATION_REPORT"
            fi
        fi
        echo

        echo "For detailed information, see the log file:"
        echo "$LOG_FILE"
        echo
        echo "========================================================"
    } > "$REPORT_FILE"

    log "SUCCESS" "Report generated at: $REPORT_FILE"
}

# Clean up specific duplicate files and ensure only one version exists
clean_duplicate_config_files() {
    print_header "CLEANING DUPLICATE CONFIGURATION FILES"
    log "INFO" "Removing duplicate configuration files and keeping single versions"

    for file in "${ROOT_REMOVE_FILES[@]}"; do
        if [ -f "${PROJECT_ROOT}/${file}" ]; then
            # Find matching file in config directories
            found_match=false
            preferred_dir=""

            for config_dir in "${CONFIG_DIRS[@]}"; do
                if [ -f "${PROJECT_ROOT}/${config_dir}/${file}" ]; then
                    found_match=true
                    preferred_dir="${config_dir}"
                    break
                fi
            done

            if [ "$found_match" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    log "INFO" "Would remove duplicate '${file}' from root directory (already in ${preferred_dir})"
                else
                    rm -f "${PROJECT_ROOT}/${file}"
                    log "SUCCESS" "Removed duplicate '${file}' from root directory (using version in ${preferred_dir})"
                fi
            else
                # No match found, move file to appropriate directory
                for config_dir in "${CONFIG_DIRS[@]}"; do
                    if [[ "$file" == ".eslintrc"* && "$config_dir" == "config/eslint" ]] || \
                       [[ "$file" == ".gitignore" && "$config_dir" == "config/git" ]] || \
                       [[ "$file" == ".docker"* && "$config_dir" == "config/dockerfiles" ]] || \
                       [[ "$file" == ".npm"* && "$config_dir" == "config/npm" ]]; then

    if [ "$DRY_RUN" = true ]; then
                            log "INFO" "Would move '${file}' to ${config_dir} directory"
                        else
                            mkdir -p "${PROJECT_ROOT}/${config_dir}" 2>/dev/null || true
                            mv "${PROJECT_ROOT}/${file}" "${PROJECT_ROOT}/${config_dir}/"
                            log "SUCCESS" "Moved '${file}' to ${config_dir} directory"
                        fi
                        break
            fi
        done
            fi
            fi
        done

    log "SUCCESS" "Duplicate configuration file cleanup completed"
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --help)
            print_usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --no-project)
            CLEAN_PROJECT=false
            shift
            ;;
        --no-root-cleanup)
            CLEAN_ROOT_DIR=false
            shift
            ;;
        --analyze-duplicates)
            ANALYZE_DUPLICATES=true
            shift
            ;;
        --no-organize)
            ORGANIZE_FILES=false
            shift
            ;;
        --keep-days)
            DAYS_TO_KEEP="$2"
            shift 2
            ;;
        --keep-in-root)
            # Add the file to keep in root directory
            ROOT_KEEP_FILES+=("$2")
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

# Log script start
log "INFO" "Starting cleanup script v$VERSION"
log "INFO" "Project root: $PROJECT_ROOT"
log "INFO" "Options: DRY_RUN=$DRY_RUN, VERBOSE=$VERBOSE, CLEAN_PROJECT=$CLEAN_PROJECT, CLEAN_ROOT_DIR=$CLEAN_ROOT_DIR"

# Run cleanup operations
if [ "$CLEAN_PROJECT" = true ]; then
    clean_project_directory
fi

if [ "$CLEAN_ROOT_DIR" = true ]; then
    if [ "$ORGANIZE_FILES" = true ]; then
        organize_root_directory
    fi

    # Clean duplicate config files
    clean_duplicate_config_files
fi

if [ "$ANALYZE_DUPLICATES" = true ]; then
    analyze_code_duplication
fi

# Generate report
generate_report

# Print completion message
print_header "CLEANUP COMPLETED"
log "SUCCESS" "Cleanup process completed successfully!"

if [ "$DRY_RUN" = true ]; then
    log "INFO" "This was a dry run. No actual changes were made."
    log "INFO" "Run without --dry-run to perform actual cleanup."
fi

log "INFO" "Log file: $LOG_FILE"
log "INFO" "Report file: $REPORT_FILE"

exit 0
