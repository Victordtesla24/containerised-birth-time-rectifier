#!/bin/bash
#
# Hybrid code duplication detection module combining multiple techniques
#

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# Generate Python script for hybrid detection
generate_hybrid_detector_script() {
    cat << 'EOF'
import ast
import sys
import os
import json
import hashlib
import re
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import traceback
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
import time

# =============================
# File Hashing Layer
# =============================

def generate_file_signatures(file_paths, hash_method='sha256'):
    """Generate hash signatures for files (Phase 1)."""
    signatures = defaultdict(list)

    for file_path in file_paths:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                if hash_method == 'sha256':
                    file_hash = hashlib.sha256(content).hexdigest()
                else:
                    file_hash = hashlib.md5(content).hexdigest()
                signatures[file_hash].append(file_path)
        except IOError as e:
            print(f"Error reading {file_path}: {str(e)}", file=sys.stderr)
            continue

    # Return only duplicate files
    return {k: v for k, v in signatures.items() if len(v) > 1}

# =============================
# AST-based Analysis
# =============================

class ASTCache:
    """Cache for parsed ASTs to avoid re-parsing."""
    def __init__(self, max_size=1000):
        self.cache = {}
        self.max_size = max_size

    def get(self, file_path):
        return self.cache.get(file_path)

    def put(self, file_path, ast_tree):
        if len(self.cache) >= self.max_size:
            # Simple LRU: just clear half the cache when it gets full
            # For production would use a proper LRU implementation
            to_remove = list(self.cache.keys())[:self.max_size//2]
            for key in to_remove:
                del self.cache[key]
        self.cache[file_path] = ast_tree

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

class ASTAnalyzer:
    """Enhanced AST analyzer with anti-unification capabilities."""

    def __init__(self):
        self.cache = ASTCache()

    def parse_file(self, file_path):
        """Parse file into AST with caching."""
        cached = self.cache.get(file_path)
        if cached:
            return cached

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tree = ast.parse(content)
            self.cache.put(file_path, tree)
            return tree
        except Exception as e:
            print(f"Error parsing {file_path}: {str(e)}", file=sys.stderr)
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

    def get_node_structure(self, node):
        """Get structure signature of a node, ignoring variable names and literals."""
        if not node:
            return ""

        # Create a normalized copy of the node
        normalizer = NodeNormalizer()
        normalized_node = normalizer.visit(ast.copy_module(node))

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

    def compare_ast_files(self, file1, file2, threshold=0.7):
        """Compare two files using AST analysis (Phase 2)."""
        tree1 = self.parse_file(file1)
        tree2 = self.parse_file(file2)

        if not tree1 or not tree2:
            return 0.0

        # Compare functions
        functions1 = self.get_function_nodes(tree1)
        functions2 = self.get_function_nodes(tree2)

        func_similarities = []
        for f1 in functions1:
            for f2 in functions2:
                # Skip comparing very small functions (less than 3 statements)
                if len(f1.body) < 3 or len(f2.body) < 3:
                    continue

                similarity = self.compare_nodes(f1, f2)
                if similarity > threshold:
                    func_similarities.append({
                        'function1': f1.name,
                        'function2': f2.name,
                        'similarity': similarity
                    })

        # Compare classes
        classes1 = self.get_class_nodes(tree1)
        classes2 = self.get_class_nodes(tree2)

        class_similarities = []
        for c1 in classes1:
            for c2 in classes2:
                similarity = self.compare_nodes(c1, c2)
                if similarity > threshold:
                    class_similarities.append({
                        'class1': c1.name,
                        'class2': c2.name,
                        'similarity': similarity
                    })

        # Calculate combined similarity score
        if func_similarities:
            func_score = max(item['similarity'] for item in func_similarities)
        else:
            func_score = 0.0

        if class_similarities:
            class_score = max(item['similarity'] for item in class_similarities)
        else:
            class_score = 0.0

        # Combined score with weights
        if func_similarities or class_similarities:
            return 0.7 * func_score + 0.3 * class_score
        else:
            return 0.0

# =============================
# Control Flow Analysis
# =============================

def analyze_control_flow(ast_node):
    """Analyze control flow structure of code (Phase 3)."""
    flow_map = []
    for node in ast.walk(ast_node):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
            flow_map.append(type(node).__name__)
        elif isinstance(node, ast.FunctionDef):
            flow_map.append(f'FUNC:{node.name}')
    return hashlib.sha256(''.join(flow_map).encode()).hexdigest()

def compare_control_flow(file1, file2, ast_analyzer):
    """Compare control flow between two files."""
    tree1 = ast_analyzer.parse_file(file1)
    tree2 = ast_analyzer.parse_file(file2)

    if not tree1 or not tree2:
        return 0.0

    flow1 = analyze_control_flow(tree1)
    flow2 = analyze_control_flow(tree2)

    # Direct hash comparison
    if flow1 == flow2:
        return 1.0

    # Get individual function flows
    functions1 = ast_analyzer.get_function_nodes(tree1)
    functions2 = ast_analyzer.get_function_nodes(tree2)

    # Compare function control flows
    flow_similarities = []
    for f1 in functions1:
        for f2 in functions2:
            # Skip small functions
            if len(f1.body) < 3 or len(f2.body) < 3:
                continue

            f1_flow = analyze_control_flow(f1)
            f2_flow = analyze_control_flow(f2)

            if f1_flow == f2_flow:
                flow_similarities.append(1.0)

    # Return max similarity if any found
    if flow_similarities:
        return max(flow_similarities)

    return 0.0

# =============================
# Combined Analysis
# =============================

def analyze_files(file_paths, threshold=0.7, max_workers=4):
    """Multi-phase analysis of duplicate code."""
    start_time = time.time()

    results = {
        'similar_pairs': [],
        'exact_duplicates': [],
        'structural_duplicates': [],
        'functional_duplicates': [],
        'file_count': len(file_paths),
        'processing_time': 0
    }

    # Phase 1: Rapid Hashing Layer
    print(f"Phase 1: Hashing {len(file_paths)} files...", file=sys.stderr)
    exact_matches = generate_file_signatures(file_paths)

    # Record exact duplicates
    for hash_val, paths in exact_matches.items():
        for path1, path2 in combinations(paths, 2):
            results['exact_duplicates'].append({
                'file1': path1,
                'file2': path2,
                'similarity': 1.0,
                'detection_method': 'hash'
            })
            # Also add to overall similar pairs
            results['similar_pairs'].append({
                'file1': path1,
                'file2': path2,
                'similarity': 1.0,
                'detection_method': 'hash'
            })

    # Create file pairs for next phases, excluding exact matches
    file_pairs = []
    exact_match_files = set()
    for paths in exact_matches.values():
        exact_match_files.update(paths)

    for i, file1 in enumerate(file_paths):
        for file2 in file_paths[i+1:]:
            # Skip if either file is an exact match with something else
            if file1 in exact_match_files and file2 in exact_match_files:
                continue
            file_pairs.append((file1, file2))

    # Limit number of comparisons if there are too many
    max_comparisons = 10000
    if len(file_pairs) > max_comparisons:
        print(f"Limiting comparisons to {max_comparisons} pairs", file=sys.stderr)
        import random
        random.shuffle(file_pairs)
        file_pairs = file_pairs[:max_comparisons]

    # Initialize AST analyzer
    ast_analyzer = ASTAnalyzer()

    # Phase 2 & 3: AST Pattern Matching and Control Flow Analysis
    print(f"Phases 2-3: Analyzing {len(file_pairs)} file pairs...", file=sys.stderr)

    def analyze_pair(pair):
        """Analyze a single file pair with both AST and control flow."""
        file1, file2 = pair

        # Skip comparing the same file
        if file1 == file2:
            return None

        # Phase 2: AST Pattern Matching
        ast_similarity = ast_analyzer.compare_ast_files(file1, file2, threshold)

        # Only proceed to Phase 3 if Phase 2 finds potential matches
        if ast_similarity >= threshold * 0.8:  # Use slightly lower threshold for phase 2->3
            # Phase 3: Control Flow Analysis
            flow_similarity = compare_control_flow(file1, file2, ast_analyzer)

            # Weighted combination
            combined_similarity = 0.7 * ast_similarity + 0.3 * flow_similarity

            if combined_similarity >= threshold:
                # Determine the primary detection method
                detection_method = 'ast' if ast_similarity > flow_similarity else 'control_flow'

                # Add to appropriate category
                result = {
                    'file1': file1,
                    'file2': file2,
                    'similarity': combined_similarity,
                    'ast_similarity': ast_similarity,
                    'flow_similarity': flow_similarity,
                    'detection_method': detection_method
                }

                if ast_similarity >= threshold:
                    # Also a structural duplicate
                    return ('structural', result)
                elif flow_similarity >= threshold:
                    # Functional duplicate
                    return ('functional', result)
                else:
                    # Combined similarity only
                    return ('combined', result)

        return None

    # Process file pairs in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_results = list(executor.map(analyze_pair, file_pairs))

    # Process results
    for result in future_results:
        if not result:
            continue

        category, data = result

        # Always add to overall similar pairs
        results['similar_pairs'].append(data)

        # Add to specific category
        if category == 'structural':
            results['structural_duplicates'].append(data)
        elif category == 'functional':
            results['functional_duplicates'].append(data)

    # Calculate processing time
    results['processing_time'] = time.time() - start_time

    return results

# =============================
# Main Execution
# =============================

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python hybrid_detector.py <threshold> <file1> <file2> ...", file=sys.stderr)
        sys.exit(1)

    threshold = float(sys.argv[1])
    file_paths = sys.argv[2:]
    max_workers = int(os.environ.get('MAX_WORKERS', '4'))

    # Run the analysis
    result = analyze_files(file_paths, threshold, max_workers)

    # Output results
    print(json.dumps(result, indent=2))
EOF
}

# Run hybrid analysis on directories
run_hybrid_analysis() {
    local threshold="${1:-0.7}"
    shift
    local directories=("$@")
    local output_file=$(mktemp)

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Running hybrid code duplication analysis on ${#directories[@]} directories with threshold $threshold"
    fi

    # Get all Python files
    local files=()
    for dir in "${directories[@]}"; do
        mapfile -t dir_files < <(find "$dir" -type f -name "*.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/node_modules/*")
        for file in "${dir_files[@]}"; do
            # Check file size
            if [ -f "$file" ] && [ "$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)" -le "$MAX_FILESIZE" ]; then
                files+=("$file")
            fi
        done
    done

    if [ "${#files[@]}" -eq 0 ]; then
        log "WARN" "No Python files found in the specified directories"
        echo '{"similar_pairs":[],"file_count":0,"processing_time":0}' > "$output_file"
        cat "$output_file"
        rm -f "$output_file"
        return 0
    fi

    if [ "$VERBOSE" = true ]; then
        log "INFO" "Found ${#files[@]} Python files to analyze"
    fi

    # Limit the number of files if needed
    if [ "${#files[@]}" -gt "$MAX_FILES_TO_COMPARE" ]; then
        log "WARN" "Limiting analysis to $MAX_FILES_TO_COMPARE files"
        files=("${files[@]:0:$MAX_FILES_TO_COMPARE}")
    fi

    # Create temporary script file
    local script_file=$(mktemp)
    generate_hybrid_detector_script > "$script_file"

    # Run the hybrid analysis with proper parallelism
    export MAX_WORKERS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    local files_str=$(printf "\"%s\" " "${files[@]}")

    # Run with timeout
    if ! run_with_timeout "$ANALYSIS_TIMEOUT" "python3 \"$script_file\" $threshold $files_str > \"$output_file\""; then
        log "ERROR" "Hybrid analysis timed out after $ANALYSIS_TIMEOUT seconds"
        echo '{"similar_pairs":[],"file_count":0,"processing_time":0,"error":"timeout"}' > "$output_file"
    fi

    # Check if output was generated
    if [ ! -s "$output_file" ]; then
        log "ERROR" "Hybrid analysis did not produce any output"
        echo '{"similar_pairs":[],"file_count":0,"processing_time":0,"error":"no_output"}' > "$output_file"
    elif [ "$VERBOSE" = true ]; then
        log "INFO" "Hybrid analysis completed successfully"
    fi

    # Return the results
    cat "$output_file"

    # Clean up
    rm -f "$script_file" "$output_file"
    return 0
}

# Export functions
export -f generate_hybrid_detector_script
export -f run_hybrid_analysis
