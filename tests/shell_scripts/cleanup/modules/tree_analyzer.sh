#!/bin/bash
#
# Tree-based directory structure analyzer
#

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# Generate a tree representation of directories
generate_directory_tree() {
    local root_dir="$1"
    local output_file="$2"
    local max_depth="${3:-5}"
    local exclude_pattern="${4:-node_modules|\.git|\.cache|__pycache__|\.venv|venv}"

    # Check if tree command is available
    if ! command -v tree >/dev/null 2>&1; then
        log "WARN" "Tree command not found. Falling back to find-based implementation."
        generate_tree_with_find "$root_dir" "$output_file" "$max_depth" "$exclude_pattern"
        return
    fi

    # Use tree command with JSON output
    if [ "$VERBOSE" = true ]; then
        log "INFO" "Generating directory tree for $root_dir (max depth: $max_depth)"
    fi

    # Generate the tree in JSON format
    tree -J -L "$max_depth" --noreport -P "*.py" --prune -I "$exclude_pattern" "$root_dir" > "$output_file" 2>/dev/null || {
        log "WARN" "Error using tree command, falling back to find-based implementation"
        generate_tree_with_find "$root_dir" "$output_file" "$max_depth" "$exclude_pattern"
        return
    }

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Directory tree generated: $(wc -l < "$output_file") lines"
    fi
}

# Generate tree structure using find (fallback if tree command is not available)
generate_tree_with_find() {
    local root_dir="$1"
    local output_file="$2"
    local max_depth="${3:-5}"
    local exclude_pattern="${4:-node_modules|\.git|\.cache|__pycache__|\.venv|venv}"

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Generating directory tree with find for $root_dir"
    fi

    # Initialize JSON structure
    echo '[{"type":"directory","name":"'"$(basename "$root_dir")"'","contents":[' > "$output_file"

    # Use find to list all Python files
    find "$root_dir" -type f -name "*.py" -not -path "*/$exclude_pattern/*" -maxdepth "$max_depth" | sort | while read -r file; do
        # Get relative path
        local rel_path="${file#$root_dir/}"

        # Add to JSON
        echo '{"type":"file","name":"'"$rel_path"'"},' >> "$output_file"
    done

    # Close JSON structure - use platform-independent approach to remove trailing comma
    local temp_file=$(mktemp)
    cat "$output_file" | sed '$s/,$//' > "$temp_file"
    mv "$temp_file" "$output_file"
    echo ']}]' >> "$output_file"

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Directory tree generated with find: $(wc -l < "$output_file") lines"
    fi
}

# Analyze the directory structure for potential duplications
analyze_directory_structure() {
    local tree_file="$1"
    local output_file="$2"

    # Create a Python script for analysis
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import json
import sys
import os
from collections import defaultdict

# Read the tree file
with open(sys.argv[1], 'r') as f:
    tree_data = json.load(f)

# Function to recursively extract all Python files
def extract_python_files(node, path=""):
    files = []
    if node['type'] == 'file' and node['name'].endswith('.py'):
        files.append(os.path.join(path, node['name']))
    elif node['type'] == 'directory':
        current_path = os.path.join(path, node['name'])
        if 'contents' in node:
            for item in node['contents']:
                files.extend(extract_python_files(item, current_path))
    return files

# Extract all Python files
all_files = []
for root in tree_data:
    all_files.extend(extract_python_files(root))

# Group by filename
filename_groups = defaultdict(list)
for file_path in all_files:
    filename = os.path.basename(file_path)
    filename_groups[filename].append(file_path)

# Filter to get only duplicate filenames
duplicates = {filename: paths for filename, paths in filename_groups.items() if len(paths) > 1}

# Group by directory patterns
directory_patterns = defaultdict(list)

# Common patterns to look for
patterns = [
    'services', 'api', 'controllers', 'models', 'views',
    'utils', 'helpers', 'routes', 'middleware', 'core'
]

for file_path in all_files:
    for pattern in patterns:
        if f'/{pattern}/' in file_path or file_path.startswith(f'{pattern}/'):
            directory_patterns[pattern].append(file_path)

# Identify service-like files that may have duplicates
service_files = []
for file_path in all_files:
    if 'service' in file_path.lower() or 'manager' in file_path.lower() or 'handler' in file_path.lower():
        service_files.append(file_path)

# Identify parallel modules in different directories
parallel_modules = defaultdict(list)
for file_path in all_files:
    parts = file_path.split('/')
    if len(parts) >= 2:
        module_path = '/'.join(parts[:-1])
        parallel_modules[parts[-1]].append(module_path)

# Filter to find modules with the same name in different paths
parallel_duplicates = {
    filename: paths
    for filename, paths in parallel_modules.items()
    if len(set(paths)) > 1 and filename.endswith('.py')
}

# Output results
result = {
    'duplicate_filenames': duplicates,
    'directory_patterns': {k: v for k, v in directory_patterns.items() if v},
    'service_files': service_files,
    'parallel_modules': parallel_duplicates,
    'file_count': len(all_files)
}

with open(sys.argv[2], 'w') as f:
    json.dump(result, f, indent=2)
EOF

    # Run the analysis
    python3 "$temp_script" "$tree_file" "$output_file"

    # Clean up
    rm -f "$temp_script"

    # Check for successful generation
    if [ -s "$output_file" ]; then
        if [ "$VERBOSE" = true ]; then
            log "INFO" "Directory structure analysis completed"
        fi
        return 0
    else
        log "ERROR" "Failed to analyze directory structure"
        return 1
    fi
}

