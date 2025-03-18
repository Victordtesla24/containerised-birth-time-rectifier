#!/usr/bin/env python3
"""
Script to fix async test methods in test_questionnaire_engine.py
Removes explicit return statements and fixes other async-related issues
"""

import re
import os

def fix_async_tests(file_path):
    """Fix async test methods in the given file"""
    print(f"Fixing async test methods in {file_path}")

    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()

    # Find all async test methods
    async_test_pattern = r'@pytest\.mark\.asyncio\s+async\s+def\s+test_[^(]+\([^)]+\):'
    async_test_matches = re.finditer(async_test_pattern, content)

    # Track positions of async test methods
    async_test_positions = []
    for match in async_test_matches:
        start_pos = match.start()
        method_name_match = re.search(r'def\s+(test_[^(]+)', match.group())
        if method_name_match:
            method_name = method_name_match.group(1)
            async_test_positions.append((start_pos, method_name))

    # Sort positions in reverse order to avoid affecting earlier positions when making changes
    async_test_positions.sort(reverse=True)

    # Process each async test method
    for start_pos, method_name in async_test_positions:
        print(f"Processing async test method: {method_name}")

        # Find the end of the method
        # This is a simplified approach - assumes proper indentation
        method_start = content.find(':', start_pos) + 1

        # Find the indentation level of the method
        next_line_start = content.find('\n', method_start) + 1
        indent_match = re.match(r'(\s+)', content[next_line_start:])
        if not indent_match:
            print(f"  Could not determine indentation for {method_name}, skipping")
            continue

        method_indent = indent_match.group(1)

        # Find where the method ends (next line with same or less indentation)
        method_end = next_line_start
        while method_end < len(content):
            next_line_start = content.find('\n', method_end) + 1
            if next_line_start <= 0:  # End of file
                method_end = len(content)
                break

            # Check if this line has less indentation
            if content[method_end:next_line_start].strip() and not content[method_end:next_line_start].startswith(method_indent):
                break

            method_end = next_line_start

        # Extract the method body
        method_body = content[method_start:method_end]

        # Remove explicit return statements at the end of the method
        fixed_method_body = re.sub(
            r'\s+return\s+None\s*$',
            '',
            method_body
        )

        # Also remove any other explicit returns that might be at the end of the method
        fixed_method_body = re.sub(
            r'\s+return\s+[^(\n]+\s*$',
            '',
            fixed_method_body
        )

        # Update the content
        if fixed_method_body != method_body:
            print(f"  Removed explicit return from {method_name}")
            content = content[:method_start] + fixed_method_body + content[method_end:]

    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(content)

    print(f"Fixed async test methods in {file_path}")

if __name__ == "__main__":
    test_file = "tests/test_questionnaire_engine.py"
    if os.path.exists(test_file):
        fix_async_tests(test_file)
    else:
        print(f"Error: File {test_file} not found")
