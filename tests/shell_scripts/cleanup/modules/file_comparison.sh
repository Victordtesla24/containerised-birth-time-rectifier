#!/bin/bash
#
# File comparison module for enhanced code duplication detection
#

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# Tokenize a file for comparison
tokenize_file() {
    local file="$1"
    local temp_file=$(mktemp)

    # First remove comments and whitespace
    python3 -c "
import re, sys
with open('$file', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
# Remove docstrings
content = re.sub(r'\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'', '', content, flags=re.DOTALL)
# Remove comments
content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
# Normalize whitespace
content = re.sub(r'\s+', ' ', content)
# Remove string literals
content = re.sub(r'[\'\"].*?[\'\"]', '\"STRING\"', content)
# Remove numeric literals
content = re.sub(r'\\b\\d+\\b', 'NUMBER', content)
# Output tokens
tokens = re.findall(r'\\w+|[^\\w\\s]', content)
print(' '.join(tokens))
" > "$temp_file" 2>/dev/null || echo "ERROR" > "$temp_file"

    # Check if tokenization was successful
    if [ "$(cat "$temp_file")" = "ERROR" ]; then
        # Fallback to simpler tokenization
        cat "$file" | tr -s '[:space:]' ' ' | tr -cs '[:alnum:]_' ' ' > "$temp_file"
    fi

    echo "$temp_file"
}

# Compare files using token-based method
compare_files_tokens() {
    local file1="$1"
    local file2="$2"
    local threshold="${3:-0.1}"
    local temp_dir=$(mktemp -d)

    # Tokenize both files
    local tokens1=$(tokenize_file "$file1")
    local tokens2=$(tokenize_file "$file2")

    # Calculate similarity using Python with enhanced token analysis
    python3 -c "
from difflib import SequenceMatcher
import sys
import re
import hashlib

def normalize_tokens(tokens):
    # Replace variable names with placeholders to focus on structure
    var_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    return [token if not var_pattern.match(token) else 'VAR' for token in tokens]

def sliding_window_hashes(tokens, window_size=4):
    # Create sliding window hashes for fuzzy matching
    if len(tokens) < window_size:
        return [hashlib.md5(' '.join(tokens).encode()).hexdigest()]

    hashes = []
    for i in range(len(tokens) - window_size + 1):
        window = tokens[i:i+window_size]
        hashes.append(hashlib.md5(' '.join(window).encode()).hexdigest())
    return hashes

with open('$tokens1', 'r') as f1, open('$tokens2', 'r') as f2:
    tokens1 = f1.read().split()
    tokens2 = f2.read().split()

# Normalize tokens to focus on structure
norm_tokens1 = normalize_tokens(tokens1)
norm_tokens2 = normalize_tokens(tokens2)

# Basic sequence similarity
basic_similarity = SequenceMatcher(None, norm_tokens1, norm_tokens2).ratio()

# Sliding window hash similarity for fuzzy matching
window_size = min(4, min(len(norm_tokens1), len(norm_tokens2)))
if window_size > 0:
    hashes1 = set(sliding_window_hashes(norm_tokens1, window_size))
    hashes2 = set(sliding_window_hashes(norm_tokens2, window_size))

    # Calculate Jaccard similarity between hash sets
    if not hashes1 and not hashes2:
        hash_similarity = 1.0  # Both empty means identical
    elif not hashes1 or not hashes2:
        hash_similarity = 0.0  # One empty means completely different
    else:
        intersection = len(hashes1.intersection(hashes2))
        union = len(hashes1.union(hashes2))
        hash_similarity = intersection / union
else:
    hash_similarity = 0.0

# Weighted combination
final_similarity = 0.6 * basic_similarity + 0.4 * hash_similarity
print(final_similarity)
" 2>/dev/null || echo "0.0"

    # Clean up
    rm -f "$tokens1" "$tokens2"
    rmdir "$temp_dir" 2>/dev/null || true
}

# Extract AST from Python file
extract_ast() {
    local file="$1"
    local output_file="$2"

    python3 -c "
import ast, json, sys
import hashlib

def extract_control_flow(node):
    '''Extract control flow structure for more accurate clone detection'''
    if isinstance(node, ast.If):
        return 'IF'
    elif isinstance(node, ast.For):
        return 'FOR'
    elif isinstance(node, ast.While):
        return 'WHILE'
    elif isinstance(node, ast.With):
        return 'WITH'
    elif isinstance(node, ast.Try):
        return 'TRY'
    elif isinstance(node, ast.FunctionDef):
        # Extract nested control flow in functions
        flow = ['FUNC']
        for body_node in node.body:
            if isinstance(body_node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                flow.append(extract_control_flow(body_node))
        return '-'.join(flow)
    return ''

try:
    with open('$file', 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    parsed = ast.parse(code)

    # Extract function and class names
    functions = []
    classes = []
    imports = []

    for node in ast.walk(parsed):
        if isinstance(node, ast.FunctionDef):
            # Extract control flow structure
            flow_signature = []
            for body_node in node.body:
                if isinstance(body_node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    flow_signature.append(extract_control_flow(body_node))

            # Create a structure hash
            structure_hash = hashlib.md5('-'.join(flow_signature).encode()).hexdigest()

            functions.append({
                'name': node.name,
                'line': node.lineno,
                'args': len(node.args.args) if hasattr(node, 'args') else 0,
                'structure': structure_hash
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({
                'name': node.name,
                'line': node.lineno
            })
        elif isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for n in node.names:
                    imports.append(f'{node.module}.{n.name}')

    result = {
        'functions': functions,
        'classes': classes,
        'imports': imports
    }

    with open('$output_file', 'w') as f:
        json.dump(result, f)

    print('OK')
except Exception as e:
    print(f'ERROR: {str(e)}')
    with open('$output_file', 'w') as f:
        json.dump({'error': str(e)}, f)
" 2>/dev/null
}

# Compare files using AST-based method
compare_files_ast() {
    local file1="$1"
    local file2="$2"
    local threshold="${3:-0.1}"
    local temp_dir=$(mktemp -d)
    local ast1="${temp_dir}/ast1.json"
    local ast2="${temp_dir}/ast2.json"

    # Extract AST from both files with enhanced analysis
    extract_ast "$file1" "$ast1"
    extract_ast "$file2" "$ast2"

    # Calculate similarity using Python with control flow analysis
    python3 -c "
import json
import sys
import hashlib
from collections import Counter

def load_ast(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return {'functions': [], 'classes': [], 'imports': []}

# Create a control flow signature for a function based on its properties
def get_function_signature(func):
    signature = [func['name']]

    # Add argument count
    signature.append(f'args:{func.get(\"args\", 0)}')

    # Create a simplified hash of the function structure
    if 'structure' in func:
        signature.append(f'structure:{func[\"structure\"]}')

    return hashlib.md5(':'.join(signature).encode()).hexdigest()

ast1 = load_ast('$ast1')
ast2 = load_ast('$ast2')

# Check for errors
if 'error' in ast1 or 'error' in ast2:
    print('0.0')
    sys.exit(0)

# Calculate Jaccard similarity for sets
def jaccard(set1, set2):
    if not set1 and not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

# Calculate similarity of function distributions
def function_signature_similarity(funcs1, funcs2):
    signatures1 = [get_function_signature(f) for f in funcs1]
    signatures2 = [get_function_signature(f) for f in funcs2]

    # Count frequencies
    counter1 = Counter(signatures1)
    counter2 = Counter(signatures2)

    # Calculate cosine similarity
    common_funcs = set(counter1.keys()) & set(counter2.keys())
    if not common_funcs:
        return 0.0

    dot_product = sum(counter1[x] * counter2[x] for x in common_funcs)
    norm1 = sum(v**2 for v in counter1.values()) ** 0.5
    norm2 = sum(v**2 for v in counter2.values()) ** 0.5

    return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

# Extract function and class names
func_names1 = {f['name'] for f in ast1.get('functions', [])}
func_names2 = {f['name'] for f in ast2.get('functions', [])}
class_names1 = {c['name'] for c in ast1.get('classes', [])}
class_names2 = {c['name'] for c in ast2.get('classes', [])}
imports1 = set(ast1.get('imports', []))
imports2 = set(ast2.get('imports', []))

# Calculate similarities
func_name_sim = jaccard(func_names1, func_names2)
class_sim = jaccard(class_names1, class_names2)
import_sim = jaccard(imports1, imports2)

# Calculate function signature similarity
func_sig_sim = function_signature_similarity(
    ast1.get('functions', []),
    ast2.get('functions', [])
)

# Calculate weighted score
weights = [0.3, 0.2, 0.2, 0.3]  # function names, classes, imports, function signatures
score = (
    weights[0] * func_name_sim +
    weights[1] * class_sim +
    weights[2] * import_sim +
    weights[3] * func_sig_sim
)

print(score)
" 2>/dev/null || echo "0.0"

    # Clean up
    rm -f "$ast1" "$ast2"
    rmdir "$temp_dir" 2>/dev/null || true
}

# Compare files using graph-based method
compare_files_graph() {
    local file1="$1"
    local file2="$2"
    local threshold="${3:-0.1}"

    # Create temporary files for control flow graphs
    local temp_dir=$(mktemp -d)
    local graph1="${temp_dir}/graph1.json"
    local graph2="${temp_dir}/graph2.json"

    # Extract control flow graphs
    extract_control_flow_graph "$file1" "$graph1"
    extract_control_flow_graph "$file2" "$graph2"

    # For graph-based comparison, we use a combination of AST, token, and control flow methods
    local ast_similarity=$(compare_files_ast "$file1" "$file2" "$threshold")
    local token_similarity=$(compare_files_tokens "$file1" "$file2" "$threshold")
    local graph_similarity=$(compare_control_flow_graphs "$graph1" "$graph2")

    # Calculate weighted average
    python3 -c "
ast_sim = float('$ast_similarity' or 0.0)
token_sim = float('$token_similarity' or 0.0)
graph_sim = float('$graph_similarity' or 0.0)
print((ast_sim * 0.4) + (token_sim * 0.3) + (graph_sim * 0.3))
" 2>/dev/null || echo "0.0"

    # Clean up
    rm -f "$graph1" "$graph2"
    rmdir "$temp_dir" 2>/dev/null || true
}

# Extract control flow graph
extract_control_flow_graph() {
    local file="$1"
    local output_file="$2"

    python3 -c "
import ast
import json
import sys

def extract_graph(node, parent=None):
    '''Extract control flow graph from AST node'''
    result = {'type': type(node).__name__, 'children': []}

    # Add specific attributes based on node type
    if isinstance(node, ast.FunctionDef):
        result['name'] = node.name
    elif isinstance(node, ast.ClassDef):
        result['name'] = node.name
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            result['name'] = node.func.id

    # Process child nodes
    if hasattr(node, 'body'):
        for child in node.body:
            result['children'].append(extract_graph(child, result))

    return result

try:
    with open('$file', 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    tree = ast.parse(code)
    graph = extract_graph(tree)

    with open('$output_file', 'w') as f:
        json.dump(graph, f)

    print('OK')
except Exception as e:
    print(f'ERROR: {str(e)}')
    with open('$output_file', 'w') as f:
        json.dump({'error': str(e)}, f)
" 2>/dev/null
}

# Compare control flow graphs
compare_control_flow_graphs() {
    local graph1="$1"
    local graph2="$2"

    python3 -c "
import json
import sys

def load_graph(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return {'children': []}

def node_similarity(node1, node2):
    '''Calculate similarity between two graph nodes'''
    if node1.get('type') != node2.get('type'):
        return 0.0

    # Basic type similarity
    similarity = 1.0

    # If nodes have names, compare them
    if 'name' in node1 and 'name' in node2:
        if node1['name'] == node2['name']:
            similarity *= 1.0
        else:
            similarity *= 0.5

    # Compare children recursively
    children1 = node1.get('children', [])
    children2 = node2.get('children', [])

    if not children1 and not children2:
        return similarity

    if not children1 or not children2:
        return similarity * 0.5

    # Calculate max similarity for each child
    max_similarities = []
    for c1 in children1:
        max_sim = 0.0
        for c2 in children2:
            sim = node_similarity(c1, c2)
            max_sim = max(max_sim, sim)
        max_similarities.append(max_sim)

    # Average of max similarities
    avg_similarity = sum(max_similarities) / len(max_similarities)

    return (similarity + avg_similarity) / 2

graph1 = load_graph('$graph1')
graph2 = load_graph('$graph2')

# Check for errors
if 'error' in graph1 or 'error' in graph2:
    print('0.0')
    sys.exit(0)

# Calculate overall similarity
similarity = node_similarity(graph1, graph2)
print(similarity)
" 2>/dev/null || echo "0.0"
}

# Find duplicate lines
find_duplicate_lines() {
    local file="$1"
    local output_file="$2"
    local min_lines="${3:-3}"

    # Extract duplicate line sequences
    python3 -c "
import re, sys, json

with open('$file', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Clean lines
clean_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]

# Find duplicate sequences
min_lines = $min_lines
duplicates = []

for i in range(len(clean_lines) - min_lines + 1):
    sequence = ''.join(clean_lines[i:i+min_lines])
    for j in range(i + min_lines, len(clean_lines) - min_lines + 1):
        compare_sequence = ''.join(clean_lines[j:j+min_lines])
        if sequence == compare_sequence:
            duplicates.append({
                'start1': i+1,  # 1-indexed line numbers
                'end1': i+min_lines,
                'start2': j+1,
                'end2': j+min_lines,
                'lines': clean_lines[i:i+min_lines]
            })

with open('$output_file', 'w') as f:
    json.dump(duplicates, f, indent=2)
" 2>/dev/null || echo "[]" > "$output_file"
}

# High-level function to compare two files
compare_files() {
    local file1="$1"
    local file2="$2"
    local method="${3:-token}"
    local threshold="${4:-0.1}"

    # Check if files exist
    if [ ! -f "$file1" ] || [ ! -f "$file2" ]; then
        echo "0.0"
        return 1
    fi

    # Skip comparing the same file
    if [ "$file1" = "$file2" ]; then
        echo "1.0"
        return 0
    fi

    # Compare files based on method
    case "$method" in
        "token")
            compare_files_tokens "$file1" "$file2" "$threshold"
            ;;
        "ast")
            compare_files_ast "$file1" "$file2" "$threshold"
            ;;
        "graph")
            compare_files_graph "$file1" "$file2" "$threshold"
            ;;
        *)
            log "ERROR" "Unknown comparison method: $method"
            echo "0.0"
            return 1
            ;;
    esac
}

# Detect patterns in a file
detect_patterns_in_file() {
    local file="$1"
    local output_file="$2"

    # Check if file exists
    if [ ! -f "$file" ]; then
        echo "{}" > "$output_file"
        return 1
    fi

    # Create a temporary Python script
    local temp_script=$(mktemp)

    # Generate Python script
    cat > "$temp_script" << 'EOF'
import re
import sys
import json

# Optimized RegEx patterns for better performance and accuracy
SECRET_REGEX = r'''(?ix)
    (api[_\-]?key|password|token|secret|credentials)   # Base identifier
    \s*=\s*                                # Assignment operator
    (["'])(?:\\\2|.)*?\2                   # Quoted value
    |
    \b[0-9a-fA-F]{32,}\b                   # Hex tokens
    |
    eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*  # JWT
'''

MOCK_REGEX = r'''(?ix)
    (mock|Mock|patch|MagicMock)\s*\(
    |@\s*(mock|patch)
    |\b(fake|dummy|stub|simulate|simulation)_\w+
    |#\s*(Test|Temporary|Mock)\s+implementation
    |TODO.*implement
    |#\s*(Stub|Placeholder)
'''

FALLBACK_REGEX = r'''(?ix)
    (try\s*:.*?except)
    |\b(fallback|backup|alternative|recovery|emergency)\b
    |if\s+(error|exception)
    |#\s*(Emergency|Workaround|Temporary fix)
    |catch\s*\(
'''

ERROR_MASKING_REGEX = r'''(?ix)
    except.*?(pass|return|None)
    |except\s*:
    |except\s*(Exception|BaseException|\*)
    |#\s*(Ignore|Silent)\s+(exceptions|fail)
    |\b(swallow|ignore|suppress)_exceptions?\b
'''

WARNING_SUPPRESSION_REGEX = r'''(?ix)
    #\s*(no[q]a|nosec|pragma:\s*no\s*cover|type:\s*ignore)
    |#\s*(pylint|flake8|mypy|pyright):\s*(disable|ignore|noqa)
    |warnings\.(filter|suppress)
    |\b(ignore|disable|suppress)_(warning|errors)\b
    |#\s*fmt:\s*off
'''

TEST_SKIPPING_REGEX = r'''(?ix)
    @(pytest\.mark\.skip|unittest\.skip|skip)
    |\b(skip[Tt]est|skip\s*=\s*True)\b
    |#\s*(Skip|Disable)\s+test
    |\b(xtest|xdescribe|xit)\s*\(
    |#\s*(Temporarily disabled|Test is flaky)
'''

def classify_match(line, match, line_number):
    """Classify a regex match into a specific issue category."""
    match_str = line[match.start():match.end()]
    result = {
        'line': line_number,
        'text': line.strip(),
        'match': match_str
    }

    if re.search(SECRET_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return ('hardcoded', result)
    elif re.search(MOCK_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return ('mocks', result)
    elif re.search(FALLBACK_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return ('fallbacks', result)
    elif re.search(ERROR_MASKING_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return ('error_masking', result)
    elif re.search(WARNING_SUPPRESSION_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return ('warning_suppression', result)
    elif re.search(TEST_SKIPPING_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return ('test_skipping', result)
    return None

def analyze_file(file_path):
    """Analyze a file for patterns."""
    issues = {
        'mocks': [],
        'fallbacks': [],
        'hardcoded': [],
        'warning_suppression': [],
        'error_masking': [],
        'test_skipping': []
    }

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Remove docstrings for cleaner analysis but keep line numbers intact
        lines = content.splitlines()
        in_docstring = False
        docstring_delimiter = None
        clean_lines = []

        for line in lines:
            # Check for docstring start/end
            if not in_docstring:
                if '"""' in line or "'''" in line:
                    delimiter = '"""' if '"""' in line else "'''"
                    if line.count(delimiter) % 2 == 1:  # Odd count, docstring starts
                        in_docstring = True
                        docstring_delimiter = delimiter
                        clean_lines.append(line.split(delimiter, 1)[0])
                        continue
            else:
                if docstring_delimiter in line:
                    in_docstring = False
                    docstring_delimiter = None
                    clean_lines.append("" if line.find(docstring_delimiter) + len(docstring_delimiter) >= len(line) else
                                      line[line.find(docstring_delimiter) + len(docstring_delimiter):])
                    continue
                else:
                    clean_lines.append("")
                    continue

            # Add line if not in docstring
            if not in_docstring:
                clean_lines.append(line)
            else:
                clean_lines.append("")

        # Compile regexes
        combined_regex = f"({SECRET_REGEX})|({MOCK_REGEX})|({FALLBACK_REGEX})|({ERROR_MASKING_REGEX})|({WARNING_SUPPRESSION_REGEX})|({TEST_SKIPPING_REGEX})"
        compiled_regex = re.compile(combined_regex, re.VERBOSE)

        # Analyze each line
        for line_number, line in enumerate(clean_lines, 1):
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Find all matches in the line
            for match in compiled_regex.finditer(line):
                result = classify_match(line, match, line_number)
                if result:
                    category, issue = result
                    issues[category].append(issue)

        # Find duplicate code blocks
        duplicate_blocks = []
        block_size = 3

        # Skip files that are too short
        if len(clean_lines) > block_size * 2:
            # Create a dictionary of code blocks
            blocks = {}
            for i in range(len(clean_lines) - block_size + 1):
                # Skip blocks with empty lines
                if any(not clean_lines[i+j].strip() for j in range(block_size)):
                    continue

                block = "\n".join(clean_lines[i:i+block_size])
                if block in blocks:
                    duplicate_blocks.append({
                        'start1': blocks[block],
                        'end1': blocks[block] + block_size - 1,
                        'start2': i + 1,
                        'end2': i + block_size,
                        'code': block
                    })
                else:
                    blocks[block] = i + 1

        # Count the number of issues found
        issue_count = sum(len(issues[category]) for category in issues)

        return {
            'path': file_path,
            'issues': issues,
            'duplicate_blocks': duplicate_blocks,
            'has_issues': issue_count > 0,
            'has_duplicates': len(duplicate_blocks) > 0,
            'issue_count': issue_count,
            'duplicate_count': len(duplicate_blocks)
        }
    except Exception as e:
        return {
            'path': file_path,
            'error': str(e),
            'issues': issues,
            'duplicate_blocks': [],
            'has_issues': False,
            'has_duplicates': False,
            'issue_count': 0,
            'duplicate_count': 0
        }

# Main logic
file_path = sys.argv[1]
output_path = sys.argv[2]

result = analyze_file(file_path)
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)
EOF

    # Run the script
    python3 "$temp_script" "$file" "$output_file"

    # Clean up
    rm -f "$temp_script"

    # Return success if output file exists
    if [ -f "$output_file" ]; then
        return 0
    else
        echo "{}" > "$output_file"
        return 1
    fi
}

# Export functions for use in other modules
export -f compare_files
export -f detect_patterns_in_file
export -f find_duplicate_lines
