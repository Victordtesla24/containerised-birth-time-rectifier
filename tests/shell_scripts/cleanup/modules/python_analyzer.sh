#!/bin/bash
#
# Python code analysis module
#

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# Setup Python virtual environment
setup_python_env() {
    local timeout=60  # 60 seconds max for environment setup

    # Skip if environment already exists and has required packages
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        if [ "$VERBOSE" = true ]; then
            log "INFO" "Using existing Python virtual environment"
        fi
        source "$VENV_DIR/bin/activate" 2>/dev/null || {
            log "ERROR" "Failed to activate existing environment"
            return 1
        }
        return 0
    fi

    # Create a virtual environment with timeout
    run_with_timeout $timeout "python3 -m venv \"$VENV_DIR\" || python -m venv \"$VENV_DIR\"" || {
        log "ERROR" "Failed to create Python virtual environment"
        return 1
    }

    # Activate the virtual environment
    source "$VENV_DIR/bin/activate" 2>/dev/null || {
        log "ERROR" "Failed to activate Python virtual environment"
        return 1
    }

    # Install required packages with timeout
    for package in "${REQUIRED_PACKAGES[@]}"; do
        run_with_timeout 30 "pip install --quiet \"$package\"" || {
            log "ERROR" "Failed to install $package"
            return 1
        }
    done

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Python environment setup completed successfully"
    fi

    return 0
}

# Python script for enhanced code analysis
generate_python_script() {
    cat << 'EOF'
import ast
import json
import os
import sys
import re
import traceback
import hashlib
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple, Any, Optional
import concurrent.futures

# Set performance limits from environment
MAX_FILESIZE = int(os.environ.get('MAX_FILESIZE', '200000'))
MAX_FILES_TO_COMPARE = int(os.environ.get('MAX_FILES_TO_COMPARE', '500'))
SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', '0.3'))
VERBOSE = os.environ.get('VERBOSE', 'false').lower() == 'true'
SKIP_DIRS = ['node_modules', 'venv', '.venv', '.git', 'migrations', 'logs', '.vscode', '.cursor', '.devcontainer', 'pycache', '__pycache__', 'public', 'media', 'reports', 'mcp-servers', 'clinrules', 'chrome-extension', 'dist', 'build', 'bundles', 'coverage', 'examples', 'tests', 'tmp', 'cache', 'backup', 'old', 'temp', 'trash', 'junk', 'unused', 'deprecated', 'archive', 'old', 'temp', 'trash', 'junk', 'unused', 'deprecated', 'archive', 'old', 'temp', 'trash', 'junk', 'unused', 'deprecated', 'archive', 'cline_docs', 'git', 'eslint', 'eslint-cache', 'eslint-temp', 'eslint-temp-cache', 'eslint-temp-cache-v2', 'eslint-temp-cache-v3', 'eslint-temp-cache-v4', 'eslint-temp-cache-v5', 'eslint-temp-cache-v6', 'eslint-temp-cache-v7', 'eslint-temp-cache-v8', 'eslint-temp-cache-v9', 'eslint-temp-cache-v10', 'ephemeris', 'env']
MODULE_MAPPING = os.environ.get('MODULE_MAPPING', '')
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))

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

# Combined regex for faster initial scanning
COMBINED_REGEX = f"({SECRET_REGEX})|({MOCK_REGEX})|({FALLBACK_REGEX})|({ERROR_MASKING_REGEX})|({WARNING_SUPPRESSION_REGEX})|({TEST_SKIPPING_REGEX})"
compiled_regex = re.compile(COMBINED_REGEX, re.VERBOSE)

def debug_print(message):
    """Print debug message if verbose mode is enabled."""
    if VERBOSE:
        print(f"DEBUG: {message}", file=sys.stderr)

# Cache for parsed ASTs to avoid re-parsing
ast_cache = {}

