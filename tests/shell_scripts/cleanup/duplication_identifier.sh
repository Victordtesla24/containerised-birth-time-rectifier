#!/bin/bash
#
# Code Duplication Identifier Script
# Purpose: Identifies duplicate or similar code across Python files
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

set -eo pipefail

# Script configuration
SIMILARITY_THRESHOLD=${SIMILARITY_THRESHOLD:-0.7}
REPORT_FILE="./reports/duplication_report.txt"
VERBOSE=${VERBOSE:-false}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Terminal colors
RESET="\033[0m"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RED="\033[31m"

# Print usage
function print_usage() {
    echo -e "${BOLD}Code Duplication Identifier${RESET}"
    echo "Usage: $0 [OPTIONS] [DIRECTORIES...]"
    echo
    echo "OPTIONS:"
    echo "  -t, --threshold FLOAT   Similarity threshold (0.0-1.0) [default: 0.7]"
    echo "  -o, --output FILE       Output report file [default: ./reports/duplication_report.txt]"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -h, --help              Show this help message"
    echo
    echo "EXAMPLES:"
    echo "  $0 ai_service api_gateway             # Check between two directories"
    echo "  $0 -t 0.8 ai_service                  # Higher threshold (fewer matches)"
    echo "  $0 -v -o custom_report.txt ai_service # Custom report with verbose output"
}

# Parse command line arguments
parse_args() {
    DIRECTORIES=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -t|--threshold)
                SIMILARITY_THRESHOLD="$2"
                shift 2
                ;;
            -o|--output)
                REPORT_FILE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                DIRECTORIES+=("$1")
                shift
                ;;
        esac
    done

    # If no directories specified, use current directory
    if [ ${#DIRECTORIES[@]} -eq 0 ]; then
        DIRECTORIES=("$PROJECT_ROOT")
    fi
}

# Create Python script for token-based similarity detection
create_python_script() {
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import os
import sys
import tokenize
from io import BytesIO
from difflib import SequenceMatcher
import json
from collections import defaultdict

# Configuration
SIMILARITY_THRESHOLD = float(sys.argv[1])
DIRECTORIES = sys.argv[2:]
EXTENSIONS = ('.py',)  # Only analyze Python files for now
IGNORE_TOKENS = set(['COMMENT', 'NL', 'NEWLINE', 'INDENT', 'DEDENT'])

# Result storage
similar_files = []
file_tokens = {}
file_metadata = {}

def tokenize_file(file_path):
    """Tokenize a file and return significant tokens."""
    tokens = []

    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        # Skip empty files
        if not content.strip():
            return []

        # Tokenize the content
        token_gen = tokenize.tokenize(BytesIO(content).readline)
        for tok in token_gen:
            if tok.type == tokenize.COMMENT:
                continue
            if tokenize.tok_name[tok.type] in IGNORE_TOKENS:
                continue
            if tok.string.strip() == '':
                continue

            # Add the token string and its type
            tokens.append((tokenize.tok_name[tok.type], tok.string))

        # Get file metadata for reporting
        lines = len(content.splitlines())
        size = len(content)
        file_metadata[file_path] = {
            'lines': lines,
            'size': size,
            'token_count': len(tokens)
        }

    except Exception as e:
        sys.stderr.write(f"Error tokenizing {file_path}: {str(e)}\n")
        return []

    return tokens

def calculate_similarity(tokens1, tokens2):
    """Calculate similarity ratio between two token lists."""
    # Early return for empty token lists
    if not tokens1 or not tokens2:
        return 0.0

    # Convert token tuples to strings for more accurate comparison
    str_tokens1 = [f"{t[0]}:{t[1]}" for t in tokens1]
    str_tokens2 = [f"{t[0]}:{t[1]}" for t in tokens2]

    # Use SequenceMatcher for similarity comparison
    s = SequenceMatcher(None, str_tokens1, str_tokens2)
    return s.ratio()

def find_similar_files():
    """Find similar files across specified directories."""
    # Collect all Python files
    all_files = []
    for directory in DIRECTORIES:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(EXTENSIONS):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)

    # Tokenize all files
    sys.stderr.write(f"Tokenizing {len(all_files)} files...\n")
    for i, file_path in enumerate(all_files):
        if i % 50 == 0:
            sys.stderr.write(f"Progress: {i}/{len(all_files)} files\n")
        file_tokens[file_path] = tokenize_file(file_path)

    # Compare file pairs for similarity
    sys.stderr.write("Comparing file pairs for similarity...\n")
    compared = 0
    total_comparisons = (len(all_files) * (len(all_files) - 1)) // 2

    # Group files by directory for better reporting
    dir_similarities = defaultdict(list)

    for i, file1 in enumerate(all_files):
        # Show progress periodically
        if i % 10 == 0:
            sys.stderr.write(f"Progress: {compared}/{total_comparisons} comparisons\n")

        for j, file2 in enumerate(all_files):
            # Skip self-comparison and already compared pairs
            if i >= j:
                continue

            compared += 1

            # Calculate similarity
            similarity = calculate_similarity(file_tokens[file1], file_tokens[file2])

            # If similarity exceeds threshold, record the pair
            if similarity >= SIMILARITY_THRESHOLD:
                # Get relative directories for better grouping
                dir1 = os.path.dirname(file1)
                dir2 = os.path.dirname(file2)

                # Generate a key for the directory pair (sorted for consistency)
                dir_pair = tuple(sorted([dir1, dir2]))

                result = {
                    'file1': file1,
                    'file2': file2,
                    'similarity': similarity,
                    'metadata1': file_metadata[file1],
                    'metadata2': file_metadata[file2]
                }

                dir_similarities[dir_pair].append(result)
                similar_files.append(result)

    # Return results
    return {
        'similar_files': similar_files,
        'by_directory': dict(dir_similarities),
        'file_count': len(all_files),
        'comparison_count': compared
    }

# Main execution
if __name__ == "__main__":
    results = find_similar_files()
    print(json.dumps(results, indent=2))
EOF

    echo "$temp_script"
}

