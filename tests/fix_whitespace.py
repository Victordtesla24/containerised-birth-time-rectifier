#!/usr/bin/env python

file_path = 'ai_service/utils/questionnaire_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the exact function definition
start_line = 0
for i, line in enumerate(lines):
    if 'def _identify_uncertain_factors' in line:
        start_line = i
        print(f"Found function definition at line {i+1}: {line.strip()}")
        break

if start_line == 0:
    print("Could not find _identify_uncertain_factors function")
    exit(1)

# Now examine whitespace in this function specifically
print("\nExamining function whitespace:")
for i in range(start_line, len(lines)):
    line = lines[i]

    # Break if we reach another function definition
    if i > start_line and line.strip().startswith('def '):
        break

    # Count leading whitespace and check for tabs
    leading_space = len(line) - len(line.lstrip())
    has_tabs = '\t' in line[:leading_space]

    # Create visualization of whitespace
    whitespace_vis = ''
    for char in line[:leading_space]:
        if char == ' ':
            whitespace_vis += '·'
        elif char == '\t':
            whitespace_vis += '→'

    print(f"Line {i+1}: spaces={leading_space}, tabs={has_tabs}, vis=[{whitespace_vis}] | {line.rstrip()}")

    # Check for hidden Unicode whitespace characters
    for j, char in enumerate(line):
        if ord(char) > 127 and char.isspace():
            print(f"  Found hidden whitespace at position {j}: ord={ord(char)}, hex={hex(ord(char))}")

# Fix any indentation issues in the function
fixed = False
for i in range(start_line, len(lines)):
    # Break if we reach another function definition
    if i > start_line and lines[i].strip().startswith('def '):
        break

    # Look for the line with planets near house cusps comment
    if "# Check for planets near house cusps" in lines[i]:
        comment_line = i
        print(f"\nFound comment line at {i+1}: {lines[i].strip()}")

        # Check and fix next line for houses declaration
        houses_line = i + 1
        if houses_line < len(lines):
            print(f"Next line {houses_line+1}: {lines[houses_line].strip()}")

            # Fix houses line indentation
            if "houses =" in lines[houses_line]:
                old_indent = len(lines[houses_line]) - len(lines[houses_line].lstrip())
                clean_line = lines[houses_line].lstrip()
                lines[houses_line] = ' ' * 8 + clean_line
                print(f"Fixed houses line indentation from {old_indent} to 8 spaces")
                fixed = True
            else:
                # If not found, look at subsequent lines
                for j in range(houses_line, houses_line + 5):
                    if j < len(lines) and "houses =" in lines[j]:
                        old_indent = len(lines[j]) - len(lines[j].lstrip())
                        clean_line = lines[j].lstrip()
                        lines[j] = ' ' * 8 + clean_line
                        print(f"Fixed houses line indentation at line {j+1} from {old_indent} to 8 spaces")
                        fixed = True
                        break

                if not fixed:
                    # Insert the houses line with proper indentation
                    lines.insert(houses_line, ' ' * 8 + 'houses = chart_data.get("houses", [])\n')
                    print(f"Inserted houses line at {houses_line+1}")
                    fixed = True

        # Also check planets line and fix if needed
        planets_line = houses_line + (1 if fixed and "houses =" not in lines[houses_line] else 0)
        if planets_line < len(lines):
            print(f"Looking at planets line {planets_line+1}: {lines[planets_line].strip()}")
            if "planets =" in lines[planets_line]:
                old_indent = len(lines[planets_line]) - len(lines[planets_line].lstrip())
                if old_indent != 8:
                    clean_line = lines[planets_line].lstrip()
                    lines[planets_line] = ' ' * 8 + clean_line
                    print(f"Fixed planets line indentation from {old_indent} to 8 spaces")
                    fixed = True

        break

if fixed:
    # Write the fixed file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("\nFile updated with fixed whitespace")
else:
    print("\nNo issues found or fixed needed")
