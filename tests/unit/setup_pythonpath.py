import sys
import os

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add project root to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Print the updated Python path
print(f"Python path updated: {sys.path}")
