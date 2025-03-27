#!/bin/bash
#
# Advanced AST analysis module for code duplication detection
#

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# Generate Python script for advanced AST analysis
generate_ast_analyzer_script() {
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

class NodeVisitor(ast.NodeVisitor):
    """Base visitor that tracks visited nodes"""

    def __init__(self):
        self.visited = []

    def generic_visit(self, node):
        self.visited.append(node)
        super().generic_visit(node)

class StructureVisitor(NodeVisitor):
    """Visitor that extracts structural patterns from AST"""

    def __init__(self):
        super().__init__()
        self.structures = []
        self.current_structure = []
        self.in_function = False

    def visit_FunctionDef(self, node):
        old_in_function = self.in_function
        old_structure = self.current_structure

        self.in_function = True
        self.current_structure = []

        # Visit child nodes
        self.generic_visit(node)

        # Store function structure
        self.structures.append({
            'name': node.name,
            'line': node.lineno,
            'structure': self.current_structure.copy(),
            'args': len(node.args.args) if hasattr(node, 'args') else 0
        })

        # Restore previous state
        self.in_function = old_in_function
        self.current_structure = old_structure

    def visit_If(self, node):
        if self.in_function:
            self.current_structure.append('If')
        self.generic_visit(node)

    def visit_For(self, node):
        if self.in_function:
            self.current_structure.append('For')
        self.generic_visit(node)

    def visit_While(self, node):
        if self.in_function:
            self.current_structure.append('While')
        self.generic_visit(node)

    def visit_With(self, node):
        if self.in_function:
            self.current_structure.append('With')
        self.generic_visit(node)

    def visit_Try(self, node):
        if self.in_function:
            self.current_structure.append('Try')
        self.generic_visit(node)

    def visit_Raise(self, node):
        if self.in_function:
            self.current_structure.append('Raise')
        self.generic_visit(node)

    def visit_Return(self, node):
        if self.in_function:
            self.current_structure.append('Return')
        self.generic_visit(node)

class TypeCounter(NodeVisitor):
    """Visitor that counts node types in AST"""

    def __init__(self):
        super().__init__()
        self.counts = Counter()

    def generic_visit(self, node):
        self.counts[type(node).__name__] += 1
        super().generic_visit(node)

class AntiUnificationVisitor(ast.NodeVisitor):
    """Visitor that implements anti-unification algorithm for code pattern detection"""

    def __init__(self):
        self.patterns = []
        self.variable_map = {}
        self.next_var_id = 0

    def get_template_variable(self, original_name):
        """Get a template variable to abstract concrete values"""
        if original_name not in self.variable_map:
            self.variable_map[original_name] = f"VAR_{self.next_var_id}"
            self.next_var_id += 1
        return self.variable_map[original_name]

    def visit_Name(self, node):
        """Replace concrete variable names with template variables"""
        return ast.Name(
            id=self.get_template_variable(node.id),
            ctx=node.ctx
        )

    def visit_Constant(self, node):
        """Replace concrete literals with abstract values"""
        if isinstance(node.value, (int, float)):
            return ast.Constant(value=0)
        elif isinstance(node.value, str):
            return ast.Constant(value="STRING")
        elif isinstance(node.value, bool):
            return ast.Constant(value=False)
        elif node.value is None:
            return ast.Constant(value=None)
        return node

    def visit_Num(self, node):
        """Legacy handler for numeric literals"""
        return ast.Num(n=0)

    def visit_Str(self, node):
        """Legacy handler for string literals"""
        return ast.Str(s="STRING")

    def anti_unify(self, node1, node2):
        """Apply anti-unification to extract common pattern from two AST nodes"""
        if type(node1) != type(node2):
            return None

        # Reset state for each anti-unification operation
        self.variable_map = {}
        self.next_var_id = 0

        try:
            # Create copies to avoid modifying original nodes
            node1_copy = ast.parse(ast.unparse(node1))
            node2_copy = ast.parse(ast.unparse(node2))

            # Apply transformation to both nodes
            unified_node1 = self.visit(node1_copy)

            # Reset variable mapping for second node
            old_map = self.variable_map.copy()
            self.variable_map = {}

            unified_node2 = self.visit(node2_copy)

            # Compare the unified ASTs
            # If they are structurally similar, return the pattern
            node1_str = ast.unparse(unified_node1)
            node2_str = ast.unparse(unified_node2)

            similarity = SequenceMatcher(None, node1_str, node2_str).ratio()

            if similarity > 0.8:  # High structural similarity
                return {
                    'pattern': node1_str,
                    'similarity': similarity,
                    'var_mapping': old_map
                }

            return None
        except Exception as e:
            print(f"Anti-unification error: {e}", file=sys.stderr)
            return None

def normalize_code(code):
    """Normalize code by removing comments, whitespace, and string literals"""
    # Remove docstrings
    code = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', '', code, flags=re.DOTALL)
    # Remove comments
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    # Normalize whitespace
    code = re.sub(r'\s+', ' ', code)
    # Remove string literals
    code = re.sub(r'[\'\"].*?[\'\"]', '"STRING"', code)
    # Remove numeric literals
    code = re.sub(r'\b\d+\b', 'NUMBER', code)
    return code

def get_ast_structure(file_path):
    """Extract AST structure from a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        # Normalize code to ignore formatting differences
        normalized_code = normalize_code(code)

        # Parse AST
        tree = ast.parse(normalized_code)

        # Extract structured information
        structure_visitor = StructureVisitor()
        structure_visitor.visit(tree)

        # Count node types
        counter = TypeCounter()
        counter.visit(tree)

        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for name in node.names:
                        imports.append(f'{node.module}.{name.name}')

        return {
            'file': file_path,
            'functions': structure_visitor.structures,
            'node_types': dict(counter.counts),
            'imports': imports,
            'tree': tree  # Include parsed AST for further analysis
        }
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {
            'file': file_path,
            'error': str(e),
            'functions': [],
            'node_types': {},
            'imports': []
        }

def structure_similarity(func1, func2):
    """Calculate similarity between two function structures"""
    structure1 = func1.get('structure', [])
    structure2 = func2.get('structure', [])

    # If both structures are empty, they're considered similar
    if not structure1 and not structure2:
        return 1.0

    # If one is empty but the other isn't, they're different
    if not structure1 or not structure2:
        return 0.0

    # Encode structures to strings for comparison
    str1 = '-'.join(structure1)
    str2 = '-'.join(structure2)

    # Use sequence matcher to find similarity
    return SequenceMatcher(None, str1, str2).ratio()

def function_signature_similarity(func1, func2):
    """Calculate similarity between two function signatures"""
    # Compare function names (exact match gives bonus)
    name_similarity = 1.0 if func1.get('name') == func2.get('name') else 0.0

    # Compare argument counts
    args1 = func1.get('args', 0)
    args2 = func2.get('args', 0)
    args_similarity = 1.0 - min(1.0, abs(args1 - args2) / max(1, max(args1, args2)))

    # Combine similarities with appropriate weights
    return 0.2 * name_similarity + 0.8 * args_similarity

def find_similar_functions(ast1, ast2, threshold=0.7):
    """Find similar functions between two AST structures using anti-unification"""
    similar_pairs = []
    common_patterns = []

    # Check if either file has errors
    if 'error' in ast1 or 'error' in ast2 or 'tree' not in ast1 or 'tree' not in ast2:
        return [], []

    # Apply anti-unification to function pairs
    visitor = AntiUnificationVisitor()

    # Extract functions from AST
    functions1 = [n for n in ast.walk(ast1['tree']) if isinstance(n, ast.FunctionDef)]
    functions2 = [n for n in ast.walk(ast2['tree']) if isinstance(n, ast.FunctionDef)]

    for func1 in functions1:
        for func2 in functions2:
            # Skip very small functions (less than 3 statements)
            if len(func1.body) < 3 or len(func2.body) < 3:
                continue

            # Try anti-unification
            pattern = visitor.anti_unify(func1, func2)

            if pattern:
                similar_pairs.append({
                    'function1': func1.name,
                    'function2': func2.name,
                    'line1': func1.lineno,
                    'line2': func2.lineno,
                    'similarity': pattern['similarity']
                })

                common_patterns.append({
                    'pattern': pattern['pattern'],
                    'function1': func1.name,
                    'function2': func2.name,
                    'similarity': pattern['similarity'],
                    'var_mapping': pattern['var_mapping']
                })

    # If no anti-unification pairs found, fall back to regular structure comparison
    if not similar_pairs:
        functions1 = ast1.get('functions', [])
        functions2 = ast2.get('functions', [])

        for func1 in functions1:
            for func2 in functions2:
                # Skip very small functions
                if len(func1.get('structure', [])) < 3 or len(func2.get('structure', [])) < 3:
                    continue

                # Calculate structural similarity
                struct_sim = structure_similarity(func1, func2)

                # Calculate signature similarity
                sig_sim = function_signature_similarity(func1, func2)

                # Combine scores with weights
                combined_similarity = 0.7 * struct_sim + 0.3 * sig_sim

                if combined_similarity >= threshold:
                    similar_pairs.append({
                        'function1': func1.get('name'),
                        'function2': func2.get('name'),
                        'line1': func1.get('line'),
                        'line2': func2.get('line'),
                        'similarity': combined_similarity
                    })

    return similar_pairs, common_patterns

def analyze_files(file_paths, threshold=0.7):
    """Analyze AST structures for a list of files"""
    structures = {}
    error_files = []
    common_patterns = []

    # Extract AST structures
    print(f"Extracting AST structures for {len(file_paths)} files...", file=sys.stderr)
    for i, file_path in enumerate(file_paths):
        if i % 10 == 0:
            print(f"Processing file {i+1}/{len(file_paths)}", file=sys.stderr)

        structure = get_ast_structure(file_path)
        structures[file_path] = structure

        if 'error' in structure:
            error_files.append(file_path)

    # Find similar files based on AST structures
    print(f"Comparing file pairs to find similarities...", file=sys.stderr)
    similar_pairs = []
    total_pairs = len(file_paths) * (len(file_paths) - 1) // 2
    pair_count = 0

    for i, file1 in enumerate(file_paths):
        for j, file2 in enumerate(file_paths):
            if j <= i:  # Skip self-comparisons and duplicates
                continue

            pair_count += 1
            if pair_count % 100 == 0:
                print(f"Comparing pair {pair_count}/{total_pairs}", file=sys.stderr)

            # Skip if either file had parsing errors
            if file1 in error_files or file2 in error_files:
                continue

            # Find similar functions using anti-unification
            similar_functions, patterns = find_similar_functions(structures[file1], structures[file2], threshold)

            # Extend the pattern collection
            common_patterns.extend(patterns)

            # Calculate overall similarity
            if similar_functions:
                max_func_similarity = max(pair['similarity'] for pair in similar_functions)

                # Compare overall AST structures
                node_types1 = structures[file1].get('node_types', {})
                node_types2 = structures[file2].get('node_types', {})

                # Calculate Jaccard similarity for node type distributions
                all_types = set(node_types1.keys()) | set(node_types2.keys())
                if all_types:
                    type_similarity = sum(min(node_types1.get(t, 0), node_types2.get(t, 0)) for t in all_types) / \
                                      sum(max(node_types1.get(t, 0), node_types2.get(t, 0)) for t in all_types)
                else:
                    type_similarity = 0.0

                # Calculate import similarity
                imports1 = set(structures[file1].get('imports', []))
                imports2 = set(structures[file2].get('imports', []))

                if imports1 or imports2:
                    import_similarity = len(imports1 & imports2) / len(imports1 | imports2) if imports1 | imports2 else 0.0
                else:
                    import_similarity = 0.0

                # Combine scores with weights
                combined_similarity = 0.6 * max_func_similarity + 0.3 * type_similarity + 0.1 * import_similarity

                if combined_similarity >= threshold:
                    similar_pairs.append({
                        'file1': file1,
                        'file2': file2,
                        'similarity': combined_similarity,
                        'similar_functions': similar_functions
                    })

    # Group common patterns by similarity to identify code templates
    if common_patterns:
        # Sort by similarity (highest first)
        common_patterns.sort(key=lambda x: x['similarity'], reverse=True)

        # Take top patterns (most similar and representative)
        top_patterns = common_patterns[:min(10, len(common_patterns))]
    else:
        top_patterns = []

    return {
        'similar_pairs': similar_pairs,
        'file_count': len(file_paths),
        'error_count': len(error_files),
        'common_patterns': top_patterns
    }

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python ast_analyzer.py <threshold> <file1> <file2> ...", file=sys.stderr)
        sys.exit(1)

    threshold = float(sys.argv[1])
    file_paths = sys.argv[2:]

    result = analyze_files(file_paths, threshold)
    print(json.dumps(result, indent=2))
EOF
}

# Run AST-based analysis on a list of files
run_ast_analysis() {
    local threshold="${1:-0.7}"
    shift
    local files=("$@")
    local output_file=$(mktemp)

    # Create temporary script file
    local script_file=$(mktemp)
    generate_ast_analyzer_script > "$script_file"

    # Run the analysis with timeout
    if [ "$VERBOSE" = true ]; then
        log "INFO" "Running enhanced AST analysis with anti-unification on ${#files[@]} files with threshold $threshold"
    fi

    # Check if files were provided
    if [ ${#files[@]} -eq 0 ]; then
        log "ERROR" "No files provided for AST analysis"
        echo '{"similar_pairs":[],"file_count":0,"error_count":0,"common_patterns":[]}'
        return 1
    fi

    # Run the analysis
    local files_str=$(printf "'%s' " "${files[@]}")
    run_with_timeout $ANALYSIS_TIMEOUT "python3 $script_file $threshold $files_str > $output_file" || {
        log "ERROR" "AST analysis timed out"
        echo '{"similar_pairs":[],"file_count":0,"error_count":0,"common_patterns":[]}'
        rm -f "$script_file" "$output_file"
        return 1
    }

    # Check if output was generated
    if [ ! -s "$output_file" ]; then
        log "ERROR" "AST analysis did not produce any output"
        echo '{"similar_pairs":[],"file_count":0,"error_count":0,"common_patterns":[]}'
        rm -f "$script_file" "$output_file"
        return 1
    fi

    # Return the results
    cat "$output_file"

    # Clean up
    rm -f "$script_file" "$output_file"
    return 0
}

# Export functions
export -f generate_ast_analyzer_script
export -f run_ast_analysis
