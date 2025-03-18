#!/usr/bin/env python

file_path = 'tests/test_questionnaire_engine.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

# Find the test methods that need fixing
methods_to_fix = [
    'test_get_first_question',
    'test_generate_dynamic_question',
    'test_calculate_confidence'
]

for method_name in methods_to_fix:
    # Find the method
    method_start = None
    method_end = None

    for i, line in enumerate(lines):
        if f'def {method_name}' in line:
            method_start = i
            # Find the end of the method (next def or end of file)
            for j in range(i + 1, len(lines)):
                if 'def ' in lines[j] or j == len(lines) - 1:
                    method_end = j
                    break

            if method_start is not None and method_end is not None:
                print(f"Found method {method_name} from line {method_start+1} to {method_end}")

                # Check if the method has a try-finally block
                has_try_finally = False
                try_start = -1
                finally_start = -1

                for j in range(method_start, method_end):
                    if 'try:' in lines[j]:
                        try_start = j
                    if 'finally:' in lines[j] and try_start >= 0:
                        finally_start = j
                        has_try_finally = True

                if has_try_finally:
                    print(f"Method {method_name} has a try-finally block")
                    # Add return None after the finally block
                    indent = 8  # Default indent
                    for j in range(finally_start, method_end):
                        if lines[j].strip() and not lines[j].strip().startswith('#'):
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            break

                    # Find the end of the finally block
                    finally_end = method_end
                    for j in range(finally_start + 1, method_end):
                        if lines[j].strip() and not lines[j].strip().startswith('#'):
                            current_indent = len(lines[j]) - len(lines[j].lstrip())
                            if current_indent <= indent:
                                finally_end = j
                                break

                    # Add return None after the finally block
                    lines.insert(finally_end, ' ' * indent + 'return None  # Explicitly return None\n')
                    print(f"Added return None after line {finally_end}")
                else:
                    # Find the last assertion
                    last_assertion = None
                    for j in range(method_end - 1, method_start, -1):
                        if 'self.assert' in lines[j]:
                            last_assertion = j
                            break

                    if last_assertion is not None:
                        # Add a None statement after the last assertion
                        lines.insert(last_assertion + 1, '        return None  # Explicitly return None\n')
                        print(f"Added return None after line {last_assertion+1}")

                # Adjust method_end for subsequent methods
                method_end += 1

            break

# Write the modified file
with open(file_path, 'w') as f:
    f.writelines(lines)

print("File updated successfully")
