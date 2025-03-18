#!/usr/bin/env python

import re

# Read the test file
with open('tests/test_questionnaire_engine.py', 'r') as f:
    content = f.read()

# Fix the test_get_first_question method
# Remove any existing 'return None' statements
content = re.sub(
    r'(async def test_get_first_question.*?self\.assertIn\("type", result\))\s+return None.*?(?=\n\s*def)',
    r'\1\n',
    content,
    flags=re.DOTALL
)

# Fix the test_generate_dynamic_question method
# Remove existing return None and ensure it's after the finally block
content = re.sub(
    r'(async def test_generate_dynamic_question.*?finally:.*?self\.engine\.openai_service = original_service)\s+return None.*?(?=\n\s*def)',
    r'\1\n',
    content,
    flags=re.DOTALL
)

# Fix the test_calculate_confidence method
# Remove existing return None and ensure it's after the finally block
content = re.sub(
    r'(async def test_calculate_confidence.*?finally:.*?self\.engine\.openai_service = original_service)\s+return None.*?(?=$|\n\s*def)',
    r'\1\n',
    content,
    flags=re.DOTALL
)

# Write the fixed content back to the file
with open('tests/test_questionnaire_engine.py', 'w') as f:
    f.write(content)

print("Test methods fixed - removed problematic return None statements")