# Generate structure insights for potential duplications
generate_structure_insights() {
    local analysis_file="$1"
    local output_file="$2"

    # Extract insights with jq
    local file_count=$(jq -r '.file_count' "$analysis_file")
    local duplicate_count=$(jq -r '.duplicate_filenames | length' "$analysis_file")
    local service_count=$(jq -r '.service_files | length' "$analysis_file")
    local parallel_count=$(jq -r '.parallel_modules | length' "$analysis_file")

    # Generate readable insights
    {
        echo "Directory Structure Insights"
        echo "============================"
        echo
        echo "Files scanned: $file_count"
        echo "Files with duplicate names: $duplicate_count"
        echo "Service-like files: $service_count"
        echo "Parallel modules: $parallel_count"
        echo

        echo "Duplicate Filename Analysis"
        echo "---------------------------"
        jq -r '.duplicate_filenames | to_entries[] | "* " + .key + " (" + (.value | length | tostring) + " instances):\n" + (.value | map("  - " + .) | join("\n"))' "$analysis_file"
        echo

        echo "Service Files"
        echo "------------"
        jq -r '.service_files | .[] | "* " + .' "$analysis_file"
        echo

        echo "Parallel Modules"
        echo "---------------"
        jq -r '.parallel_modules | to_entries[] | "* " + .key + " in " + (.value | length | tostring) + " locations:\n" + (.value | map("  - " + .) | join("\n"))' "$analysis_file"
        echo

        echo "Directory Pattern Analysis"
        echo "---------------------------"
        jq -r '.directory_patterns | to_entries[] | "* " + .key + " (" + (.value | length | tostring) + " files)"' "$analysis_file"

    } > "$output_file"

    return 0
}

# Main function to analyze directory structure
analyze_tree() {
    local root_dir="$1"
    local output_dir="$2"

    # Create temporary directory if output_dir not provided
    if [ -z "$output_dir" ]; then
        output_dir=$(mktemp -d)
    fi

    # Ensure the output directory exists
    mkdir -p "$output_dir"

    # Generate tree representation
    local tree_file="$output_dir/tree.json"
    generate_directory_tree "$root_dir" "$tree_file"

    # Check if tree file was created successfully
    if [ ! -s "$tree_file" ]; then
        # Create a simple fallback
        echo "{}" > "$tree_file"
        log "WARN" "Failed to generate tree structure for $root_dir"
    fi

    # Analyze the tree structure
    local analysis_file="$output_dir/structure_analysis.json"
    analyze_directory_structure "$tree_file" "$analysis_file"

    # Generate insights
    local insights_file="$output_dir/structure_insights.txt"
    generate_structure_insights "$analysis_file" "$insights_file"

    # Return the output directory
    echo "$output_dir"
}

