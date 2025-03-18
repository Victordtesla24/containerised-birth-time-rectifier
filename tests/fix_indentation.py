#!/usr/bin/env python
file_path = 'ai_service/utils/questionnaire_engine.py'
with open(file_path, 'r') as f:
    lines = f.readlines()

# Find and examine the houses line
for i, line in enumerate(lines):
    if '# Check for planets near house cusps' in line:
        houses_line = i+2
        print(f'Found comment at line {i+1}: {repr(line)}')
        print(f'Houses line {houses_line+1}: {repr(lines[houses_line])}')
        print(f'ASCII representation:')
        for c in lines[houses_line]:
            print(f'{c}: {ord(c)}')

        # Try to fix the line
        fixed_line = ' ' * 8 + lines[houses_line].lstrip()
        print(f'Fixed line would be: {repr(fixed_line)}')

        # Update the line
        lines[houses_line] = fixed_line

        # Write back to file
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print('File updated')
        break
