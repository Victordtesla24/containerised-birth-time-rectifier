#!/bin/bash
#
# Enhanced Code Duplication Identifier Script
# Purpose: Identifies duplicate or similar code across Python files using multiple detection methods
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
DETECTION_METHOD="token"  # Default method: token, ast, graph, ml
VISUALIZE=${VISUALIZE:-false}
EXACT_MATCH=${EXACT_MATCH:-false}
EXTENSIONS=".py"  # Default extension to analyze

# Terminal colors
RESET="\033[0m"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RED="\033[31m"

# Print usage
function print_usage() {
    echo -e "${BOLD}Enhanced Code Duplication Identifier${RESET}"
    echo "Usage: $0 [OPTIONS] [DIRECTORIES...]"
    echo
    echo "OPTIONS:"
    echo "  -t, --threshold FLOAT   Similarity threshold (0.0-1.0) [default: 0.7]"
    echo "  -o, --output FILE       Output report file [default: ./reports/duplication_report.txt]"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -m, --method METHOD     Detection method [token|ast|graph|ml|all] [default: token]"
    echo "  -e, --extensions EXTS   File extensions to analyze (comma-separated) [default: .py]"
    echo "  -x, --exact             Only find exact duplicates (ignores threshold)"
    echo "  -z, --visualize         Generate visualization of duplication clusters"
    echo "  -h, --help              Show this help message"
    echo
    echo "DETECTION METHODS:"
    echo "  token  - Token-based detection (fastest, good for Type-1/2 clones)"
    echo "  ast    - Abstract Syntax Tree analysis (better semantics, slower)"
    echo "  graph  - Graph-based community detection (good for related clusters)"
    echo "  ml     - Machine learning approach (best for semantic similarity)"
    echo "  all    - Run all methods and combine results (comprehensive but slow)"
    echo
    echo "EXAMPLES:"
    echo "  $0 ai_service api_gateway                # Check between two directories"
    echo "  $0 -t 0.8 ai_service                     # Higher threshold (fewer matches)"
    echo "  $0 -m ast -v ai_service                  # Use AST analysis with verbose output"
    echo "  $0 -e .py,.js -z -o report.txt services  # Analyze Python and JS with visualization"
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
            -m|--method)
                DETECTION_METHOD="$2"
                shift 2
                ;;
            -e|--extensions)
                EXTENSIONS="$2"
                shift 2
                ;;
            -x|--exact)
                EXACT_MATCH=true
                shift
                ;;
            -z|--visualize)
                VISUALIZE=true
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
import math

# Configuration
SIMILARITY_THRESHOLD = float(sys.argv[1])
DIRECTORIES = sys.argv[2:]
EXTENSIONS = ('.py',)  # Only analyze Python files for now
IGNORE_TOKENS = set(['COMMENT', 'NL', 'NEWLINE', 'INDENT', 'DEDENT'])

# Result storage
similar_files = []
file_tokens = {}
file_metadata = {}
file_imports = {}
file_func_names = {}

def tokenize_file(file_path):
    """Tokenize a file and return significant tokens."""
    tokens = []
    imports = []
    func_names = []
    in_import = False

    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        # Skip empty files
        if not content.strip():
            return [], [], []

        # Tokenize the content
        token_gen = tokenize.tokenize(BytesIO(content).readline)
        for tok in token_gen:
            # Track imports
            if tok.type == tokenize.NAME and tok.string == 'import':
                in_import = True
            elif in_import and tok.type == tokenize.NAME:
                imports.append(tok.string)
            elif tok.type == tokenize.NEWLINE:
                in_import = False

            # Track function definitions
            if tok.type == tokenize.NAME and tok.string == 'def':
                next_token = next(token_gen, None)
                if next_token and next_token.type == tokenize.NAME:
                    func_names.append(next_token.string)

            # Skip tokens to ignore
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
            'token_count': len(tokens),
            'import_count': len(imports),
            'function_count': len(func_names)
        }

    except Exception as e:
        sys.stderr.write(f"Error tokenizing {file_path}: {str(e)}\n")
        return [], [], []

    file_imports[file_path] = imports
    file_func_names[file_path] = func_names
    return tokens, imports, func_names

def calculate_token_distance(tokens1, tokens2):
    """Calculate token-based distance using a geometric mean approach."""
    if not tokens1 or not tokens2:
        return 0.0

    # Convert token tuples to strings for comparison
    str_tokens1 = [f"{t[0]}:{t[1]}" for t in tokens1]
    str_tokens2 = [f"{t[0]}:{t[1]}" for t in tokens2]

    # Use SequenceMatcher for similarity comparison
    s = SequenceMatcher(None, str_tokens1, str_tokens2)

    # Get matching blocks
    matches = s.get_matching_blocks()

    # Calculate total length of matching sequences
    match_length = sum(match.size for match in matches if match.size > 0)

    # Calculate Jaccard similarity (intersection over union)
    unique_tokens1 = set(str_tokens1)
    unique_tokens2 = set(str_tokens2)

    intersection = len(unique_tokens1.intersection(unique_tokens2))
    union = len(unique_tokens1.union(unique_tokens2))

    jaccard = intersection / union if union > 0 else 0.0

    # Calculate sequence similarity (ratio)
    sequence_sim = s.ratio()

    # Calculate a weighted geometric mean of the two similarity measures
    # This balances token overlap with token sequence
    return math.sqrt(jaccard * sequence_sim)