# High-level function to analyze multiple directories and combine results
analyze_directories_structure() {
    local output_dir=$(mktemp -d)
    local combined_insights_file="$output_dir/combined_structure_insights.txt"

    # Create output directory
    mkdir -p "$output_dir"
    echo "# Directory Structure Analysis" > "$combined_insights_file"
    echo "================================" >> "$combined_insights_file"
    echo "" >> "$combined_insights_file"

    # Process each directory
    for dir in "$@"; do
        if [ ! -d "$dir" ]; then
            log "WARN" "Directory does not exist: $dir"
            continue
        fi

        if [ "$VERBOSE" = true ]; then
            log "INFO" "Analyzing directory structure: $dir"
        fi

        # Create directory-specific output directory
        local dir_output_path="$output_dir/$(basename "$dir")"
        mkdir -p "$dir_output_path"

        # Analyze this directory
        analyze_tree "$dir" "$dir_output_path"

        # Append insights to combined file if file exists
        if [ -f "$dir_output_path/structure_insights.txt" ]; then
            echo "## Directory: $dir" >> "$combined_insights_file"
            echo "" >> "$combined_insights_file"
            cat "$dir_output_path/structure_insights.txt" >> "$combined_insights_file"
            echo -e "\n\n" >> "$combined_insights_file"
        else
            echo "## Directory: $dir" >> "$combined_insights_file"
            echo "No structure insights available" >> "$combined_insights_file"
            echo -e "\n\n" >> "$combined_insights_file"
        fi
    done

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Combined structure analysis complete"
    fi

    # Return the output directory
    echo "$combined_insights_file"
}

# Generate Python module mapping for enhanced duplicate detection
generate_module_mapping() {
    local directories=("$@")
    local output_file=$(mktemp)

    # Create Python script for module mapping
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import os
import sys
import json
import re
import ast
from collections import defaultdict

def scan_directory(directory):
    """Scan directory for Python files and build module mapping."""
    modules = {}
    imports = defaultdict(list)
    classes = defaultdict(list)
    functions = defaultdict(list)

    # Walk through directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory)
                module_path = os.path.splitext(rel_path)[0].replace('/', '.')

                try:
                    # Parse the file to extract information
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    modules[module_path] = {'path': full_path, 'imports': [], 'classes': [], 'functions': []}

                    # Extract imports, classes, and functions using AST
                    try:
                        tree = ast.parse(content)

                        # Extract imports
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for name in node.names:
                                    modules[module_path]['imports'].append(name.name)
                                    imports[name.name].append(module_path)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    modules[module_path]['imports'].append(f"{node.module}")
                                    imports[node.module].append(module_path)
                            elif isinstance(node, ast.ClassDef):
                                modules[module_path]['classes'].append(node.name)
                                classes[node.name].append(module_path)
                            elif isinstance(node, ast.FunctionDef):
                                modules[module_path]['functions'].append(node.name)
                                functions[node.name].append(module_path)
                    except Exception as e:
                        print(f"Error parsing {full_path}: {e}", file=sys.stderr)

                except Exception as e:
                    print(f"Error processing {full_path}: {e}", file=sys.stderr)

    return {
        'modules': modules,
        'imports': {k: v for k, v in imports.items() if len(v) > 1},
        'classes': {k: v for k, v in classes.items() if len(v) > 1},
        'functions': {k: v for k, v in functions.items() if len(v) > 1}
    }

# Process all directories
results = {}
for directory in sys.argv[1:-1]:
    results[directory] = scan_directory(directory)

# Final output
with open(sys.argv[-1], 'w') as f:
    json.dump(results, f, indent=2)
EOF

    # Run the script
    python3 "$temp_script" "${directories[@]}" "$output_file"

    # Clean up
    rm -f "$temp_script"

    # Return the output file path
    echo "$output_file"
}

# Export functions for use in other modules
export -f generate_directory_tree
export -f analyze_tree
export -f analyze_directories_structure
export -f generate_module_mapping