class ASTAnalyzer:
    """Enhanced AST analyzer with anti-unification capabilities."""

    def __init__(self):
        self.cache = {}

    def parse_file(self, file_path):
        """Parse file into AST with caching."""
        if file_path in self.cache:
            return self.cache[file_path]

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tree = ast.parse(content)
            self.cache[file_path] = tree
            return tree
        except Exception as e:
            debug_print(f"Error parsing {file_path}: {str(e)}")
            return None

    def get_function_nodes(self, tree):
        """Extract function nodes from AST."""
        if not tree:
            return []
        return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    def get_class_nodes(self, tree):
        """Extract class nodes from AST."""
        if not tree:
            return []
        return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    def normalize_node(self, node):
        """Normalize a node by removing variable names and literals."""
        if isinstance(node, ast.Name):
            return ast.Name(id='VAR', ctx=node.ctx)
        elif isinstance(node, ast.Str):
            return ast.Str(s='STRING')
        elif isinstance(node, ast.Num):
            return ast.Num(n=0)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
            return ast.Constant(value=type(node.value)())
        return node

    def get_node_structure(self, node):
        """Get structure signature of a node, ignoring variable names and literals."""
        if not node:
            return ""

        # Create a normalized copy of the node
        normalizer = NodeNormalizer()
        normalized_node = normalizer.visit(node)

        # Get the hash of the normalized node
        return self.hash_node(normalized_node)

    def hash_node(self, node):
        """Create a hash of a node based on its structure."""
        node_type = type(node).__name__
        if isinstance(node, ast.AST):
            fields = []
            for field, value in ast.iter_fields(node):
                if field in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset', 'ctx'):
                    continue
                if isinstance(value, list):
                    field_hash = ''.join(self.hash_node(item) for item in value)
                else:
                    field_hash = self.hash_node(value)
                fields.append(f"{field}:{field_hash}")
            return f"{node_type}({','.join(fields)})"
        elif isinstance(node, list):
            return '[' + ','.join(self.hash_node(item) for item in node) + ']'
        return str(node)

    def compare_nodes(self, node1, node2):
        """Compare two AST nodes for structural similarity."""
        hash1 = self.get_node_structure(node1)
        hash2 = self.get_node_structure(node2)

        # If structures are identical
        if hash1 == hash2:
            return 1.0

        # Otherwise use sequence matcher on the structural hashes
        return SequenceMatcher(None, hash1, hash2).ratio()

    def find_similar_functions(self, file1, file2):
        """Find similar functions between two files."""
        tree1 = self.parse_file(file1)
        tree2 = self.parse_file(file2)

        if not tree1 or not tree2:
            return []

        functions1 = self.get_function_nodes(tree1)
        functions2 = self.get_function_nodes(tree2)

        similar_pairs = []

        for f1 in functions1:
            for f2 in functions2:
                # Skip comparing very small functions (less than 3 statements)
                if len(f1.body) < 3 or len(f2.body) < 3:
                    continue

                similarity = self.compare_nodes(f1, f2)

                if similarity > SIMILARITY_THRESHOLD:
                    similar_pairs.append({
                        'file1': file1,
                        'file2': file2,
                        'function1': f1.name,
                        'function2': f2.name,
                        'line1': f1.lineno,
                        'line2': f2.lineno,
                        'similarity': similarity
                    })

        return similar_pairs

class NodeNormalizer(ast.NodeTransformer):
    """Normalizes AST nodes by replacing variable names and literals."""

    def visit_Name(self, node):
        """Normalize variable names."""
        node.id = 'VAR'
        return node

    def visit_Str(self, node):
        """Normalize string literals."""
        return ast.Str(s='STRING')

    def visit_Num(self, node):
        """Normalize numeric literals."""
        return ast.Num(n=0)

    def visit_Constant(self, node):
        """Normalize constants (Python 3.8+)."""
        if isinstance(node.value, (str, int, float, bool)):
            return ast.Constant(value=type(node.value)())
        return node

def load_module_mapping():
    """Load module mapping from file if available."""
    if not MODULE_MAPPING:
        return None

    try:
        with open(MODULE_MAPPING, 'r') as f:
            return json.load(f)
    except Exception as e:
        debug_print(f"Error loading module mapping: {e}")
        return None