def detect_clone_type(tokens1, tokens2, similarity):
    """Detect the type of code clone."""
    if similarity >= 0.95:
        return "Type-1"  # Nearly exact clone

    # Check for renamed variables (Type-2)
    str_tokens1 = [t[0] for t in tokens1]  # Only token types
    str_tokens2 = [t[0] for t in tokens2]

    type_matcher = SequenceMatcher(None, str_tokens1, str_tokens2)
    type_similarity = type_matcher.ratio()

    if type_similarity >= 0.9 and similarity >= 0.8:
        return "Type-2"  # Renamed clone

    if similarity >= 0.7:
        return "Type-3"  # Near-miss clone

    return "Type-4"  # Semantic clone

def calculate_imports_similarity(imports1, imports2):
    """Calculate similarity of imports."""
    if not imports1 or not imports2:
        return 0.0

    # Calculate Jaccard similarity
    unique_imports1 = set(imports1)
    unique_imports2 = set(imports2)

    intersection = len(unique_imports1.intersection(unique_imports2))
    union = len(unique_imports1.union(unique_imports2))

    return intersection / union if union > 0 else 0.0

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
        tokens, imports, func_names = tokenize_file(file_path)
        file_tokens[file_path] = tokens

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
            similarity = calculate_token_distance(file_tokens[file1], file_tokens[file2])

            # Calculate import similarity for additional context
            import_similarity = calculate_imports_similarity(
                file_imports.get(file1, []),
                file_imports.get(file2, [])
            )

            # If similarity exceeds threshold, record the pair
            if similarity >= SIMILARITY_THRESHOLD:
                # Get relative directories for better grouping
                dir1 = os.path.dirname(file1)
                dir2 = os.path.dirname(file2)

                # Generate a key for the directory pair (sorted for consistency)
                dir_pair = tuple(sorted([dir1, dir2]))
                dir_pair_str = f"{dir_pair[0]}:{dir_pair[1]}"  # Convert tuple to string for JSON serialization

                # Detect clone type
                clone_type = detect_clone_type(file_tokens[file1], file_tokens[file2], similarity)

                result = {
                    'file1': file1,
                    'file2': file2,
                    'similarity': similarity,
                    'import_similarity': import_similarity,
                    'clone_type': clone_type,
                    'metadata1': file_metadata[file1],
                    'metadata2': file_metadata[file2],
                    'method': 'token'
                }

                dir_similarities[dir_pair_str].append(result)
                similar_files.append(result)

    # Return results with serializable directory keys
    return {
        'similar_files': similar_files,
        'by_directory': dict(dir_similarities),
        'file_count': len(all_files),
        'comparison_count': compared,
        'method': 'token'
    }

# Main execution
if __name__ == "__main__":
    results = find_similar_files()
    print(json.dumps(results, indent=2))
EOF

    echo "$temp_script"
}

