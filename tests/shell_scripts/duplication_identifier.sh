#!/bin/bash
#
# Advanced Code Duplication Detector
# Identifies code duplications, simulated fallback mechanisms, mocked-up code,
# hardcoded values, and error masking in Python code with enhanced accuracy
#
# Usage: ./duplication_identifier.sh [options] <directory1> <directory2> ...
#
# Options:
#   -t, --threshold FLOAT  Similarity threshold (0.0-1.0, default: 0.7)
#   -m, --methods LIST     Comma-separated list of methods (token,ast,graph,hybrid)
#   -v, --verbose          Enable verbose output
#   -q, --quick            Quick mode (skip time-consuming operations for testing)
#   -h, --help             Show this help message
#

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="${SCRIPT_DIR}/cleanup/modules"

# Default options
QUICK_MODE=false

# Source modules
source "${MODULE_DIR}/config.sh"
source "${MODULE_DIR}/utils.sh"
source "${MODULE_DIR}/spinner.sh"
source "${MODULE_DIR}/file_comparison.sh"
source "${MODULE_DIR}/python_analyzer.sh"
source "${MODULE_DIR}/tree_analyzer.sh"
source "${MODULE_DIR}/hybrid_detector.sh"
source "${MODULE_DIR}/report_generator.sh"

# Show header and help
show_header() {
    echo -e "${BOLD}${BLUE}Advanced Code Duplication Detector${RESET}"
    echo "Identifies code duplications and quality issues in Python code"
    echo
}

show_help() {
    show_header
    echo "Usage: ./duplication_identifier.sh [options] <directory1> <directory2> ..."
    echo
    echo "Options:"
    echo "  -t, --threshold FLOAT  Similarity threshold (0.0-1.0, default: $SIMILARITY_THRESHOLD)"
    echo "  -m, --methods LIST     Comma-separated list of methods (token,ast,graph,hybrid)"
    echo "  -v, --verbose          Enable verbose output"
    echo "  -q, --quick            Quick mode (skip time-consuming operations for testing)"
    echo "  -h, --help             Show this help message"
    echo
    echo "Example:"
    echo "  ./duplication_identifier.sh -t 0.7 -m hybrid,ast -v ./src ./tests"
    echo
}

# Main execution function
main() {
    # Initialize spinner module
    init_spinner

    # Parse command line arguments
    parse_args "$@" || {
        show_help
        exit 1
    }

    # Show help if requested
    if [ "$SHOW_HELP" = true ]; then
        show_help
        exit 0
    fi

    # Welcome message
    show_animated_banner "Code Duplication Analysis" "gradient" 1.0

    # Create output directory
    local timestamp=$(date +%Y%m%d%H%M%S)
    local report_dir="reports/duplication_${timestamp}"
    mkdir -p "$report_dir"

    # Start the analysis
    log "INFO" "Starting code duplication analysis with threshold $SIMILARITY_THRESHOLD"
    log "INFO" "Using detection methods: ${DETECTION_METHODS[*]}"
    log "INFO" "Analyzing directories: ${DIRECTORIES[*]}"
    if [ "$QUICK_MODE" = true ]; then
        log "INFO" "Running in quick mode (skipping time-consuming operations)"
    fi

    # Setup Python environment
    start_fancy_spinner "Setting up Python environment" "dots"
    if ! setup_python_env; then
        stop_spinner false
        log "ERROR" "Failed to set up Python environment"
        exit 1
    fi
    stop_spinner true

    # Step 1: Analyze directory structure
    start_fancy_spinner "Analyzing directory structure" "flow"
    local structure_file="${report_dir}/structure_insights.txt"

    if [ "$QUICK_MODE" = true ]; then
        # In quick mode, create a minimal directory structure file
        echo "Directory structure analysis skipped in quick mode." > "$structure_file"
        stop_spinner true
    else
        local tree_result=$(analyze_directories_structure "${DIRECTORIES[@]}")
        if [ -f "$tree_result" ]; then
            cp "$tree_result" "$structure_file"
            stop_spinner true
        else
            stop_spinner false
            log "WARN" "Directory structure analysis failed"

            # Create an empty file to avoid errors in later steps
            echo "No structure analysis available" > "$structure_file"
        fi
    fi

    # Step 2: Analyze Python files for quality issues
    start_fancy_spinner "Analyzing code quality issues" "dots"
    local quality_file="${report_dir}/quality_issues.json"

    if [ "$QUICK_MODE" = true ]; then
        # In quick mode, create a minimal quality analysis file
        echo '{"status":"success","message":"Quality analysis skipped in quick mode","file_count":0,"similar_pairs":[],"files_with_issues":[]}' > "$quality_file"
        stop_spinner true
    else
        if ! run_python_analysis > "$quality_file"; then
            stop_spinner false
            log "ERROR" "Code quality analysis failed"
            echo '{"status":"error","message":"Analysis failed","file_count":0,"similar_pairs":[],"files_with_issues":[]}' > "$quality_file"
        else
            stop_spinner true
        fi
    fi

    # Step 3: Perform hybrid duplicate detection for enhanced accuracy
    start_fancy_spinner "Running hybrid duplicate detection" "pulse"
    local hybrid_file="${report_dir}/hybrid_duplicates.json"

    if [ "$QUICK_MODE" = true ]; then
        # In quick mode, create a minimal hybrid detection file
        echo '{"similar_pairs":[],"file_count":0,"processing_time":0,"message":"Hybrid detection skipped in quick mode"}' > "$hybrid_file"
        stop_spinner true
    else
        if ! run_hybrid_analysis "$SIMILARITY_THRESHOLD" "${DIRECTORIES[@]}" > "$hybrid_file"; then
            stop_spinner false
            log "ERROR" "Hybrid duplicate detection failed"
            echo '{"similar_pairs":[],"file_count":0,"processing_time":0,"error":"failed"}' > "$hybrid_file"
        else
            stop_spinner true
        fi
    fi

    # Step 4: Generate combined report
    start_fancy_spinner "Generating comprehensive report" "bounce"
    local report_file="${report_dir}/duplication_report.md"

    # Merge results from all analyses
    local merged_result=$(merge_results "$quality_file" "$hybrid_file" "$structure_file")
    echo "$merged_result" > "${report_dir}/merged_results.json"

    # Generate the report
    if ! generate_report "${report_dir}/merged_results.json" "$report_file"; then
        stop_spinner false
        log "ERROR" "Report generation failed"
        echo "Report generation failed. See logs for details." > "$report_file"
    else
        stop_spinner true
    fi

    # Show completion message
    show_enhanced_status "Analysis Complete" \
        "Report saved to: $report_file" \
        "Found $(jq -r '.similar_pairs | length' "${report_dir}/merged_results.json") similar file pairs" \
        "Identified $(jq -r '.files_with_issues | length' "${report_dir}/merged_results.json") files with code quality issues"

    log "INFO" "Analysis completed in $(compute_elapsed_time "$START_TIME")"
    echo -e "\n${BOLD}${GREEN}View the report at:${RESET} $report_file"
}

