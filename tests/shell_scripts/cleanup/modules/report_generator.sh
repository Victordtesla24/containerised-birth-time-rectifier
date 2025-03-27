#!/bin/bash
#
# Report generation module for code duplication detection
#

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# Get a value from JSON safely
safe_get_json_value() {
    local json="$1"
    local query="$2"
    local default="$3"

    local result
    result=$(echo "$json" | jq -r "$query" 2>/dev/null)

    if [[ $? -ne 0 || "$result" == "null" || -z "$result" ]]; then
        echo "$default"
    else
        echo "$result"
    fi
}

# Generate the header section
generate_header() {
    local result=$1
    local file_count
    file_count=$(safe_get_json_value "$result" '.file_count' '0')

    {
        echo "## Code Quality Analysis Report"
        echo "Generated on: $(date '+%Y-%m-%d %H:%M:%S')"
        echo
        echo "### Summary"
        echo "- Analyzed $file_count Python files"
        echo "- Similarity threshold: $SIMILARITY_THRESHOLD"
        echo "- Detection methods: ${DETECTION_METHODS[*]}"
        echo
    }
}

# Generate duplication section
generate_duplication_section() {
    local result=$1

    local similar_pairs
    similar_pairs=$(safe_get_json_value "$result" '.similar_pairs' '[]')
    local similar_count
    similar_count=$(echo "$similar_pairs" | jq -r 'length')

    {
        echo "### Duplication Analysis"
        echo

        if [ "$similar_count" -eq 0 ]; then
            echo "No significant code duplications detected."
            return
        fi

        echo "Found $similar_count similar file pairs:"
        echo

        # Group by similarity ranges
        local high_similarity=()
        local medium_similarity=()
        local low_similarity=()

        while read -r file1 file2 similarity; do
            similarity=$(echo "$similarity" | sed 's/^"//' | sed 's/"$//')
            file1=$(echo "$file1" | sed 's/^"//' | sed 's/"$//')
            file2=$(echo "$file2" | sed 's/^"//' | sed 's/"$//')

            local entry="- $file1 and $file2 (similarity: $similarity)"

            # Categorize by similarity level
            if (( $(echo "$similarity >= 0.8" | bc -l) )); then
                high_similarity+=("$entry")
            elif (( $(echo "$similarity >= 0.5" | bc -l) )); then
                medium_similarity+=("$entry")
            else
                low_similarity+=("$entry")
            fi
        done < <(echo "$similar_pairs" | jq -r '.[] | [.file1, .file2, .similarity] | @tsv')

        # Output categorized duplicates
        if [ ${#high_similarity[@]} -gt 0 ]; then
            echo "#### High Similarity (>=80%)"
            echo
            for entry in "${high_similarity[@]}"; do
                echo "$entry"
            done
            echo
        fi

        if [ ${#medium_similarity[@]} -gt 0 ]; then
            echo "#### Medium Similarity (50-79%)"
            echo
            for entry in "${medium_similarity[@]}"; do
                echo "$entry"
            done
            echo
        fi

        if [ ${#low_similarity[@]} -gt 0 ]; then
            echo "#### Lower Similarity (<50%)"
            echo
            for entry in "${low_similarity[@]}"; do
                echo "$entry"
            done
            echo
        fi
    }
}

# Generate issues section
generate_issues() {
    local result=$1

    # Safe extraction of files with issues
    local files_with_issues=$(safe_get_json_value "$result" '.files_with_issues' '[]')
    local issue_count=$(echo "$files_with_issues" | jq -r 'length')

    if [ "$issue_count" -eq 0 ]; then
        echo "No significant code issues detected."
        return
    fi

    echo -e "\n${BOLD}${RED}Code Quality Issues${RESET}"
    echo "The following files contain code quality issues that should be addressed:"

    # Mock/Simulated Code
    echo -e "\n${BOLD}Mock/Simulated Code${RESET}"
    echo "Mocks and simulations that should be replaced with real implementations:"
    if [ "$(echo "$files_with_issues" | jq -r '[.[] | select(.issues.mocks | length > 0)] | length')" -gt 0 ]; then
        local mock_count=0
        while read -r file; do
            if [ -n "$file" ]; then
                echo "- $file"
                local issues
                issues=$(echo "$files_with_issues" | jq -r --arg file "$file" '.[] | select(.path == $file) | .issues.mocks')
                if [ -n "$issues" ] && [ "$issues" != "null" ]; then
                    echo "$issues" | jq -r '.[]' | sed 's/^/    /'
                fi
                mock_count=$((mock_count + 1))
                # Limit to top 10 files for readability
                if [ $mock_count -ge 10 ]; then
                    echo "    ... and more files with mock code"
                    break
                fi
            fi
        done < <(echo "$files_with_issues" | jq -r '.[] | select(.issues.mocks | length > 0) | .path')
    else
        echo "    No mock code detected."
    fi

    # Fallback Mechanisms
    echo -e "\n${BOLD}Fallback Mechanisms${RESET}"
    echo "Potentially simulated fallback logic that should be implemented properly:"
    if [ "$(echo "$files_with_issues" | jq -r '[.[] | select(.issues.fallbacks | length > 0)] | length')" -gt 0 ]; then
        local fallback_count=0
        while read -r file; do
            if [ -n "$file" ]; then
                echo "- $file"
                local issues
                issues=$(echo "$files_with_issues" | jq -r --arg file "$file" '.[] | select(.path == $file) | .issues.fallbacks')
                if [ -n "$issues" ] && [ "$issues" != "null" ]; then
                    echo "$issues" | jq -r '.[]' | sed 's/^/    /'
                fi
                fallback_count=$((fallback_count + 1))
                # Limit to top 10 files for readability
                if [ $fallback_count -ge 10 ]; then
                    echo "    ... and more files with fallback mechanisms"
                    break
                fi
            fi
        done < <(echo "$files_with_issues" | jq -r '.[] | select(.issues.fallbacks | length > 0) | .path')
    else
        echo "    No simulated fallback mechanisms detected."
    fi

    # Hardcoded Values
    echo -e "\n${BOLD}Hardcoded Values${RESET}"
    echo "Hardcoded values that should be configurable:"
    if [ "$(echo "$files_with_issues" | jq -r '[.[] | select(.issues.hardcoded | length > 0)] | length')" -gt 0 ]; then
        local hardcoded_count=0
        while read -r file; do
            if [ -n "$file" ]; then
                echo "- $file"
                local issues
                issues=$(echo "$files_with_issues" | jq -r --arg file "$file" '.[] | select(.path == $file) | .issues.hardcoded')
                if [ -n "$issues" ] && [ "$issues" != "null" ]; then
                    echo "$issues" | jq -r '.[]' | sed 's/^/    /'
                fi
                hardcoded_count=$((hardcoded_count + 1))
                # Limit to top 10 files for readability
                if [ $hardcoded_count -ge 10 ]; then
                    echo "    ... and more files with hardcoded values"
                    break
                fi
            fi
        done < <(echo "$files_with_issues" | jq -r '.[] | select(.issues.hardcoded | length > 0) | .path')
    else
        echo "    No hardcoded values detected."
    fi

    # Warning Suppression
    echo -e "\n${BOLD}Warning Suppression${RESET}"
    echo "Warning suppressions that might be masking issues:"
    if [ "$(echo "$files_with_issues" | jq -r '[.[] | select(.issues.warning_suppression | length > 0)] | length')" -gt 0 ]; then
        local warning_count=0
        while read -r file; do
            if [ -n "$file" ]; then
                echo "- $file"
                local issues
                issues=$(echo "$files_with_issues" | jq -r --arg file "$file" '.[] | select(.path == $file) | .issues.warning_suppression')
                if [ -n "$issues" ] && [ "$issues" != "null" ]; then
                    echo "$issues" | jq -r '.[]' | sed 's/^/    /'
                fi
                warning_count=$((warning_count + 1))
                # Limit to top 10 files for readability
                if [ $warning_count -ge 10 ]; then
                    echo "    ... and more files with warning suppressions"
                    break
                fi
            fi
        done < <(echo "$files_with_issues" | jq -r '.[] | select(.issues.warning_suppression | length > 0) | .path')
    else
        echo "    No warning suppressions detected."
    fi

    # Error Masking
    echo -e "\n${BOLD}Error Masking${RESET}"
    echo "Error handling that might be silencing important errors:"
    if [ "$(echo "$files_with_issues" | jq -r '[.[] | select(.issues.error_masking | length > 0)] | length')" -gt 0 ]; then
        local error_count=0
        while read -r file; do
            if [ -n "$file" ]; then
                echo "- $file"
                local issues
                issues=$(echo "$files_with_issues" | jq -r --arg file "$file" '.[] | select(.path == $file) | .issues.error_masking')
                if [ -n "$issues" ] && [ "$issues" != "null" ]; then
                    echo "$issues" | jq -r '.[]' | sed 's/^/    /'
                fi
                error_count=$((error_count + 1))
                # Limit to top 10 files for readability
                if [ $error_count -ge 10 ]; then
                    echo "    ... and more files with error masking"
                    break
                fi
            fi
        done < <(echo "$files_with_issues" | jq -r '.[] | select(.issues.error_masking | length > 0) | .path')
    else
        echo "    No error masking detected."
    fi

    # Test Skipping
    echo -e "\n${BOLD}Test Skipping${RESET}"
    echo "Skipped tests that should be fixed:"
    if [ "$(echo "$files_with_issues" | jq -r '[.[] | select(.issues.test_skipping | length > 0)] | length')" -gt 0 ]; then
        local test_count=0
        while read -r file; do
            if [ -n "$file" ]; then
                echo "- $file"
                local issues
                issues=$(echo "$files_with_issues" | jq -r --arg file "$file" '.[] | select(.path == $file) | .issues.test_skipping')
                if [ -n "$issues" ] && [ "$issues" != "null" ]; then
                    echo "$issues" | jq -r '.[]' | sed 's/^/    /'
                fi
                test_count=$((test_count + 1))
                # Limit to top 10 files for readability
                if [ $test_count -ge 10 ]; then
                    echo "    ... and more files with skipped tests"
                    break
                fi
            fi
        done < <(echo "$files_with_issues" | jq -r '.[] | select(.issues.test_skipping | length > 0) | .path')
    else
        echo "    No skipped tests detected."
    fi
}

# Generate structure insights section
generate_structure_insights() {
    local result=$1

    # Extract structure analysis
    local structure=$(safe_get_json_value "$result" '.structure_analysis' '"No structure analysis available"')

    {
        echo "### Directory Structure Analysis"
        echo
        echo "$structure"
        echo
    }
}

# Generate recommendations section
generate_recommendations() {
    local result=$1

    local similar_count
    similar_count=$(safe_get_json_value "$result" '.similar_pairs | length' '0')

    local issues_count
    issues_count=$(safe_get_json_value "$result" '.files_with_issues | length' '0')

    {
        echo "### Recommendations"
        echo

        if [ "$similar_count" -gt 0 ] || [ "$issues_count" -gt 0 ]; then
            echo "Based on the analysis, consider the following actions:"
            echo

            if [ "$similar_count" -gt 0 ]; then
                echo "#### Addressing Code Duplication"
                echo
                echo "1. **Extract Common Functionality**: Identify duplicate code blocks and refactor them into reusable functions or classes."
                echo "2. **Create Shared Modules**: Move duplicate logic to shared utility modules that can be imported where needed."
                echo "3. **Review Similar Files**: Evaluate similar files for consolidation or restructuring to promote code reuse."

                # Additional specific recommendations based on the analysis
                local high_sim_files=$(safe_get_json_value "$result" '[.similar_pairs[] | select(.similarity >= 0.8)]' '[]')
                if [ "$(echo "$high_sim_files" | jq 'length')" -gt 0 ]; then
                    echo
                    echo "**High Priority Refactoring Targets**:"
                    echo
                    echo "The following files have high similarity and should be prioritized for refactoring:"
                    echo
                    echo "$high_sim_files" | jq -r '.[] | "- " + .file1 + " and " + .file2 + " (" + (.similarity | tostring | .[0:4]) + " similarity)"' | head -5
                fi
                echo
            fi

            if [ "$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.mocks | length > 0)] | length' '0')" -gt 0 ]; then
                echo "#### Addressing Mock/Simulated Code"
                echo
                echo "1. **Implement Real Functionality**: Replace mock implementations with actual code."
                echo "2. **Remove Dead Code**: Delete any stubbed functions that are no longer needed."
                echo "3. **Document Technical Debt**: If temporary implementations must remain, document them as technical debt with a timeline for replacement."
                echo "4. **Create Test Fixtures**: Replace ad-hoc mocks with proper test fixtures and dependency injection."
                echo
            fi

            if [ "$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.fallbacks | length > 0)] | length' '0')" -gt 0 ]; then
                echo "#### Addressing Fallback Mechanisms"
                echo
                echo "1. **Review Error Handling**: Ensure fallback logic properly handles edge cases."
                echo "2. **Test Failure Scenarios**: Add tests specifically for fallback paths to ensure they work correctly."
                echo "3. **Improve Logging**: Add detailed logging for when fallback mechanisms are triggered."
                echo "4. **Implement Circuit Breakers**: Consider using proper circuit breaker patterns for more robust fallback handling."
                echo
            fi

            if [ "$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.hardcoded | length > 0)] | length' '0')" -gt 0 ]; then
                echo "#### Addressing Hardcoded Values"
                echo
                echo "1. **Move to Configuration**: Move hardcoded values to configuration files or environment variables."
                echo "2. **Create Constants**: For values that must remain in code, define them as named constants in a single location."
                echo "3. **Remove Sensitive Data**: Ensure any hardcoded credentials are moved to secure storage."
                echo "4. **Use Configuration Service**: Consider implementing a centralized configuration service for complex applications."
                echo
            fi

            if [ "$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.error_masking | length > 0)] | length' '0')" -gt 0 ]; then
                echo "#### Addressing Error Masking"
                echo
                echo "1. **Add Specific Exception Handling**: Replace generic `except:` blocks with specific exception types."
                echo "2. **Improve Error Logging**: Ensure all caught exceptions are properly logged with context information."
                echo "3. **Propagate Important Errors**: Consider letting critical errors propagate rather than suppressing them."
                echo "4. **Add Monitoring**: Implement monitoring for error frequency to detect issues in production."
                echo
            fi

            echo "#### General Improvements"
            echo
            echo "1. **Improve Test Coverage**: Add tests for any code with quality issues to prevent regression."
            echo "2. **Regular Code Reviews**: Establish regular code quality reviews to prevent future issues."
            echo "3. **Automation**: Add automated code quality checks to your CI/CD pipeline."
            echo "4. **Refactoring Plan**: Create a systematic refactoring plan with the following phases:"
            echo "   - Phase 1: Address critical security issues (hardcoded credentials)"
            echo "   - Phase 2: Fix error masking issues that could cause silent failures"
            echo "   - Phase 3: Refactor high-similarity code (>0.8 similarity)"
            echo "   - Phase 4: Address testing issues and improve test coverage"
            echo
        else
            echo "No significant issues were detected. Continue maintaining good code quality standards."
            echo
        fi
    }
}

# Generate a summary report with severity scoring
generate_summary() {
    local result=$1

    local similar_count
    similar_count=$(safe_get_json_value "$result" '.similar_pairs | length' '0')

    local issues_count
    issues_count=$(safe_get_json_value "$result" '.files_with_issues | length' '0')

    # Count various issue types
    local mock_count
    mock_count=$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.mocks | length > 0)] | length' '0')

    local fallback_count
    fallback_count=$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.fallbacks | length > 0)] | length' '0')

    local hardcoded_count
    hardcoded_count=$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.hardcoded | length > 0)] | length' '0')

    local warning_count
    warning_count=$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.warning_suppression | length > 0)] | length' '0')

    local error_count
    error_count=$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.error_masking | length > 0)] | length' '0')

    local test_count
    test_count=$(safe_get_json_value "$result" '[.files_with_issues[] | select(.issues.test_skipping | length > 0)] | length' '0')

    # Get average similarity for duplicates to assess severity
    local avg_similarity="0.0"
    if [ "$similar_count" -gt 0 ]; then
        avg_similarity=$(safe_get_json_value "$result" '.similar_pairs | map(.similarity) | add / length' '0.0')
    fi

    {
        echo "### Executive Summary"
        echo
        echo "| Metric | Count | Severity |"
        echo "|--------|-------|----------|"
        echo "| Files Analyzed | $(safe_get_json_value "$result" '.file_count' '0') | - |"
        echo "| Similar File Pairs | $similar_count | $(get_severity_level "$similar_count" 5 10) |"
        echo "| Average Similarity | $avg_similarity | $(get_similarity_severity "$avg_similarity") |"
        echo "| Files with Quality Issues | $issues_count | $(get_severity_level "$issues_count" 5 15) |"
        echo "| Files with Mock Code | $mock_count | $(get_severity_level "$mock_count" 3 8) |"
        echo "| Files with Fallback Mechanisms | $fallback_count | $(get_severity_level "$fallback_count" 5 15) |"
        echo "| Files with Hardcoded Values | $hardcoded_count | $(get_severity_level "$hardcoded_count" 3 8) |"
        echo "| Files with Warning Suppression | $warning_count | $(get_severity_level "$warning_count" 5 10) |"
        echo "| Files with Error Masking | $error_count | $(get_severity_level "$error_count" 3 8) |"
        echo "| Files with Skipped Tests | $test_count | $(get_severity_level "$test_count" 3 8) |"
        echo

        # Calculate overall quality score with weighted metrics
        local file_count=$(safe_get_json_value "$result" '.file_count' '0')

        if [ "$file_count" -gt 0 ]; then
            # Weight each issue type by severity
            local weights="hardcoded:1.5,error_masking:1.3,mocks:1.0,test_skipping:0.8,fallbacks:0.7,warning_suppression:0.5"

            # Calculate weighted issue count
            local weighted_issues=$(echo "scale=2; $hardcoded_count * 1.5 + $error_count * 1.3 + $mock_count * 1.0 + $test_count * 0.8 + $fallback_count * 0.7 + $warning_count * 0.5" | bc)

            # Calculate duplicate code penalty
            local duplication_penalty=$(echo "scale=2; $similar_count * $avg_similarity" | bc)

            # Total weighted issues
            local total_weighted_issues=$(echo "scale=2; $weighted_issues + $duplication_penalty" | bc)

            # Calculate score (10 - penalty ratio)
            local issue_ratio=$(echo "scale=4; $total_weighted_issues / $file_count" | bc)
            local penalty=$(echo "scale=2; 10 * ($issue_ratio > 1 ? 1 : $issue_ratio)" | bc)
            local score=$(echo "scale=2; 10.0 - $penalty" | bc)

            # Enforce minimum score of 0.0
            if (( $(echo "$score < 0.0" | bc -l) )); then
                score="0.0"
            fi

            echo "**Code Quality Score:** $score/10.0"

            if (( $(echo "$score >= 9.0" | bc -l) )); then
                echo "**Status:** Excellent - Codebase is clean and well-maintained"
            elif (( $(echo "$score >= 7.5" | bc -l) )); then
                echo "**Status:** Good - Minor issues but generally healthy codebase"
            elif (( $(echo "$score >= 6.0" | bc -l) )); then
                echo "**Status:** Satisfactory - Several issues need addressing"
            elif (( $(echo "$score >= 4.0" | bc -l) )); then
                echo "**Status:** Fair - Significant issues require attention"
            elif (( $(echo "$score >= 2.0" | bc -l) )); then
                echo "**Status:** Poor - Immediate action required to address major issues"
            else
                echo "**Status:** Critical - Severe code quality problems throughout the codebase"
            fi
        else
            echo "**Quality Score:** N/A (No files analyzed)"
        fi
        echo

        # Add risk assessment summary
        echo "**Risk Assessment:**"
        echo
        if [ "$hardcoded_count" -gt 0 ]; then
            echo "- **Security Risk**: $(get_severity_level "$hardcoded_count" 3 8) - Hardcoded secrets or credentials detected"
        fi
        if [ "$error_count" -gt 0 ]; then
            echo "- **Reliability Risk**: $(get_severity_level "$error_count" 3 8) - Error masking may lead to silent failures"
        fi
        if [ "$similar_count" -gt 5 ]; then
            echo "- **Maintainability Risk**: $(get_severity_level "$similar_count" 5 15) - Significant code duplication increases maintenance burden"
        fi
        if [ "$test_count" -gt 0 ]; then
            echo "- **Testing Gap Risk**: $(get_severity_level "$test_count" 3 8) - Skipped tests may hide bugs"
        fi
        echo
    }
}