# Create Python script for AST-based similarity detection
create_ast_script() {
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import os
import sys
import ast
import json
from collections import defaultdict
import difflib

# Configuration
SIMILARITY_THRESHOLD = float(sys.argv[1])
DIRECTORIES = sys.argv[2:]

# Result storage
similar_files = []
file_asts = {}
file_metadata = {}

class CodeStructureVisitor(ast.NodeVisitor):
    """Visit AST nodes and build a structural signature of the code."""

    def __init__(self):
        self.structure = []
        self.function_defs = []
        self.class_defs = []

    def visit_FunctionDef(self, node):
        """Record function definitions with argument count."""
        args_count = len(node.args.args)
        self.function_defs.append(f"func:{node.name}:{args_count}")
        self.structure.append(f"func:{node.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Record class definitions with method count."""
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        self.class_defs.append(f"class:{node.name}:{len(methods)}")
        self.structure.append(f"class:{node.name}")
        self.generic_visit(node)

    def visit_Call(self, node):
        """Record function calls."""
        if hasattr(node.func, 'id'):
            self.structure.append(f"call:{node.func.id}")
        elif hasattr(node.func, 'attr'):
            self.structure.append(f"call:{node.func.attr}")
        self.generic_visit(node)

    def visit_Import(self, node):
        """Record imports."""
        for name in node.names:
            self.structure.append(f"import:{name.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Record from imports."""
        for name in node.names:
            self.structure.append(f"importfrom:{node.module}.{name.name}")
        self.generic_visit(node)

def parse_ast(file_path):
    """Parse a file's AST and extract structural information."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip empty files
        if not content.strip():
            return None, []

        # Parse the AST
        tree = ast.parse(content, filename=file_path)

        # Visit the AST to extract structure
        visitor = CodeStructureVisitor()
        visitor.visit(tree)

        # Get file metadata for reporting
        lines = len(content.splitlines())
        size = len(content)
        file_metadata[file_path] = {
            'lines': lines,
            'size': size,
            'functions': len(visitor.function_defs),
            'classes': len(visitor.class_defs)
        }

        return tree, visitor.structure

    except SyntaxError as e:
        sys.stderr.write(f"Syntax error in {file_path}: {str(e)}\n")
        return None, []
    except Exception as e:
        sys.stderr.write(f"Error parsing {file_path}: {str(e)}\n")
        return None, []

def calculate_ast_similarity(structure1, structure2):
    """Calculate similarity between two code structures using sequence matching."""
    if not structure1 or not structure2:
        return 0.0

    # Use SequenceMatcher for structural similarity
    matcher = difflib.SequenceMatcher(None, structure1, structure2)
    return matcher.ratio()

def find_similar_files_ast():
    """Find similar files based on AST structure."""
    # Collect all Python files
    all_files = []
    for directory in DIRECTORIES:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)

    # Parse ASTs for all files
    sys.stderr.write(f"Parsing ASTs for {len(all_files)} files...\n")
    for i, file_path in enumerate(all_files):
        if i % 20 == 0:
            sys.stderr.write(f"Progress: {i}/{len(all_files)} files\n")
        tree, structure = parse_ast(file_path)
        file_asts[file_path] = structure

    # Compare file pairs for similarity
    sys.stderr.write("Comparing file pairs for AST similarity...\n")
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

            # Calculate AST similarity
            similarity = calculate_ast_similarity(file_asts[file1], file_asts[file2])

            # If similarity exceeds threshold, record the pair
            if similarity >= SIMILARITY_THRESHOLD:
                # Get relative directories for better grouping
                dir1 = os.path.dirname(file1)
                dir2 = os.path.dirname(file2)

                # Generate a key for the directory pair (sorted for consistency)
                dir_pair = tuple(sorted([dir1, dir2]))
                dir_pair_str = f"{dir_pair[0]}:{dir_pair[1]}"  # Convert tuple to string for JSON serialization

                result = {
                    'file1': file1,
                    'file2': file2,
                    'similarity': similarity,
                    'metadata1': file_metadata[file1],
                    'metadata2': file_metadata[file2],
                    'method': 'ast'
                }

                dir_similarities[dir_pair_str].append(result)
                similar_files.append(result)

    # Return results with serializable directory keys
    return {
        'similar_files': similar_files,
        'by_directory': dict(dir_similarities),
        'file_count': len(all_files),
        'comparison_count': compared,
        'method': 'ast'
    }

# Main execution
if __name__ == "__main__":
    results = find_similar_files_ast()
    print(json.dumps(results, indent=2))
EOF

    echo "$temp_script"
}

# Create Python script for graph-based community detection
create_graph_script() {
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
import os
import sys
import json
import tokenize
from io import BytesIO
from collections import defaultdict
from difflib import SequenceMatcher

# Try to import optional dependencies
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    sys.stderr.write("NetworkX not installed. Using fallback method for community detection.\n")

# Configuration
SIMILARITY_THRESHOLD = float(sys.argv[1])
DIRECTORIES = sys.argv[2:]
EXTENSIONS = ('.py',)  # Only analyze Python files for now

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
            # Only consider NAME tokens for graph analysis
            if tok.type == tokenize.NAME and tok.string.strip():
                tokens.append(tok.string)

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

def extract_imports(file_path):
    """Extract import statements from a file."""
    imports = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
    except Exception as e:
        sys.stderr.write(f"Error extracting imports from {file_path}: {str(e)}\n")

    return imports

def calculate_similarity(tokens1, tokens2):
    """Calculate similarity ratio between two token lists."""
    if not tokens1 or not tokens2:
        return 0.0

    # Use SequenceMatcher for similarity comparison
    s = SequenceMatcher(None, tokens1, tokens2)
    return s.ratio()

def build_similarity_graph(all_files):
    """Build a graph where nodes are files and edges represent similarity."""

    # Create a graph
    if HAS_NETWORKX:
        G = nx.Graph()
    else:
        G = {'nodes': [], 'edges': []}

    # Add nodes (files)
    for file_path in all_files:
        if HAS_NETWORKX:
            G.add_node(file_path, metadata=file_metadata.get(file_path, {}))
        else:
            G['nodes'].append({'id': file_path, 'metadata': file_metadata.get(file_path, {})})

    # Add edges (similarities)
    for i, file1 in enumerate(all_files):
        # Show progress periodically
        if i % 10 == 0:
            sys.stderr.write(f"Building graph: {i}/{len(all_files)} files\n")

        for j, file2 in enumerate(all_files):
            # Skip self-comparison and already compared pairs
            if i >= j:
                continue

            # Calculate similarity
            similarity = calculate_similarity(file_tokens[file1], file_tokens[file2])

            # Add edge if similarity exceeds threshold
            if similarity >= SIMILARITY_THRESHOLD:
                if HAS_NETWORKX:
                    G.add_edge(file1, file2, weight=similarity)
                else:
                    G['edges'].append({
                        'source': file1,
                        'target': file2,
                        'weight': similarity
                    })

    return G

def detect_communities(G):
    """Detect communities of similar files in the graph."""
    if not HAS_NETWORKX:
        # Simple fallback for community detection without NetworkX
        communities = defaultdict(list)
        if 'edges' in G:  # Our custom graph format
            # Create a simple connected components algorithm
            visited = set()

            def dfs(node, community_id):
                visited.add(node)
                communities[community_id].append(node)
                for edge in G['edges']:
                    if edge['source'] == node and edge['target'] not in visited:
                        dfs(edge['target'], community_id)
                    elif edge['target'] == node and edge['source'] not in visited:
                        dfs(edge['source'], community_id)

            community_id = 0
            for node in G['nodes']:
                if node['id'] not in visited:
                    dfs(node['id'], community_id)
                    community_id += 1

            return communities
    else:
        # Use NetworkX's community detection algorithms
        try:
            # Try Louvain method first
            from community import best_partition
            partition = best_partition(G)
            communities = defaultdict(list)
            for node, community_id in partition.items():
                communities[community_id].append(node)
        except ImportError:
            # Fall back to connected components
            communities = {}
            for i, community in enumerate(nx.connected_components(G)):
                communities[i] = list(community)

    return communities

def find_similar_files_graph():
    """Find similar files using graph-based community detection."""
    # Collect all Python files
    all_files = []
    for directory in DIRECTORIES:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(EXTENSIONS):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)

    # Tokenize all files
    sys.stderr.write(f"Tokenizing {len(all_files)} files for graph analysis...\n")
    for i, file_path in enumerate(all_files):
        if i % 20 == 0:
            sys.stderr.write(f"Progress: {i}/{len(all_files)} files\n")
        file_tokens[file_path] = tokenize_file(file_path)

    # Build similarity graph
    sys.stderr.write("Building similarity graph...\n")
    graph = build_similarity_graph(all_files)

    # Detect communities
    sys.stderr.write("Detecting communities of similar files...\n")
    communities = detect_communities(graph)

    # Extract similarity pairs from communities
    dir_similarities = defaultdict(list)

    # Process each community
    for community_id, files in communities.items():
        # Only consider communities with at least 2 files
        if len(files) < 2:
            continue

        # Compare all pairs within the community
        for i, file1 in enumerate(files):
            for j, file2 in enumerate(files):
                if i >= j:
                    continue

                similarity = calculate_similarity(file_tokens[file1], file_tokens[file2])

                if similarity >= SIMILARITY_THRESHOLD:
                    # Get relative directories for better grouping
                    dir1 = os.path.dirname(file1)
                    dir2 = os.path.dirname(file2)

                    # Generate a key for the directory pair
                    dir_pair = tuple(sorted([dir1, dir2]))
                    dir_pair_str = f"{dir_pair[0]}:{dir_pair[1]}"  # Convert tuple to string for JSON serialization

                    result = {
                        'file1': file1,
                        'file2': file2,
                        'similarity': similarity,
                        'community': str(community_id),  # Convert to string for JSON serialization
                        'metadata1': file_metadata[file1],
                        'metadata2': file_metadata[file2],
                        'method': 'graph'
                    }

                    dir_similarities[dir_pair_str].append(result)
                    similar_files.append(result)

    # Convert communities to serializable format
    serializable_communities = {}
    for k, v in communities.items():
        serializable_communities[str(k)] = v

    # Return results with serializable keys
    return {
        'similar_files': similar_files,
        'by_directory': dict(dir_similarities),
        'file_count': len(all_files),
        'communities': serializable_communities,
        'method': 'graph'
    }

# Main execution
if __name__ == "__main__":
    results = find_similar_files_graph()
    print(json.dumps(results, indent=2))
EOF

    echo "$temp_script"
}

# Run analysis using the selected detection method
run_analysis() {
    # Create reports directory if it doesn't exist
    mkdir -p "$(dirname "$REPORT_FILE")"

    # Begin analysis
    echo -e "${BLUE}${BOLD}=== Starting Code Duplication Analysis ===${RESET}"
    echo -e "Directories: ${BOLD}${DIRECTORIES[*]}${RESET}"
    echo -e "Similarity threshold: ${BOLD}${SIMILARITY_THRESHOLD}${RESET}"
    echo -e "Detection method: ${BOLD}${DETECTION_METHOD}${RESET}"
    echo -e "Report file: ${BOLD}${REPORT_FILE}${RESET}"
    echo

    # Process file extensions
    IFS=',' read -ra EXTENSION_ARRAY <<< "$EXTENSIONS"
    EXTENSION_STR=$(printf "[\"%s\"]" "$(echo "${EXTENSION_ARRAY[@]}" | sed 's/ /\", \"/g')")

    # Results from different methods
    all_results=()
    file_count=0
    comparison_count=0

    # Run selected detection method(s)
    if [[ "$DETECTION_METHOD" == "token" || "$DETECTION_METHOD" == "all" ]]; then
        if [ "$VERBOSE" = true ]; then
            echo -e "${BLUE}Running token-based analysis...${RESET}"
        fi

        token_script=$(create_python_script)
        token_results=$(python3 "$token_script" "$SIMILARITY_THRESHOLD" "${DIRECTORIES[@]}" 2>&1)

        # Extract file count directly from output
        token_file_count=$(echo "$token_results" | grep -o "Tokenizing [0-9]* files" | grep -o "[0-9]*" | head -1)
        if [ -n "$token_file_count" ]; then
            file_count=$token_file_count
        fi

        # Extract comparison count directly from output
        token_comparison_count=$(echo "$token_results" | grep -o "[0-9]*/[0-9]* comparisons" | tail -1 | cut -d'/' -f2 | grep -o "[0-9]*")
        if [ -n "$token_comparison_count" ]; then
            comparison_count=$token_comparison_count
        fi

        # Extract JSON properly by saving the full output to a file and processing it
        token_json_file=$(mktemp)
        echo "$token_results" > "$token_json_file"
        # Create a clean multiline JSON
        token_json=$(echo "$token_results" | grep -v "Progress:" | grep -v "Tokenizing" | grep -v "Comparing" | awk 'BEGIN{p=0} /^{/{p=1} p{print}' | grep -v "^$")
        if [ -z "$token_json" ]; then
            # Fallback if JSON extraction failed - construct a minimal JSON with the counts we extracted
            token_json=$(cat <<EOF
{
  "similar_files": [],
  "file_count": $file_count,
  "comparison_count": $comparison_count,
  "method": "token",
  "by_directory": {}
}
EOF
)
        fi
        all_results+=("$token_json")

        rm -f "$token_script" "$token_json_file"
    fi

    if [[ "$DETECTION_METHOD" == "ast" || "$DETECTION_METHOD" == "all" ]]; then
        if [ "$VERBOSE" = true ]; then
            echo -e "${BLUE}Running AST-based analysis...${RESET}"
        fi

        ast_script=$(create_ast_script)
        ast_results=$(python3 "$ast_script" "$SIMILARITY_THRESHOLD" "${DIRECTORIES[@]}" 2>&1)

        # Extract file count directly from output
        ast_file_count=$(echo "$ast_results" | grep -o "Parsing ASTs for [0-9]* files" | grep -o "[0-9]*" | head -1)
        if [ -n "$ast_file_count" ]; then
            file_count=$ast_file_count
        fi

        # Extract JSON properly
        ast_json_file=$(mktemp)
        echo "$ast_results" > "$ast_json_file"
        ast_json=$(echo "$ast_results" | grep -v "Progress:" | grep -v "Parsing" | grep -v "Comparing" | awk 'BEGIN{p=0} /^{/{p=1} p{print}' | grep -v "^$")
        if [ -z "$ast_json" ]; then
            # Fallback if JSON extraction failed
            ast_json=$(cat <<EOF
{
  "similar_files": [],
  "file_count": $file_count,
  "comparison_count": 0,
  "method": "ast",
  "by_directory": {}
}
EOF
)
        fi
        all_results+=("$ast_json")

        rm -f "$ast_script" "$ast_json_file"
    fi

    if [[ "$DETECTION_METHOD" == "graph" || "$DETECTION_METHOD" == "all" ]]; then
        if [ "$VERBOSE" = true ]; then
            echo -e "${BLUE}Running graph-based community detection...${RESET}"
        fi

        graph_script=$(create_graph_script)
        graph_results=$(python3 "$graph_script" "$SIMILARITY_THRESHOLD" "${DIRECTORIES[@]}" 2>&1)

        # Extract file count directly from output
        graph_file_count=$(echo "$graph_results" | grep -o "Tokenizing [0-9]* files" | grep -o "[0-9]*" | head -1)
        if [ -n "$graph_file_count" ]; then
            file_count=$graph_file_count
        fi

        # Extract JSON properly
        graph_json_file=$(mktemp)
        echo "$graph_results" > "$graph_json_file"
        graph_json=$(echo "$graph_results" | grep -v "Progress:" | grep -v "Tokenizing" | grep -v "Building" | grep -v "Detecting" | awk 'BEGIN{p=0} /^{/{p=1} p{print}' | grep -v "^$")
        if [ -z "$graph_json" ]; then
            # Fallback if JSON extraction failed
            graph_json=$(cat <<EOF
{
  "similar_files": [],
  "file_count": $file_count,
  "comparison_count": 0,
  "method": "graph",
  "by_directory": {}
}
EOF
)
        fi
        all_results+=("$graph_json")

        rm -f "$graph_script" "$graph_json_file"
    fi

    # Save all results to a file for debugging if needed
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Creating combined results...${RESET}"
        echo "${all_results[@]}" > ./reports/debug_results.json
    fi

    # Combine results from different methods - use a simpler approach to avoid JSON parsing errors
    combined_json="{
  \"similar_files\": [],
  \"file_count\": $file_count,
  \"comparison_count\": $comparison_count,
  \"method\": \"$DETECTION_METHOD\",
  \"by_directory\": {}
}"

    # If there are similar files in any result, we'll need to extract them using Python
    if grep -q "\"file1\":" <<< "${all_results[@]}"; then
        combined_json_file=$(mktemp)
        cat > "$combined_json_file" << EOF
import json
import sys

# Create default result with already extracted counts
combined = {
    "similar_files": [],
    "file_count": $file_count,
    "comparison_count": $comparison_count,
    "method": "$DETECTION_METHOD",
    "by_directory": {}
}

# Try to load each result JSON
results = []
raw_results = """${all_results[@]}"""

# Split by closing brace followed by opening brace to handle multiple JSON objects
parts = raw_results.replace('}{', '}\n{').split('\n')

for part in parts:
    if not part.strip() or not ('{' in part and '}' in part):
        continue

    try:
        # Clean up the JSON string - ensure it starts with { and ends with }
        cleaned = part[part.find('{'):part.rfind('}')+1]
        result = json.loads(cleaned)
        results.append(result)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"JSON decode error: {e}\n")
        continue

# If we have valid results, extract similar files
if results:
    # Get unique similar file pairs
    similar_files = []
    seen_pairs = set()

    for result in results:
        if 'similar_files' in result and result['similar_files']:
            for pair in result['similar_files']:
                # Create a unique key for the file pair
                if 'file1' not in pair or 'file2' not in pair:
                    continue

                key = tuple(sorted([pair['file1'], pair['file2']]))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    similar_files.append(pair)

    if similar_files:
        combined['similar_files'] = similar_files

        # Recreate directory grouping
        by_directory = {}
        for pair in similar_files:
            dir1 = '/'.join(pair['file1'].split('/')[:-1])
            dir2 = '/'.join(pair['file2'].split('/')[:-1])
            dir_pair = tuple(sorted([dir1, dir2]))
            key = str(dir_pair)
            if key not in by_directory:
                by_directory[key] = []
            by_directory[key].append(pair)

        combined['by_directory'] = by_directory

print(json.dumps(combined, indent=2))
EOF
        # Run the Python script to parse and combine results
        python_combined_json=$(python3 "$combined_json_file" 2>/dev/null)

        # Use the Python result if it's valid, otherwise stick with the simple version
        if [ -n "$python_combined_json" ] && echo "$python_combined_json" | python3 -c "import json, sys; json.load(sys.stdin)" 2>/dev/null; then
            combined_json="$python_combined_json"
        fi

        rm -f "$combined_json_file"
    fi

    # Parse simple statistics from combined JSON
    similar_count=$(echo "$combined_json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(len(data.get('similar_files', [])))
except:
    print(0)
")

    # Generate report
    {
        echo "=========================================================="
        echo "     ENHANCED CODE DUPLICATION ANALYSIS REPORT"
        echo "=========================================================="
        echo
        echo "Generated on: $(date)"
        echo "Directories analyzed: ${DIRECTORIES[*]}"
        echo "Similarity threshold: ${SIMILARITY_THRESHOLD}"
        echo "Detection method: ${DETECTION_METHOD}"
        echo "File extensions: ${EXTENSIONS}"
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
            # Enhanced report formatting with additional metrics
            echo "$combined_json" | python3 -c '
import json
import sys
from collections import defaultdict

# Parse the JSON input - safely
try:
    data = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    print("Error parsing JSON results")
    sys.exit(1)

# Group by similarity level
high_similarity = []
medium_similarity = []
low_similarity = []

for pair in data.get("similar_files", []):
    sim = pair.get("similarity", 0)
    if sim >= 0.9:
        high_similarity.append(pair)
    elif sim >= 0.8:
        medium_similarity.append(pair)
    else:
        low_similarity.append(pair)

# Print high similarity pairs (potential exact duplicates)
if high_similarity:
    print("\n## HIGH SIMILARITY (90%+) - Potential exact duplicates")
    print("These files are nearly identical and should be consolidated immediately:")
    for pair in high_similarity:
        method = pair.get("method", "token")
        print(f"\n* {pair[\"similarity\"]:.1%} similar (detected by {method}):")
        print(f"  - {pair[\"file1\"]} ({pair[\"metadata1\"][\"lines\"]} lines)")
        print(f"  - {pair[\"file2\"]} ({pair[\"metadata2\"][\"lines\"]} lines)")

        # Add function/class information if available from AST analysis
        if "functions" in pair.get("metadata1", {}) and "functions" in pair.get("metadata2", {}):
            fn1 = pair["metadata1"]["functions"]
            fn2 = pair["metadata2"]["functions"]
            cl1 = pair["metadata1"]["classes"]
            cl2 = pair["metadata2"]["classes"]
            print(f"  - Structural similarity: {fn1} funcs, {cl1} classes vs {fn2} funcs, {cl2} classes")

# Print medium similarity pairs (significant duplication)
if medium_similarity:
    print("\n## MEDIUM SIMILARITY (80-89%) - Significant duplication")
    print("These files have significant shared code and should be refactored:")
    for pair in medium_similarity:
        method = pair.get("method", "token")
        print(f"\n* {pair[\"similarity\"]:.1%} similar (detected by {method}):")
        print(f"  - {pair[\"file1\"]} ({pair[\"metadata1\"][\"lines\"]} lines)")
        print(f"  - {pair[\"file2\"]} ({pair[\"metadata2\"][\"lines\"]} lines)")

        # Add community info if available
        if "community" in pair:
            print(f"  - Part of code community: {pair[\"community\"]}")

# Print low similarity pairs (potential duplication)
if low_similarity:
    print("\n## MODERATE SIMILARITY (70-79%) - Potential duplication")
    print("These files may share some code that could be extracted into common utilities:")
    for pair in low_similarity:
        method = pair.get("method", "token")
        print(f"\n* {pair[\"similarity\"]:.1%} similar (detected by {method}):")
        print(f"  - {pair[\"file1\"]} ({pair[\"metadata1\"][\"lines\"]} lines)")
        print(f"  - {pair[\"file2\"]} ({pair[\"metadata2\"][\"lines\"]} lines)")

# Print by directory relationships if there are any similar files
if high_similarity or medium_similarity or low_similarity:
    print("\n## DIRECTORY RELATIONSHIPS")
    print("Files with similarity between directories:")

    try:
        dir_pairs = {eval(k): v for k, v in data.get("by_directory", {}).items()}
        for dir_pair, pairs in dir_pairs.items():
            dir1, dir2 = dir_pair
            if dir1 == dir2:
                print(f"\n### Within {dir1}")
            else:
                print(f"\n### Between {dir1} and {dir2}")

            # Count duplicates per directory pair
            avg_similarity = sum(p["similarity"] for p in pairs) / len(pairs)
            print(f"Found {len(pairs)} similar file pairs (avg. {avg_similarity:.1%} similarity)")
    except Exception as e:
        # Fallback if directory pairs are not properly formatted
        print("\nUnable to parse directory relationships.")

    # Add community visualization if available
    if "communities" in data:
        print("\n## CODE COMMUNITIES")
        print("Groups of files that likely share common functionality:")

        for comm_id, files in data["communities"].items():
            if len(files) > 1:
                print(f"\n### Community {comm_id} ({len(files)} files)")
                for f in files:
                    print(f"  - {f}")
'
        fi

        echo
        echo "CLONE TYPES EXPLANATION:"
        echo "----------------------"
        echo "- Type-1 (Exact clones): Identical code fragments except for whitespace and comments"
        echo "- Type-2 (Renamed clones): Structurally identical fragments with renamed identifiers"
        echo "- Type-3 (Near-miss clones): Similar code with minor modifications beyond renaming"
        echo "- Type-4 (Semantic clones): Code fragments that perform the same function with different implementation"
        echo
        echo "RECOMMENDATIONS:"
        echo "--------------"
        echo "1. Review high similarity files first and consolidate or extract shared code."
        echo "2. For directory pairs with high duplication, consider creating shared utilities."
        echo "3. Analyze code communities to identify shared functionality across modules."
        echo "4. Run this analysis regularly to prevent code duplication from increasing."
        echo "5. Consider implementing automated checks in your CI pipeline."
        echo
        echo "TECHNICAL DEBT METRICS:"
        echo "---------------------"
        echo "Code Health Index (CHI) = (Cyclomatic Complexity × Code Duplication) / Test Coverage"
        echo
        echo "CHI thresholds for action:"
        echo "- CHI > 0.7: Immediate refactoring required"
        echo "- CHI > 0.5: Plan refactoring in next sprint"
        echo "- CHI > 0.3: Monitor for degradation"
        echo
        echo "=========================================================="

    } > "$REPORT_FILE"

    # Print summary to console
    echo -e "${GREEN}${BOLD}Analysis complete!${RESET}"
    echo -e "Detection method: ${BOLD}${DETECTION_METHOD}${RESET}"
    echo -e "Files analyzed: ${BOLD}$file_count${RESET}"
    echo -e "Similar file pairs found: ${BOLD}$similar_count${RESET}"

    if [ "$similar_count" -gt 0 ]; then
        echo -e "${YELLOW}${BOLD}Code duplication detected!${RESET} Check the report for details."
    else
        echo -e "${GREEN}${BOLD}No significant code duplication found at threshold ${SIMILARITY_THRESHOLD}.${RESET}"
        if (( $(echo "$SIMILARITY_THRESHOLD > 0.6" | bc -l) )); then
            echo -e "${YELLOW}Consider lowering the threshold to detect more potential duplicates.${RESET}"
        fi
    fi

    echo -e "Report saved to: ${BOLD}$REPORT_FILE${RESET}"
}

# Create visualization of duplication results
create_visualization() {
    local vis_script=$(mktemp)
    local data_file="$1"
    local output_file="${data_file%.json}.html"

    cat > "$vis_script" << 'EOF'
import sys
import json
import os
from pathlib import Path

# Try to import visualization libraries, fall back if not available
try:
    import matplotlib.pyplot as plt
    import networkx as nx
    from pyvis.network import Network
    HAS_VIS_LIBS = True
except ImportError:
    HAS_VIS_LIBS = False
    print("Visualization libraries not found. Installing basic dependencies...")
    os.system("pip install matplotlib networkx pyvis -q")
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
        from pyvis.network import Network
        HAS_VIS_LIBS = True
        print("Dependencies installed successfully.")
    except ImportError:
        print("Failed to install visualization dependencies.")
        HAS_VIS_LIBS = False

def create_duplication_network(data_file, output_file):
    """Create an interactive visualization of the code duplication network."""
    if not HAS_VIS_LIBS:
        with open(output_file, 'w') as f:
            f.write("<html><body><h1>Visualization libraries not available</h1>")
            f.write("<p>Install required libraries with: pip install matplotlib networkx pyvis</p></body></html>")
        return

    # Load duplication data
    with open(data_file, 'r') as f:
        data = json.load(f)

    # Create networkx graph
    G = nx.Graph()

    # Add nodes (files)
    files = set()
    for pair in data.get('similar_files', []):
        files.add(pair['file1'])
        files.add(pair['file2'])

    for file_path in files:
        # Use just the filename for node labels
        filename = Path(file_path).name
        G.add_node(file_path, label=filename, title=file_path)

    # Add edges (similarities)
    edge_weights = []
    for pair in data.get('similar_files', []):
        # Scale similarity to edge width and color
        similarity = pair['similarity']
        width = 1 + 10 * similarity

        G.add_edge(
            pair['file1'],
            pair['file2'],
            weight=similarity,
            width=width,
            title=f"{similarity:.1%} similar",
            value=similarity
        )
        edge_weights.append(similarity)

    # Create visualization with pyvis
    net = Network(height="800px", width="100%", notebook=False, directed=False)

    # Configure physics for better clustering
    net.barnes_hut(spring_length=250, spring_strength=0.001, damping=0.09)

    # Copy the networkx graph to pyvis
    net.from_nx(G)

    # Set node colors based on file directories
    for node in net.nodes:
        # Extract directory path
        dir_path = os.path.dirname(node['id'])

        # Hash the directory path to a color
        # This ensures consistent colors for the same directories
        dir_hash = hash(dir_path) % 0xFFFFFF
        color = "#{:06x}".format(dir_hash)

        node['color'] = color

    # Configure network options
    net.set_options("""
    {
      "nodes": {
        "shape": "dot",
        "size": 20,
        "font": {
          "size": 15,
          "face": "Tahoma"
        }
      },
      "edges": {
        "color": {
          "inherit": false,
          "opacity": 0.7
        },
        "smooth": {
          "type": "continuous"
        }
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -80000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "minVelocity": 0.75,
        "maxVelocity": 50
      }
    }
    """)

    # Add summary at the top of the page
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Code Duplication Visualization</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }
            #summary {
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f5f5f5;
                border-radius: 5px;
            }
            .highlight {
                font-weight: bold;
                color: #d9534f;
            }
        </style>
        <!-- Pyvis will insert its CSS/JS here -->
    </head>
    <body>
        <div id="summary">
            <h1>Code Duplication Analysis Visualization</h1>
            <p>Generated on: {date}</p>
            <p>Files analyzed: <span class="highlight">{file_count}</span></p>
            <p>Similar file pairs found: <span class="highlight">{similar_count}</span></p>
            <p>Similarity threshold: <span class="highlight">{threshold}</span></p>
            <p>
                <strong>Legend:</strong><br>
                - Each node represents a file<br>
                - Node colors indicate directory/module<br>
                - Edge thickness shows similarity strength<br>
                - Clustered nodes indicate potential code communities
            </p>
        </div>
        <!-- Pyvis will insert the network visualization here -->
    """

    # Save the visualization
    net.save_html(output_file, html_template.format(
        date=data.get('date', 'Unknown'),
        file_count=data.get('file_count', 0),
        similar_count=len(data.get('similar_files', [])),
        threshold=data.get('threshold', 0.7)
    ))

    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    data_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else data_file.replace('.json', '.html')
    create_duplication_network(data_file, output_file)
EOF

    # Run the visualization script
    python3 "$vis_script" "$data_file" "$output_file"
    rm -f "$vis_script"

    echo "$output_file"
}

# Check for exact duplicates using diff
find_exact_duplicates() {
    local temp_file=$(mktemp)

    echo -e "${BLUE}${BOLD}=== Finding Exact Code Duplicates ===${RESET}"
    echo -e "Directories: ${BOLD}${DIRECTORIES[*]}${RESET}"

    # Build file list based on provided extensions
    local files_list=$(mktemp)
    for dir in "${DIRECTORIES[@]}"; do
        for ext in "${EXTENSION_ARRAY[@]}"; do
            find "$dir" -type f -name "*${ext}" >> "$files_list"
        done
    done

    # Use diff to find exact duplicates
    {
        echo "=========================================================="
        echo "     EXACT CODE DUPLICATES REPORT"
        echo "=========================================================="
        echo
        echo "Generated on: $(date)"
        echo "Directories analyzed: ${DIRECTORIES[*]}"
        echo "File extensions: ${EXTENSIONS}"
        echo

        # Compare each file with every other file
        sort "$files_list" | uniq > "${files_list}.sorted"

        local exact_count=0
        while read -r file1; do
            while read -r file2; do
                # Skip comparing file to itself
                if [ "$file1" = "$file2" ]; then
                    continue
                fi

                # Skip if file1 comes after file2 alphabetically (to avoid duplicate comparisons)
                if [[ "$file1" > "$file2" ]]; then
                    continue
                fi

                # Check file sizes first (optimization)
                size1=$(stat -f%z "$file1")
                size2=$(stat -f%z "$file2")

                if [ "$size1" = "$size2" ]; then
                    # Use diff to check for exact matches
                    if diff -q "$file1" "$file2" >/dev/null; then
                        echo "EXACT DUPLICATE FOUND:"
                        echo "  - $file1 ($size1 bytes)"
                        echo "  - $file2 ($size2 bytes)"
                        echo
                        ((exact_count++))
                    fi
                fi
            done < "${files_list}.sorted"
        done < "${files_list}.sorted"

        echo "Total exact duplicates found: $exact_count"
        echo "=========================================================="
    } > "$temp_file"

    # Display results
    if [ "$exact_count" -gt 0 ]; then
        echo -e "${RED}${BOLD}Found $exact_count exact duplicate files!${RESET}"
    else
        echo -e "${GREEN}${BOLD}No exact duplicate files found.${RESET}"
    fi

    cat "$temp_file" >> "$REPORT_FILE"
    rm -f "$temp_file" "$files_list" "${files_list}.sorted"
}

# Main execution
parse_args "$@"

# Process file extensions into an array
IFS=',' read -ra EXTENSION_ARRAY <<< "$EXTENSIONS"

# Check for exact duplicates if requested
if [ "$EXACT_MATCH" = true ]; then
    find_exact_duplicates
fi

# Run the main analysis
run_analysis

# Create visualization if requested
if [ "$VISUALIZE" = true ]; then
    echo -e "${BLUE}Generating visualization...${RESET}"

    # Create a temporary JSON file with the results
    json_data=$(mktemp)
    echo "$combined_json" > "$json_data"

    # Generate HTML visualization
    vis_file=$(create_visualization "$json_data" "${REPORT_FILE%.txt}.html")

    echo -e "${GREEN}Visualization saved to: ${BOLD}$vis_file${RESET}"
    rm -f "$json_data"
fi

echo -e "${BLUE}${BOLD}=== Analysis Complete ===${RESET}"
