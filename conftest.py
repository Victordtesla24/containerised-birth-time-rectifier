import pytest
import os
from dotenv import load_dotenv

# Load environment variables from .env file for all tests
load_dotenv()

# Ensure OPENAI_API_KEY is set
if not os.environ.get("OPENAI_API_KEY"):
    pytest.fail("OPENAI_API_KEY environment variable is not set. Please set it in .env file.")




