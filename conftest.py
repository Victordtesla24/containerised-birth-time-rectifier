import pytest
import os
from dotenv import load_dotenv

# Load environment variables from .env file for all tests
load_dotenv()

# Ensure OPENAI_API_KEY is set
if not os.environ.get("OPENAI_API_KEY"):
    pytest.fail("OPENAI_API_KEY environment variable is not set. Please set it in .env file.")

# Run all tests with real implementations
# No test mocks or fixtures that use mocks
# No test skipping based on environment
# All tests should fail if real implementations are not available