# Run Python script and process results
run_analysis() {
    local python_script=$(create_python_script)

    # Create reports directory if it doesn't exist
    mkdir -p "$(dirname "$REPORT_FILE")"

    # Begin analysis
    echo -e "${BLUE}${BOLD}=== Starting Code Duplication Analysis ===${RESET}"
    echo -e "Directories: ${BOLD}${DIRECTORIES[*]}${RESET}"
    echo -e "Similarity threshold: ${BOLD}${SIMILARITY_THRESHOLD}${RESET}"
    echo -e "Report file: ${BOLD}${REPORT_FILE}${RESET}"
    echo

    # Run Python script
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Running analysis - this may take a while...${RESET}"
    fi

    results=$(python3 "$python_script" "$SIMILARITY_THRESHOLD" "${DIRECTORIES[@]}" 2>&1)
    raw_results=$(echo "$results" | grep -v "Progress:" | grep -v "Tokenizing" | grep -v "Comparing")

    # Extract JSON results from output (last line only)
    json_results=$(echo "$raw_results" | tail -n 1)

    # Parse simple statistics
    file_count=$(echo "$json_results" | grep -o '"file_count": [0-9]*' | cut -d' ' -f2)
    comparison_count=$(echo "$json_results" | grep -o '"comparison_count": [0-9]*' | cut -d' ' -f2)
    similar_count=$(echo "$json_results" | grep -o '"similar_files": \[' -A 1000 | grep -c '"file1":')

    # Generate report
    {
        echo "=========================================================="
        echo "     CODE DUPLICATION ANALYSIS REPORT"
        echo "=========================================================="
        echo
        echo "Generated on: $(date)"
        echo "Directories analyzed: ${DIRECTORIES[*]}"
        echo "Similarity threshold: ${SIMILARITY_THRESHOLD}"
        echo
        echo "SUMMARY:"
        echo "---------"
        echo "Files analyzed: $file_count"
        echo "Comparisons performed: $comparison_count"
        echo "Similar file pairs found: $similar_count"
        echo
        echo "DETAILED RESULTS:"
        echo "----------------"

        if [ "$similar_count" -eq 0 ]; then
            echo "No significant code duplication found."
        else
            # Parse and format similar file groups
            echo "$json_results" | python3 -c '
import json
import sys
from collections import defaultdict

# Parse the JSON input
data = json.loads(sys.stdin.read())

# Group by similarity level
high_similarity = []
medium_similarity = []
low_similarity = []

for pair in data["similar_files"]:
    if pair["similarity"] >= 0.9:
        high_similarity.append(pair)
    elif pair["similarity"] >= 0.8:
        medium_similarity.append(pair)
    else:
        low_similarity.append(pair)

# Print high similarity pairs (potential exact duplicates)
if high_similarity:
    print("\n## HIGH SIMILARITY (90%+) - Potential exact duplicates")
    print("These files are nearly identical and should be consolidated immediately:")
    for pair in high_similarity:
        print(f"\n* {pair['similarity']:.1%} similar:")
        print(f"  - {pair['file1']} ({pair['metadata1']['lines']} lines)")
        print(f"  - {pair['file2']} ({pair['metadata2']['lines']} lines)")

# Print medium similarity pairs (significant duplication)
if medium_similarity:
    print("\n## MEDIUM SIMILARITY (80-89%) - Significant duplication")
    print("These files have significant shared code and should be refactored:")
    for pair in medium_similarity:
        print(f"\n* {pair['similarity']:.1%} similar:")
        print(f"  - {pair['file1']} ({pair['metadata1']['lines']} lines)")
        print(f"  - {pair['file2']} ({pair['metadata2']['lines']} lines)")

# Print low similarity pairs (potential duplication)
if low_similarity:
    print("\n## MODERATE SIMILARITY (70-79%) - Potential duplication")
    print("These files may share some code that could be extracted into common utilities:")
    for pair in low_similarity:
        print(f"\n* {pair['similarity']:.1%} similar:")
        print(f"  - {pair['file1']} ({pair['metadata1']['lines']} lines)")
        print(f"  - {pair['file2']} ({pair['metadata2']['lines']} lines)")

# Print by directory relationships
print("\n## DIRECTORY RELATIONSHIPS")
print("Files with similarity between directories:")

dir_pairs = data["by_directory"]
for dir_pair, pairs in dir_pairs.items():
    dir1, dir2 = dir_pair
    if dir1 == dir2:
        print(f"\n### Within {dir1}")
    else:
        print(f"\n### Between {dir1} and {dir2}")

    # Count duplicates per directory pair
    avg_similarity = sum(p["similarity"] for p in pairs) / len(pairs)
    print(f"Found {len(pairs)} similar file pairs (avg. {avg_similarity:.1%} similarity)")
'
        fi

        echo
        echo "RECOMMENDATIONS:"
        echo "--------------"
        echo "1. Review high similarity files first and consolidate or extract shared code."
        echo "2. For directory pairs with high duplication, consider creating shared utilities."
        echo "3. Run this analysis regularly to prevent code duplication from increasing."
        echo
        echo "=========================================================="

    } > "$REPORT_FILE"

    # Print summary to console
    echo -e "${GREEN}${BOLD}Analysis complete!${RESET}"
    echo -e "Files analyzed: ${BOLD}$file_count${RESET}"
    echo -e "Similar file pairs found: ${BOLD}$similar_count${RESET}"

    if [ "$similar_count" -gt 0 ]; then
        echo -e "${YELLOW}${BOLD}Code duplication detected!${RESET} Check the report for details."
    else
        echo -e "${GREEN}${BOLD}No significant code duplication found.${RESET}"
    fi

    echo -e "Report saved to: ${BOLD}$REPORT_FILE${RESET}"

    # Clean up temporary Python script
    rm -f "$python_script"
}

# Main execution
parse_args "$@"
run_analysis
