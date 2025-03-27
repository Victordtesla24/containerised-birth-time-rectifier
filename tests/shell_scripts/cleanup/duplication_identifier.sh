#!/bin/bash
#
# Enhanced Code Duplication Identifier
# This script analyzes Python code for duplications, simulated fallbacks, and hardcoded values
# in ai_service and api_gateway directories
#

set -eo pipefail

# Get script directory and source modules
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="${SCRIPT_DIR}/modules"

# Source required modules
source "${MODULE_DIR}/config.sh"
source "${MODULE_DIR}/utils.sh"
source "${MODULE_DIR}/spinner.sh"
source "${MODULE_DIR}/python_analyzer.sh"
source "${MODULE_DIR}/report_generator.sh"
source "${MODULE_DIR}/file_comparison.sh"
source "${MODULE_DIR}/tree_analyzer.sh"
source "${MODULE_DIR}/ast_analyzer.sh"  # New AST analyzer module

# Print script header
print_header() {
    if [ "$HAS_COLOR" = true ]; then
        echo -e "\n${BOLD}${BLUE}=================================================================${RESET}"
        echo -e "${BOLD}${BLUE}       Code Duplication & Quality Issue Detector       ${RESET}"
        echo -e "${BOLD}${BLUE}=================================================================${RESET}\n"
    else
        echo -e "\n================================================================="
        echo -e "       Code Duplication & Quality Issue Detector       "
        echo -e "=================================================================\n"
    fi
}

# Print usage information
print_usage() {
    echo -e "${BOLD}Usage:${RESET} $0 [OPTIONS] [DIRECTORIES...]"
    echo ""
    echo -e "${BOLD}OPTIONS:${RESET}"
    echo "  -t, --threshold VALUE   Set similarity threshold (0.0-1.0) [default: 0.1]"
    echo "  -m, --methods LIST      Detection methods (comma-separated: token,ast,graph) [default: all]"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -h, --help              Display this help message"
    echo ""
    echo -e "${BOLD}EXAMPLES:${RESET}"
    echo "  $0 ./ai_service ./api_gateway"
    echo "  $0 -t 0.2 -m token,ast ./ai_service"
    echo "  $0 -v ./ai_service ./api_gateway"
    exit 0
}

# Generate structural analysis of directories
analyze_directory_structures() {
    local directories=("$@")
    local temp_dir=$(mktemp -d)
    local insights_file="${temp_dir}/insights.txt"

    # Ensure temp directory exists
    if [ ! -d "$temp_dir" ]; then
        mkdir -p "$temp_dir"
        if [ ! -d "$temp_dir" ]; then
            # If we can't create the temp dir, use a fixed path in /tmp
            temp_dir="/tmp/duplication_insights_$$"
            mkdir -p "$temp_dir"
            insights_file="${temp_dir}/insights.txt"
        fi
    fi

    start_spinner "Analyzing directory structure"

    # Create a basic structure insight file
    echo "# Directory Structure Analysis" > "$insights_file"
    echo "================================" >> "$insights_file"
    echo "" >> "$insights_file"

    # Process each directory with a timeout to prevent hanging
    for dir in "${directories[@]}"; do
        echo "## Directory: $dir" >> "$insights_file"
        echo "" >> "$insights_file"

        # Count Python files in directory with timeout
        local py_count=0
        py_count=$(run_with_timeout 10 "find \"$dir\" -type f -name \"*.py\" | wc -l" || echo "0")
        echo "* Contains $py_count Python files" >> "$insights_file"

        # List important subdirectories with timeout (limit depth to avoid long outputs)
        echo "* Major subdirectories:" >> "$insights_file"
        run_with_timeout 10 "find \"$dir\" -type d -not -path \"*/\.*\" -maxdepth 2 | head -20 | sort | sed 's|^|  - |'" >> "$insights_file" || echo "  - (Error listing subdirectories)" >> "$insights_file"

        echo "" >> "$insights_file"
    done

    # Try using the tree analyzer module with timeout
    if type analyze_directories_structure >/dev/null 2>&1; then
        if [ "$VERBOSE" = true ]; then
            log "INFO" "Attempting tree-based directory analysis..."
        fi

        local tree_result=""
        tree_result=$(run_with_timeout 30 "analyze_directories_structure ${directories[*]}" || echo "")

        # Check if the analysis was successful
        if [ -n "$tree_result" ] && [ -f "$tree_result" ]; then
            # Copy the file but keep our basic insights as a fallback
            local temp_insights=$(mktemp)
            cat "$insights_file" > "$temp_insights"
            cat "$tree_result" >> "$insights_file"

            # If the result is too short, use our basic insights instead
            if [ "$(wc -l < "$insights_file")" -lt 5 ]; then
                cat "$temp_insights" > "$insights_file"
                if [ "$VERBOSE" = true ]; then
                    log "WARN" "Tree-based analysis produced insufficient results, using basic analysis"
                fi
            fi
            rm -f "$temp_insights"
        else
            if [ "$VERBOSE" = true ]; then
                log "WARN" "Tree-based analysis failed, using basic analysis"
            fi
        fi
    fi

    stop_spinner true

    if [ ! -f "$insights_file" ]; then
        log "ERROR" "Failed to create directory insights file"
        # Create an empty file to avoid further errors
        echo "# Directory Structure Analysis (Error)" > "$insights_file"
    fi

    echo "$insights_file"
}

