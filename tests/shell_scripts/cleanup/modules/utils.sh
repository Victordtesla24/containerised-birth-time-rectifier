#!/bin/bash
#
# Utility functions for code duplication detection
#

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Log a message with a timestamp
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Format by log level
    case "$level" in
        "DEBUG")
            if [ "$VERBOSE" = true ]; then
                echo -e "\033[0;34m[${timestamp}] ${level}: ${message}\033[0m" >&2
            fi
            ;;
        "INFO")
            echo -e "\033[0;34m[${timestamp}] ${level}: ${message}\033[0m" >&2
            ;;
        "WARN")
            echo -e "\033[0;33m[${timestamp}] ${level}: ${message}\033[0m" >&2
            ;;
        "ERROR")
            echo -e "\033[0;31m[${timestamp}] ${level}: ${message}\033[0m" >&2
            ;;
        *)
            echo -e "[${timestamp}] ${level}: ${message}" >&2
            ;;
    esac
}

# Cleanup temporary files
cleanup() {
    for file in "$@"; do
        if [ -e "$file" ]; then
            rm -rf "$file" 2>/dev/null || true
        fi
    done
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get the maximum of two numbers
max() {
    echo $(( $1 > $2 ? $1 : $2 ))
}

# Get the minimum of two numbers
min() {
    echo $(( $1 < $2 ? $1 : $2 ))
}

# Format a file path for display (truncate if too long)
format_path() {
    local path="$1"
    local max_length="${2:-80}"

    if [ ${#path} -gt "$max_length" ]; then
        # Truncate the middle of the path
        local prefix_len=$(( (max_length - 3) / 2 ))
        local suffix_len=$(( max_length - 3 - prefix_len ))
        echo "${path:0:$prefix_len}...${path:(-$suffix_len)}"
    else
        echo "$path"
    fi
}

# Compute the time elapsed since a given timestamp
compute_elapsed_time() {
    local start_time="$1"
    local end_time=$(date +%s)
    local elapsed_seconds=$((end_time - start_time))

    # Format the elapsed time
    if [ "$elapsed_seconds" -ge 3600 ]; then
        printf "%dh %dm %ds" $((elapsed_seconds / 3600)) $(((elapsed_seconds % 3600) / 60)) $((elapsed_seconds % 60))
    elif [ "$elapsed_seconds" -ge 60 ]; then
        printf "%dm %ds" $((elapsed_seconds / 60)) $((elapsed_seconds % 60))
    else
        printf "%ds" "$elapsed_seconds"
    fi
}

# Find the most common value in a list
find_most_common() {
    local items=("$@")
    local counts=()
    local uniq_items=()

    # Count occurrences
    for item in "${items[@]}"; do
        local found=false
        for i in "${!uniq_items[@]}"; do
            if [ "${uniq_items[$i]}" = "$item" ]; then
                counts[$i]=$((counts[$i] + 1))
                found=true
                break
            fi
        done

        if [ "$found" = false ]; then
            uniq_items+=("$item")
            counts+=(1)
        fi
    done

    # Find the most common
    local max_count=0
    local max_index=0
    for i in "${!counts[@]}"; do
        if [ "${counts[$i]}" -gt "$max_count" ]; then
            max_count="${counts[$i]}"
            max_index="$i"
        fi
    done

    echo "${uniq_items[$max_index]}"
}

# Check if a value is in an array
in_array() {
    local needle="$1"
    shift
    local haystack=("$@")

    for item in "${haystack[@]}"; do
        if [ "$item" = "$needle" ]; then
            return 0
        fi
    done

    return 1
}

# Join array elements with a delimiter
join_by() {
    local delimiter="$1"
    shift
    local array=("$@")

    local result=""
    for i in "${!array[@]}"; do
        if [ "$i" -gt 0 ]; then
            result+="$delimiter"
        fi
        result+="${array[$i]}"
    done

    echo "$result"
}

# Get file extension
get_extension() {
    local filename="$1"
    echo "${filename##*.}"
}

# Get filename without path
get_filename() {
    local filepath="$1"
    echo "$(basename "$filepath")"
}

# Get directory of a file
get_directory() {
    local filepath="$1"
    echo "$(dirname "$filepath")"
}

# Strip comments from a file
strip_comments() {
    local file="$1"
    local temp_file=$(mktemp)

    # Different comment styles based on file extension
    local ext=$(get_extension "$file")
    case "$ext" in
        py)
            # Python: strip # comments and docstrings
            python3 -c "import re; content = open('$file').read(); content = re.sub(r'#.*$', '', content, flags=re.MULTILINE); content = re.sub(r'\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'', '', content, flags=re.DOTALL); print(content)" > "$temp_file" 2>/dev/null || cat "$file" > "$temp_file"
            ;;
        js|ts)
            # JavaScript/TypeScript: strip // and /* */ comments
            python3 -c "import re; content = open('$file').read(); content = re.sub(r'//.*$', '', content, flags=re.MULTILINE); content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL); print(content)" > "$temp_file" 2>/dev/null || cat "$file" > "$temp_file"
            ;;
        *)
            # Default: just copy the file
            cat "$file" > "$temp_file"
            ;;
    esac

    echo "$temp_file"
}

# Check if jq is installed, which is required for JSON processing
check_jq() {
    if ! command_exists jq; then
        log "ERROR" "jq is required but not installed"
        echo "Please install jq: https://stedolan.github.io/jq/download/"
        return 1
    fi
    return 0
}

# Run a command with a timeout
run_with_timeout() {
    local timeout=$1
    local cmd=$2
    local args=${@:3}

    # Create a temporary file for results
    local temp_result=$(mktemp)

    # Run the command in background
    (
        # Execute command and capture output
        eval "$cmd $args" > "$temp_result" 2>&1
        echo $? > "${temp_result}.exit"
    ) &

    local pid=$!

    # Wait up to timeout seconds
    local i=0
    while [ $i -lt $timeout ]; do
        if ! kill -0 $pid 2>/dev/null; then
            # Process has finished
            if [ -f "${temp_result}.exit" ]; then
                local exit_code=$(cat "${temp_result}.exit")
                cat "$temp_result"
                rm -f "$temp_result" "${temp_result}.exit"
                return $exit_code
            fi
            break
        fi
        sleep 1
        i=$((i + 1))
    done

    # If we're here, the process timed out
    kill -9 $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    log "WARN" "Command timed out after ${timeout} seconds: $cmd $args"
    echo "TIMEOUT" > "$temp_result"
    cat "$temp_result"
    rm -f "$temp_result" "${temp_result}.exit" 2>/dev/null || true
    return 124  # Standard timeout exit code
}

# Export functions for use in other modules
export -f log
export -f cleanup
export -f command_exists
export -f max
export -f min
export -f format_path
export -f compute_elapsed_time
export -f find_most_common
export -f in_array
export -f join_by
export -f get_extension
export -f get_filename
export -f get_directory
export -f strip_comments
export -f check_jq
export -f run_with_timeout
