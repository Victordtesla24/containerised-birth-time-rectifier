import pytest

def pytest_collect_file(parent, path):
    """Custom file collection hook to avoid treating specific router files as test files."""
    if path.basename == 'ai_integration_test.py':
        return None