# Get severity level based on count
get_severity_level() {
    local count=$1
    local med_threshold=$2
    local high_threshold=$3

    if [ "$count" -eq 0 ]; then
        echo "Low"
    elif [ "$count" -lt "$med_threshold" ]; then
        echo "Low-Medium"
    elif [ "$count" -lt "$high_threshold" ]; then
        echo "Medium"
    elif [ "$count" -lt "$((high_threshold * 2))" ]; then
        echo "High"
    else
        echo "Critical"
    fi
}

# Get severity level based on similarity score
get_similarity_severity() {
    local similarity=$1

    if (( $(echo "$similarity < 0.3" | bc -l) )); then
        echo "Low"
    elif (( $(echo "$similarity < 0.5" | bc -l) )); then
        echo "Low-Medium"
    elif (( $(echo "$similarity < 0.7" | bc -l) )); then
        echo "Medium"
    elif (( $(echo "$similarity < 0.9" | bc -l) )); then
        echo "High"
    else
        echo "Critical"
    fi
}

# Generate hybrid detection section
generate_hybrid_section() {
    local result=$1

    local exact_duplicates
    exact_duplicates=$(safe_get_json_value "$result" '.exact_duplicates' '[]')
    local exact_count
    exact_count=$(echo "$exact_duplicates" | jq -r 'length')

    local structural_duplicates
    structural_duplicates=$(safe_get_json_value "$result" '.structural_duplicates' '[]')
    local structural_count
    structural_count=$(echo "$structural_duplicates" | jq -r 'length')

    local functional_duplicates
    functional_duplicates=$(safe_get_json_value "$result" '.functional_duplicates' '[]')
    local functional_count
    functional_count=$(echo "$functional_duplicates" | jq -r 'length')

    local common_patterns
    common_patterns=$(safe_get_json_value "$result" '.common_patterns' '[]')
    local pattern_count
    pattern_count=$(echo "$common_patterns" | jq -r 'length')

    {
        echo "### Advanced Hybrid Detection Analysis"
        echo

        if [ "$exact_count" -eq 0 ] && [ "$structural_count" -eq 0 ] && [ "$functional_count" -eq 0 ]; then
            echo "No significant code duplications detected with hybrid analysis."
            return
        fi

        # Exact duplicates (hash-based)
        if [ "$exact_count" -gt 0 ]; then
            echo "#### Exact Duplicates (File Hash Analysis)"
            echo "The following files are exact duplicates (100% identical):"
            echo
            while read -r file1 file2 similarity; do
                file1=$(echo "$file1" | sed 's/^"//' | sed 's/"$//')
                file2=$(echo "$file2" | sed 's/^"//' | sed 's/"$//')
                echo "- $file1 and $file2"
            done < <(echo "$exact_duplicates" | jq -r '.[] | [.file1, .file2, .similarity] | @tsv')
            echo
        else
            echo "No exact duplicate files were found."
            echo
        fi

        # Structural duplicates (AST-based)
        if [ "$structural_count" -gt 0 ]; then
            echo "#### Structural Duplicates (AST Pattern Analysis)"
            echo "The following files contain similar code structure based on Abstract Syntax Tree analysis:"
            echo
            while read -r file1 file2 similarity ast_similarity; do
                file1=$(echo "$file1" | sed 's/^"//' | sed 's/"$//')
                file2=$(echo "$file2" | sed 's/^"//' | sed 's/"$//')
                similarity=$(echo "$similarity" | sed 's/^"//' | sed 's/"$//')
                ast_similarity=$(echo "$ast_similarity" | sed 's/^"//' | sed 's/"$//')
                echo "- $file1 and $file2 (similarity: $similarity, AST similarity: $ast_similarity)"
            done < <(echo "$structural_duplicates" | jq -r '.[] | [.file1, .file2, .similarity, .ast_similarity] | @tsv')
            echo
        fi

        # Functional duplicates (control flow based)
        if [ "$functional_count" -gt 0 ]; then
            echo "#### Functional Duplicates (Control Flow Analysis)"
            echo "The following files have similar functionality based on control flow analysis:"
            echo
            while read -r file1 file2 similarity flow_similarity; do
                file1=$(echo "$file1" | sed 's/^"//' | sed 's/"$//')
                file2=$(echo "$file2" | sed 's/^"//' | sed 's/"$//')
                similarity=$(echo "$similarity" | sed 's/^"//' | sed 's/"$//')
                flow_similarity=$(echo "$flow_similarity" | sed 's/^"//' | sed 's/"$//')
                echo "- $file1 and $file2 (similarity: $similarity, flow similarity: $flow_similarity)"
            done < <(echo "$functional_duplicates" | jq -r '.[] | [.file1, .file2, .similarity, .flow_similarity] | @tsv')
            echo
        fi

        # Common code patterns (anti-unification results)
        if [ "$pattern_count" -gt 0 ]; then
            echo "#### Common Code Patterns (Anti-Unification Analysis)"
            echo "The following common patterns were identified across multiple files:"
            echo

            while read -r pattern func1 func2 similarity; do
                pattern=$(echo "$pattern" | sed 's/^"//' | sed 's/"$//')
                func1=$(echo "$func1" | sed 's/^"//' | sed 's/"$//')
                func2=$(echo "$func2" | sed 's/^"//' | sed 's/"$//')
                similarity=$(echo "$similarity" | sed 's/^"//' | sed 's/"$//')

                echo "- Pattern used in $func1 and $func2 (similarity: $similarity)"
                echo "  ```python"
                echo "  $pattern"
                echo "  ```"
                echo
            done < <(echo "$common_patterns" | jq -r '.[] | [.pattern, .function1, .function2, .similarity] | @tsv')
        fi
    }
}

# Generate a full report
generate_report() {
    local result_file="$1"
    local output_file="$2"

    # Read the result
    local result
    result=$(cat "$result_file")

    # Create the report
    {
        generate_header "$result"
        generate_summary "$result"
        generate_hybrid_section "$result"
        generate_duplication_section "$result"
        generate_issues "$result"
        generate_structure_insights "$result"
        generate_recommendations "$result"
    } > "$output_file"

    # Return success
    return 0
}

# Export functions
export -f generate_report
export -f safe_get_json_value