# Load module mapping if available
module_mapping = load_module_mapping()

def get_module_similarity(file1, file2):
    """Calculate similarity based on module structure."""
    if not module_mapping:
        return 0.0

    # Extract relative paths
    for base_dir, mapping in module_mapping.items():
        if file1.startswith(base_dir) and file2.startswith(base_dir):
            rel_path1 = os.path.relpath(file1, base_dir)
            rel_path2 = os.path.relpath(file2, base_dir)

            module1 = os.path.splitext(rel_path1)[0].replace('/', '.')
            module2 = os.path.splitext(rel_path2)[0].replace('/', '.')

            modules = mapping.get('modules', {})

            if module1 in modules and module2 in modules:
                # Compare imports
                imports1 = set(modules[module1].get('imports', []))
                imports2 = set(modules[module2].get('imports', []))

                # Compare classes
                classes1 = set(modules[module1].get('classes', []))
                classes2 = set(modules[module2].get('classes', []))

                # Compare functions
                funcs1 = set(modules[module1].get('functions', []))
                funcs2 = set(modules[module2].get('functions', []))

                # Calculate Jaccard similarity for each
                def jaccard(s1, s2):
                    if not s1 and not s2:
                        return 0.0
                    intersection = len(s1.intersection(s2))
                    union = len(s1.union(s2))
                    return intersection / union if union > 0 else 0.0

                # Weighted average
                weights = [0.4, 0.3, 0.3]  # imports, classes, functions
                scores = [
                    jaccard(imports1, imports2),
                    jaccard(classes1, classes2),
                    jaccard(funcs1, funcs2)
                ]

                return sum(w * s for w, s in zip(weights, scores))

    return 0.0

def should_skip_directory(path):
    """Check if directory should be skipped."""
    for pattern in SKIP_DIRS:
        if pattern in path:
            debug_print(f"Skipping directory: {path}")
            return True
    return False

def get_python_files(directory):
    """Get all Python files recursively from directory."""
    debug_print(f"Scanning directory: {directory}")
    python_files = []

    for root, _, files in os.walk(directory):
        if should_skip_directory(root):
            continue

        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)

                # Skip large files
                try:
                    file_size = os.path.getsize(full_path)
                    if file_size > MAX_FILESIZE:
                        debug_print(f"Skipping large file: {full_path} ({file_size} bytes)")
                        continue
                except OSError:
                    continue

                python_files.append(full_path)
                debug_print(f"Found Python file: {full_path}")

    return python_files[:MAX_FILES_TO_COMPARE] if len(python_files) > MAX_FILES_TO_COMPARE else python_files