# Display a spinner while finding Python files
find_python_files() {
    local directories=("$@")
    local temp_file=$(mktemp)

    start_spinner "Finding Python files"

    for dir in "${directories[@]}"; do
        if [ "$VERBOSE" = true ]; then
            log "INFO" "Scanning directory: $dir"
        fi

        # Use find with a limited output to avoid buffer issues
        find "$dir" -type f -name "*.py" | while read -r file; do
            # Skip files larger than the maximum filesize
            local filesize=0
            filesize=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)

            if [ "$filesize" -gt "$MAX_FILESIZE" ]; then
                continue
            fi

            # Check if file is in a skipped directory
            local skip=false
            for pattern in "${SKIP_DIRECTORIES[@]}"; do
                if [[ "$file" == $pattern ]]; then
                    skip=true
                    break
                fi
            done

            if [ "$skip" = false ]; then
                # Use a simple echo to avoid encoding issues
                echo "$file" >> "$temp_file"
            fi
        done
    done

    stop_spinner true

    # Count files found
    local count=$(wc -l < "$temp_file" | tr -d ' ')
    if [ "$VERBOSE" = true ]; then
        log "INFO" "Found $count Python files"
    fi

    echo "$temp_file"
}

# Analyze files for duplications and issues
analyze_files() {
    local files_list="$1"
    local temp_dir=$(mktemp -d)
    local similar_file="${temp_dir}/similar_pairs.json"
    local issues_file="${temp_dir}/issues.json"
    local results_file="${temp_dir}/results.json"
    local ast_results_file="${temp_dir}/ast_results.json"

    # Initialize empty result files
    echo "[]" > "$similar_file"
    echo "[]" > "$issues_file"
    echo "[]" > "$ast_results_file"

    # Read files list
    local files=()
    while IFS= read -r file; do
        if [ -f "$file" ]; then  # Ensure the file exists
            files+=("$file")
        fi
    done < "$files_list"

    # Show message about what we're analyzing
    local file_count=${#files[@]}
    local comparison_count=1  # Default to 1 to avoid division by zero
    if [ "$file_count" -gt 1 ]; then
        comparison_count=$(( file_count * (file_count - 1) / 2 ))
    fi

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Analyzing $file_count files ($comparison_count potential comparisons)"
    fi

    # Initialize results container
    echo '{"status":"success","file_count":0,"similar_pairs":[],"files_with_issues":[]}' > "$results_file"

    # Step 1: First run tree-based structural analysis
    show_animated_banner "Analyzing Directory Structure"
    local structure_insights
    structure_insights=$(analyze_directory_structures "${DIRECTORIES[@]}")
    if [ "$VERBOSE" = true ]; then
        log "INFO" "Directory structure insights saved to: $structure_insights"
        cat "$structure_insights"
    fi

    # Step 2: Generate module mapping for context-aware analysis
    show_animated_banner "Generating Module Mapping"
    local module_mapping_file=$(generate_module_mapping "${DIRECTORIES[@]}")
    if [ "$VERBOSE" = true ]; then
        log "INFO" "Module mapping generated: $module_mapping_file"
    fi

    # Export module mapping to environment
    export MODULE_MAPPING="$module_mapping_file"

    # Step 3: Compare files for similarity using the enhanced analyzers
    show_animated_banner "Analyzing Code Similarity"

    # Check if we have files to compare
    if [ "$file_count" -le 1 ]; then
        log "WARN" "Not enough files to compare (need at least 2)"
    else
        # Progress bar for file comparisons
        start_fancy_progress "$comparison_count" "Comparing files for duplication" "gradient"

        # Run Advanced AST-based analysis for more accurate clone detection
        if [ "$file_count" -gt 0 ]; then
            if [ "$VERBOSE" = true ]; then
                log "INFO" "Running advanced AST-based analysis"
            fi

            # Only analyze a subset of files if there are too many
            local ast_files=("${files[@]}")
            if [ "$file_count" -gt 100 ]; then
                log "INFO" "Too many files, analyzing a subset of 100 for AST analysis"
                ast_files=("${files[@]:0:100}")
            fi

            # Run AST analysis
            run_ast_analysis "$SIMILARITY_THRESHOLD" "${ast_files[@]}" > "$ast_results_file"

            # Check if AST analysis produced results
            if [ -s "$ast_results_file" ] && [ "$(jq '.similar_pairs | length' "$ast_results_file")" -gt 0 ]; then
                if [ "$VERBOSE" = true ]; then
                    log "INFO" "AST analysis found $(jq '.similar_pairs | length' "$ast_results_file") similar file pairs"
                fi
                jq -r '.similar_pairs' "$ast_results_file" > "$similar_file"
            else
                if [ "$VERBOSE" = true ]; then
                    log "INFO" "AST analysis found no similar pairs, falling back to standard methods"
                fi
            fi
        fi

        # Run Python-based analysis which now uses module mapping
        local python_result_file=$(mktemp)
        run_python_analysis > "$python_result_file"

        # Extract similar pairs from Python analysis and combine with AST results
        if [ -s "$python_result_file" ]; then
            # If we already have results from AST analysis
            if [ -s "$similar_file" ] && [ "$(jq 'length' "$similar_file")" -gt 0 ]; then
                # Combine with Python results
                jq -s '.[0] + .[1]' "$similar_file" <(jq '.similar_pairs' "$python_result_file") > "${temp_dir}/combined.json"
                mv "${temp_dir}/combined.json" "$similar_file"
            else
                # Just use Python results
                jq -r '.similar_pairs' "$python_result_file" > "$similar_file"
            fi

            # Extract files with issues
            jq -r '.files_with_issues' "$python_result_file" > "$issues_file"

            # Update progress
            update_fancy_progress "$comparison_count" "File comparison complete" "gradient"
        else
            log "ERROR" "Python analysis failed, using fallback methods"
            # Fallback to basic comparison methods if Python analysis fails
            for method in "${DETECTION_METHODS[@]}"; do
                log "INFO" "Using detection method: $method"

                # Batch compare files
                local method_similar_file="${temp_dir}/similar_${method}.json"
                echo "[]" > "$method_similar_file"  # Initialize with empty JSON array

                # Process comparisons in batches to show progress
                local progress=0
                for ((i=0; i<${#files[@]}; i++)); do
                    for ((j=i+1; j<${#files[@]}; j++)); do
                        local file1="${files[$i]}"
                        local file2="${files[$j]}"

                        # Skip if either file doesn't exist
                        if [ ! -f "$file1" ] || [ ! -f "$file2" ]; then
                            continue
                        fi

                        # Compare files and check similarity
                        local similarity=$(compare_files "$file1" "$file2" "$method" "$SIMILARITY_THRESHOLD")

                        # If similarity is above threshold, add to results
                        if (( $(echo "$similarity >= $SIMILARITY_THRESHOLD" | bc -l) )); then
                            # Create a temporary file for the new result
                            local temp_file=$(mktemp)

                            # Add new result
                            local new_result=$(jq -n \
                                --arg file1 "$file1" \
                                --arg file2 "$file2" \
                                --arg similarity "$similarity" \
                                '[{"file1": $file1, "file2": $file2, "similarity": ($similarity | tonumber)}]')

                            # Combine with existing results (if any)
                            if [ "$(jq 'length' "$method_similar_file")" -eq 0 ]; then
                                echo "$new_result" > "$temp_file"
                            else
                                jq -s '.[0] + .[1]' "$method_similar_file" <(echo "$new_result") > "$temp_file"
                            fi

                            # Replace the output file
                            mv "$temp_file" "$method_similar_file"
                        fi

                        # Update progress
                        progress=$((progress + 1))
                        if [ "$((progress % 10))" -eq 0 ]; then
                            update_fancy_progress "$progress" "Comparing files using $method method ($progress/$comparison_count)" "gradient"
                        fi
                    done
                done

                # Combine results if any were found
                if [ -s "$method_similar_file" ] && [ "$(jq 'length' "$method_similar_file")" -gt 0 ]; then
                    if [ "$(jq 'length' "$similar_file")" -eq 0 ]; then
                        cp "$method_similar_file" "$similar_file"
                    else
                        jq -s '.[0] + .[1]' "$similar_file" "$method_similar_file" > "${temp_dir}/combined.json"
                        mv "${temp_dir}/combined.json" "$similar_file"
                    fi
                fi
            done
        fi

        # Complete progress bar
        update_fancy_progress "$comparison_count" "File comparison complete"
        stop_progress true
    fi

    # Step 3: If we didn't already extract code quality issues in the Python analysis
    if [ ! -s "$issues_file" ] || [ "$(jq 'length' "$issues_file")" -eq 0 ]; then
        show_animated_banner "Analyzing Code Quality Issues"

        # Check if we have files to analyze
        if [ "$file_count" -eq 0 ]; then
            log "WARN" "No files to analyze for code quality issues"
        else
            # Progress bar for issue detection
            start_fancy_progress "${#files[@]}" "Scanning for code quality issues" "animated"

            # Process each file
            for i in "${!files[@]}"; do
                local file="${files[$i]}"
                local basename=$(basename "$file")
                local temp_issues="${temp_dir}/issues_${i}.json"

                # Skip if file doesn't exist
                if [ ! -f "$file" ]; then
                    continue
                fi

                # Update progress
                update_fancy_progress "$i" "Scanning ${basename}" "animated"

                # Detect patterns in file
                detect_patterns_in_file "$file" "$temp_issues" >/dev/null

                # If issues were found, add to the list
                if [ -s "$temp_issues" ] && [ "$(jq '.issues | length' "$temp_issues")" -gt 0 ]; then
                    if [ "$(jq 'length' "$issues_file")" -eq 0 ]; then
                        echo "[$(cat "$temp_issues")]" > "$issues_file"
                    else
                        jq -s '.[0] + [.[1]]' "$issues_file" "$temp_issues" > "${temp_dir}/combined_issues.json"
                        mv "${temp_dir}/combined_issues.json" "$issues_file"
                    fi
                fi
            done

            # Complete progress bar
            update_fancy_progress "${#files[@]}" "Code quality scan complete"
            stop_progress true
        fi
    fi

    # Step 4: Final result compilation
    start_fancy_spinner "Compiling analysis results" "bounce"

    # Combine directory structure insights with the analysis results
    if [ -f "$structure_insights" ]; then
        local structure_content=$(cat "$structure_insights")

        # Create a formatted version to include in the results
        local formatted_structure=$(echo "$structure_content" | jq -sR .)
    else
        local formatted_structure='"No directory structure analysis available"'
    fi

    # Get function-level similarities from AST analysis if available
    local function_similarities="[]"
    if [ -s "$ast_results_file" ]; then
        function_similarities=$(jq -r '[.similar_pairs[] | .similar_functions[]] | unique_by({function1, function2})' "$ast_results_file")
        if [ "$function_similarities" = "null" ]; then
            function_similarities="[]"
        fi
    fi

    # Combine all results
    jq --arg count "${#files[@]}" \
       --slurpfile similar "$similar_file" \
       --slurpfile issues "$issues_file" \
       --arg structure "$formatted_structure" \
       --argjson func_similarities "$function_similarities" \
        '{
            "status": "success",
            "file_count": ($count | tonumber),
            "similar_pairs": ($similar[0] // []),
            "files_with_issues": ($issues[0] // []),
            "function_similarities": $func_similarities,
            "structure_analysis": ($structure | fromjson)
        }' > "$results_file"

    stop_spinner true

    # Clean up temporary files
    rm -f "$module_mapping_file" 2>/dev/null || true

    echo "$results_file"
}

# Main function
main() {
    # Print header
    print_header

    # Parse command line arguments
    if ! parse_args "$@"; then
        log "ERROR" "Failed to parse arguments"
        exit 1
    fi

    # If help flag was provided, show usage and exit
    if [ "$SHOW_HELP" = true ]; then
        print_usage
    fi

    # Show configuration summary
    show_enhanced_status "Configuration" \
        "Similarity threshold: ${SIMILARITY_THRESHOLD}" \
        "Detection methods: ${DETECTION_METHODS[*]}" \
        "Directories: ${DIRECTORIES[*]}" \
        "Verbose mode: ${VERBOSE}"

    # Create reports directory if it doesn't exist
    mkdir -p "$(dirname "$REPORT_FILE")"

    # Setup Python environment
    start_fancy_spinner "Setting up Python environment" "pulse"
    if ! setup_python_env; then
        stop_spinner false
        log "ERROR" "Failed to setup Python environment"
        exit 1
    fi
    stop_spinner true

    # Find all Python files
    local files_list
    files_list=$(find_python_files "${DIRECTORIES[@]}")

    # Start analysis
    show_animated_banner "Starting Enhanced Code Analysis"
    local result_file
    result_file=$(analyze_files "$files_list")

    # Parse result stats
    local file_count=$(jq '.file_count' "$result_file")
    local similar_count=$(jq '.similar_pairs | length' "$result_file")
    local issues_count=$(jq '.files_with_issues | length' "$result_file")

    # Show quick summary
    show_enhanced_status "Analysis Summary" \
        "Files analyzed: ${file_count}" \
        "Similar file pairs: ${similar_count}" \
        "Files with code quality issues: ${issues_count}"

    # Generate report
    start_fancy_spinner "Generating detailed analysis report" "flow"
    if ! generate_report "$result_file" "$REPORT_FILE"; then
        stop_spinner false
        log "ERROR" "Failed to generate report"
        cleanup "$files_list" "$result_file"
        exit 1
    fi
    stop_spinner true

    # Show final message
    if [ "${similar_count}" -gt 0 ] || [ "${issues_count}" -gt 0 ]; then
        if [ "$HAS_COLOR" = true ]; then
            echo -e "\n${BOLD}${YELLOW}Code quality issues detected!${RESET}"
        else
            echo -e "\n[WARNING] Code quality issues detected!"
        fi
        echo -e "Detailed report saved to: ${REPORT_FILE}"

        # Show report summary based on severity
        if [ "${similar_count}" -gt 5 ] || [ "${issues_count}" -gt 10 ]; then
            if [ "$HAS_COLOR" = true ]; then
                echo -e "${BOLD}${RED}HIGH SEVERITY:${RESET} Significant code duplication and quality issues found"
            else
                echo -e "HIGH SEVERITY: Significant code duplication and quality issues found"
            fi
        elif [ "${similar_count}" -gt 0 ] || [ "${issues_count}" -gt 0 ]; then
            if [ "$HAS_COLOR" = true ]; then
                echo -e "${BOLD}${YELLOW}MEDIUM SEVERITY:${RESET} Some code quality issues need attention"
            else
                echo -e "MEDIUM SEVERITY: Some code quality issues need attention"
            fi
        fi
    else
        if [ "$HAS_COLOR" = true ]; then
            echo -e "\n${BOLD}${GREEN}No significant code quality issues detected!${RESET}"
        else
            echo -e "\nNo significant code quality issues detected!"
        fi
        echo -e "Report saved to: ${REPORT_FILE}"
    fi

    # Display the report if verbose mode is enabled
    if [ "$VERBOSE" = true ]; then
        show_animated_banner "Analysis Report"
        cat "$REPORT_FILE"
    fi

    # Clean up temporary files
    cleanup "$files_list" "$result_file"

    echo -e "\n${BOLD}Analysis completed successfully!${RESET}"

    # Return appropriate exit code
    if [ "${similar_count}" -gt 0 ] || [ "${issues_count}" -gt 0 ]; then
        return 2  # Non-zero exit code indicates issues found
    else
        return 0  # Zero exit code indicates no issues
    fi
}

# Run main function with all arguments
main "$@"
