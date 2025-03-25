"""
Unit tests for env_loader.py
Tests the functionality for loading environment variables
and validating required variables without using mocks.
"""

import os
import pytest
from pathlib import Path
import tempfile
from ai_service.utils.env_loader import (
    load_env_file,
    validate_required_env_vars,
    get_openai_api_key,
)

class TestEnvLoader:
    """Test the environment variable loader functions."""

    def test_load_env_file_success(self):
        """Test loading environment variables from a .env file successfully."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.env', delete=False) as temp:
            temp.write("TEST_VAR_1=test_value_1\n")
            temp.write("TEST_VAR_2=test_value_2\n")
            temp_file_path = temp.name

        try:
            # Load the environment variables
            result = load_env_file(temp_file_path)

            # Check that the file was loaded
            assert result is True

            # Check that the variables were loaded
            assert os.environ.get("TEST_VAR_1") == "test_value_1"
            assert os.environ.get("TEST_VAR_2") == "test_value_2"
        finally:
            # Clean up
            os.unlink(temp_file_path)
            # Remove the vars from environment
            os.environ.pop("TEST_VAR_1", None)
            os.environ.pop("TEST_VAR_2", None)

    def test_load_env_file_nonexistent(self):
        """Test loading environment variables from a nonexistent .env file."""
        # Try to load a nonexistent file
        result = load_env_file("/path/to/nonexistent/file.env")

        # Function should return False and not raise an exception
        assert result is False

    def test_validate_required_env_vars_success(self):
        """Test validation of required environment variables when all are present."""
        # Set environment variables
        os.environ["TEST_REQUIRED_1"] = "value1"
        os.environ["TEST_REQUIRED_2"] = "value2"

        try:
            # Validate the variables
            result = validate_required_env_vars(["TEST_REQUIRED_1", "TEST_REQUIRED_2"])

            # Check the result
            assert result == {
                "TEST_REQUIRED_1": "value1",
                "TEST_REQUIRED_2": "value2"
            }
        finally:
            # Clean up
            os.environ.pop("TEST_REQUIRED_1", None)
            os.environ.pop("TEST_REQUIRED_2", None)

    def test_validate_required_env_vars_missing(self):
        """Test validation of required environment variables when some are missing."""
        # Set only one environment variable
        os.environ["TEST_REQUIRED_1"] = "value1"

        try:
            # Try to validate with a missing variable - should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                validate_required_env_vars(["TEST_REQUIRED_1", "TEST_MISSING_VAR"])

            # Check the error message
            assert "TEST_MISSING_VAR" in str(exc_info.value)
        finally:
            # Clean up
            os.environ.pop("TEST_REQUIRED_1", None)

    def test_get_openai_api_key_success(self):
        """Test getting the OpenAI API key when it's present."""
        # Set the API key
        os.environ["OPENAI_API_KEY"] = "sk-test-key"

        try:
            # Get the API key
            api_key = get_openai_api_key()

            # Check the result
            assert api_key == "sk-test-key"
        finally:
            # Clean up
            os.environ.pop("OPENAI_API_KEY", None)

    def test_get_openai_api_key_missing(self):
        """Test getting the OpenAI API key when it's missing."""
        # Make sure the API key is not set
        os.environ.pop("OPENAI_API_KEY", None)

        # Try to get the API key - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            get_openai_api_key()

        # Check the error message
        assert "OPENAI_API_KEY" in str(exc_info.value)
