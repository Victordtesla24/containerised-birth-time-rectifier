#!/usr/bin/env python

file_path = 'ai_service/utils/questionnaire_engine.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

# Find the line with the comment and the houses line
for i, line in enumerate(lines):
    if '# Check for planets near house cusps' in line:
        print(f"Found comment at line {i+1}: {repr(line)}")

        # Check the next line for houses
        houses_line_idx = i + 1
        houses_line = lines[houses_line_idx]
        print(f"Houses line {houses_line_idx+1}: {repr(houses_line)}")

        # Fix the indentation to 8 spaces
        if 'houses = ' in houses_line:
            fixed_line = ' ' * 8 + houses_line.lstrip()
            lines[houses_line_idx] = fixed_line
            print(f"Fixed line: {repr(fixed_line)}")

            # Write back to file
            with open(file_path, 'w') as f:
                f.writelines(lines)
            print("File updated successfully")
            break