def read_file(file_path):
    """Read file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except:
            return ""
    except:
        return ""

def analyze_control_flow(ast_node):
    """Analyze control flow structure of code for more accurate clone detection."""
    flow_map = []
    for node in ast.walk(ast_node):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
            flow_map.append(type(node).__name__)
        elif isinstance(node, ast.FunctionDef):
            flow_map.append(f'FUNC:{node.name}')
    return hashlib.sha256(''.join(flow_map).encode()).hexdigest()

def classify_match(line, match):
    """Classify a regex match into a specific issue category."""
    match_str = line[match.start():match.end()]
    if re.search(SECRET_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return 'hardcoded'
    elif re.search(MOCK_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return 'mocks'
    elif re.search(FALLBACK_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return 'fallbacks'
    elif re.search(ERROR_MASKING_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return 'error_masking'
    elif re.search(WARNING_SUPPRESSION_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return 'warning_suppression'
    elif re.search(TEST_SKIPPING_REGEX, match_str, re.VERBOSE | re.IGNORECASE):
        return 'test_skipping'
    return None

def find_patterns_optimized(content):
    """Find all patterns in content using optimized regex approach."""
    issues = defaultdict(list)
    line_number = 1

    # Remove docstrings and block comments for cleaner analysis
    content_no_docstrings = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', '', content, flags=re.DOTALL)

    for line in content_no_docstrings.splitlines():
        # Skip empty or comment-only lines
        if not line.strip() or line.strip().startswith('#'):
            line_number += 1
            continue

        # Find all matches in the line
        for match in compiled_regex.finditer(line):
            category = classify_match(line, match)
            if category:
                issues[category].append(f"Line {line_number}: {line.strip()}")

        line_number += 1

    return issues

def analyze_file(file_path):
    """Analyze a single file for issues."""
    content = read_file(file_path)
    if not content:
        return None

    # Find all patterns using optimized approach
    issues = find_patterns_optimized(content)

    try:
        # Parse AST for more advanced analysis
        tree = ast.parse(content)
        ast_cache[file_path] = tree

        # Find duplicate imports
        duplicates = find_duplicate_imports(tree)
        if duplicates:
            issues['duplicates'] = [f"Duplicate import: {d['import']} at lines {', '.join(map(str, d['lines']))}" for d in duplicates]

        # Find similar functions within the file
        similar_functions = find_similar_functions_in_file(tree, file_path)
    except Exception as e:
        debug_print(f"AST analysis error for {file_path}: {e}")
        similar_functions = []

    return {
        'path': file_path,
        'issues': issues,
        'similar_functions': similar_functions,
        'has_issues': any(len(issues[k]) > 0 for k in issues),
        'has_similar_functions': len(similar_functions) > 0
    }

def find_duplicate_imports(tree):
    """Find duplicate import statements in AST."""
    imports = defaultdict(list)
    duplicates = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports[name.name].append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for name in node.names:
                    import_name = f"{node.module}.{name.name}"
                    imports[import_name].append(node.lineno)

    for import_name, lines in imports.items():
        if len(lines) > 1:
            duplicates.append({
                'import': import_name,
                'lines': lines,
                'count': len(lines)
            })

    return duplicates

def find_similar_functions_in_file(tree, file_path):
    """Find similar functions within a single file using AST."""
    similar_functions = []

    # Extract all function definitions
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node)

    # Compare each function against others
    ast_analyzer = ASTAnalyzer()
    for i, func1 in enumerate(functions):
        for func2 in functions[i+1:]:
            # Skip small functions
            if len(func1.body) < 3 or len(func2.body) < 3:
                continue

            # Calculate structural similarity
            similarity = ast_analyzer.compare_nodes(func1, func2)

            if similarity > SIMILARITY_THRESHOLD:
                similar_functions.append({
                    'func1': func1.name,
                    'func2': func2.name,
                    'lineno1': func1.lineno,
                    'lineno2': func2.lineno,
                    'similarity': similarity
                })

    return similar_functions

def compare_files(file1, file2):
    """Compare two files for similarity using multiple techniques."""
    # Initialize AST analyzer
    ast_analyzer = ASTAnalyzer()

    # Calculate various similarity metrics

    # 1. Text similarity (20%)
    content1 = read_file(file1)
    content2 = read_file(file2)
    if not content1 or not content2:
        return 0.0
    text_similarity = SequenceMatcher(None, content1, content2).ratio()

    # 2. AST-based structural similarity (40%)
    try:
        ast_similarity = 0.0
        similar_functions = ast_analyzer.find_similar_functions(file1, file2)
        if similar_functions:
            ast_similarity = max(item['similarity'] for item in similar_functions)
    except Exception as e:
        debug_print(f"AST comparison error: {e}")
        ast_similarity = 0.0

    # 3. Control flow similarity (20%)
    try:
        tree1 = ast_analyzer.parse_file(file1)
        tree2 = ast_analyzer.parse_file(file2)

        if tree1 and tree2:
            flow1 = analyze_control_flow(tree1)
            flow2 = analyze_control_flow(tree2)

            # Compare control flow hashes
            flow_similarity = 1.0 if flow1 == flow2 else 0.0
        else:
            flow_similarity = 0.0
    except Exception as e:
        debug_print(f"Control flow analysis error: {e}")
        flow_similarity = 0.0

    # 4. Module structure similarity (20%)
    module_similarity = get_module_similarity(file1, file2)

    # Weight and combine the scores
    weights = [0.2, 0.4, 0.2, 0.2]
    scores = [text_similarity, ast_similarity, flow_similarity, module_similarity]

    combined_similarity = sum(w * s for w, s in zip(weights, scores))

    return combined_similarity

def process_file(file_path):
    """Process a single file for analysis."""
    return analyze_file(file_path)

def analyze_directories(directories):
    """Main analysis function."""
    try:
        all_files = []
        for directory in directories:
            files = get_python_files(directory)
            all_files.extend(files)
            debug_print(f"Found {len(files)} Python files in {directory}")

        debug_print(f"Total files to analyze: {len(all_files)}")

        # Process files in parallel for better performance
        file_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            file_results = list(executor.map(process_file, all_files))

        # Filter out None results
        file_results = [r for r in file_results if r is not None]

        # Find similar file pairs
        similar_pairs = []

        # Process file comparisons in parallel
        total_comparisons = len(all_files) * (len(all_files) - 1) // 2
        debug_print(f"Analyzing {total_comparisons} potential file comparisons")

        # Use a more efficient approach for file comparison
        file_pairs = []
        for i, file1 in enumerate(all_files):
            for j, file2 in enumerate(all_files):
                if i < j:  # Only compare each pair once
                    file_pairs.append((file1, file2))

        # Limit the number of comparisons if there are too many
        if len(file_pairs) > 10000:
            debug_print(f"Too many file pairs ({len(file_pairs)}), limiting to 10000")
            file_pairs = file_pairs[:10000]

        # Process comparisons in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            similarity_results = []
            for file1, file2 in file_pairs:
                similarity_results.append(executor.submit(compare_files, file1, file2))

            # Collect results
            for i, future in enumerate(concurrent.futures.as_completed(similarity_results)):
                similarity = future.result()
                if similarity >= SIMILARITY_THRESHOLD:
                    file1, file2 = file_pairs[i]
                    similar_pairs.append({
                        "file1": file1,
                        "file2": file2,
                        "similarity": similarity
                    })

        debug_print(f"Found {len(similar_pairs)} similar file pairs")

        # Extract files with issues
        files_with_issues = [
            {
                "path": result["path"],
                "issues": result["issues"],
                "similar_functions": result.get("similar_functions", [])
            }
            for result in file_results if result.get("has_issues") or result.get("has_similar_functions")
        ]

        return {
            "status": "success",
            "file_count": len(all_files),
            "similar_pairs": similar_pairs,
            "files_with_issues": files_with_issues
        }

    except Exception as e:
        debug_print(f"Error in analyze_directories: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "file_count": 0,
            "similar_pairs": [],
            "files_with_issues": []
        }

if __name__ == '__main__':
    try:
        directories = sys.argv[1:]
        debug_print(f"Starting analysis with directories: {directories}")
        result = analyze_directories(directories)
        print(json.dumps(result))
    except Exception as e:
        debug_print(f"Fatal error: {traceback.format_exc()}")
        error_result = {
            'status': 'error',
            'message': str(e),
            'file_count': 0,
            'similar_pairs': [],
            'files_with_issues': []
        }
        print(json.dumps(error_result))
EOF
}

# Run Python analysis with proper error handling and timeout
run_python_analysis() {
    local timeout="${ANALYSIS_TIMEOUT:-600}"
    local directories_str=$(printf "%s " "${DIRECTORIES[@]}")

    # Define a Python script that includes timeout handling
    local py_script=$(mktemp)

    # Create a Python script with built-in timeout
    generate_python_script > "$py_script"

    # Run the Python script with a timeout
    run_with_timeout $timeout "python3 $py_script $directories_str" || {
        log "ERROR" "Python analysis timed out or failed"
        # Create fallback empty JSON result
        echo '{"status": "error", "message": "Analysis timed out", "similar_pairs": [], "files_with_issues": []}'
        rm -f "$py_script" 2>/dev/null || true
        return 1
    }

    # Clean up
    rm -f "$py_script" 2>/dev/null || true
    return 0
}

# Export functions
export -f setup_python_env
export -f generate_python_script
export -f run_python_analysis