# Function to merge results from different analyses
merge_results() {
    local quality_file="$1"
    local hybrid_file="$2"
    local structure_file="$3"

    # Create Python script for merging results
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import json
import sys

# Load the quality analysis results
with open(sys.argv[1], 'r') as f:
    quality_data = json.load(f)

# Load the hybrid analysis results
with open(sys.argv[2], 'r') as f:
    hybrid_data = json.load(f)

# Load the structure analysis if available
try:
    with open(sys.argv[3], 'r') as f:
        structure_data = f.read()
except:
    structure_data = "No structure analysis available"

# Create merged results
result = {
    "file_count": max(quality_data.get("file_count", 0), hybrid_data.get("file_count", 0)),
    "similar_pairs": [],
    "files_with_issues": quality_data.get("files_with_issues", []),
    "structure_analysis": structure_data,
    "exact_duplicates": hybrid_data.get("exact_duplicates", []),
    "structural_duplicates": hybrid_data.get("structural_duplicates", []),
    "functional_duplicates": hybrid_data.get("functional_duplicates", [])
}

# Combine similar pairs from all sources
seen_pairs = set()

# Add similar pairs from quality analysis
for pair in quality_data.get("similar_pairs", []):
    file1 = pair.get("file1", "")
    file2 = pair.get("file2", "")
    if file1 and file2:
        pair_key = f"{file1}|{file2}"
        alt_key = f"{file2}|{file1}"
        if pair_key not in seen_pairs and alt_key not in seen_pairs:
            seen_pairs.add(pair_key)
            result["similar_pairs"].append(pair)

# Add similar pairs from hybrid analysis
for pair in hybrid_data.get("similar_pairs", []):
    file1 = pair.get("file1", "")
    file2 = pair.get("file2", "")
    if file1 and file2:
        pair_key = f"{file1}|{file2}"
        alt_key = f"{file2}|{file1}"
        if pair_key not in seen_pairs and alt_key not in seen_pairs:
            seen_pairs.add(pair_key)
            result["similar_pairs"].append(pair)

# Output merged results
print(json.dumps(result, indent=2))
EOF

    # Run the script
    python3 "$temp_script" "$quality_file" "$hybrid_file" "$structure_file"

    # Clean up
    rm -f "$temp_script"
}

# Record start time
START_TIME=$(date +%s)

# Cleanup function to ensure all processes are terminated
cleanup() {
    # Get exit code of the previous command
    local exit_code=$?

    # Reset terminal cursor if needed
    echo -en "\r\033[K"
    tput cnorm 2>/dev/null || true

    # Stop any active spinners or progress bars
    if type stop_spinner_no_message >/dev/null 2>&1; then
        stop_spinner_no_message
    fi

    if type stop_progress_no_message >/dev/null 2>&1; then
        stop_progress_no_message
    fi

    # Kill any background processes more aggressively
    jobs -p | xargs kill -9 2>/dev/null || true
    sleep 0.1

    # Send a SIGKILL to any remaining spinners
    pkill -f "_spinner" 2>/dev/null || true
    pkill -f "_progress_bar" 2>/dev/null || true

    # Clear any progress or spinner display again
    echo -en "\r\033[K"

    # Print a message if the script was interrupted
    if [ $exit_code -ne 0 ] && [ "$exit_code" != "0" ]; then
        echo -e "\n${RED}Script execution interrupted.${RESET}"
    fi

    # Remove any temporary files
    rm -f /tmp/duplication_*.tmp 2>/dev/null || true
}

# Set trap for proper cleanup on exit
trap cleanup EXIT INT TERM

# Run main function with all arguments
main "$@"

# Force terminal refresh to clear any leftover spinners
echo -en "\r\033[K\033[?25h"
echo ""
