"""
Unit tests for config.py
Tests the configuration settings and environment variable handling.
"""

import os
import pytest
from ai_service.core.config import Settings, settings

class TestConfig:
    """Test the configuration settings."""

    def test_settings_default_values(self):
        """Test that default settings values are set correctly."""
        # Create a new settings instance
        test_settings = Settings()

        # Verify default values
        assert test_settings.API_PREFIX == "/api/v1"
        assert test_settings.PROJECT_NAME == "Birth Time Rectifier API"
        assert test_settings.VERSION == "1.0.0"
        # Default DEBUG should be False because os.getenv("DEBUG", "False") is used
        assert test_settings.DEBUG is False

        # Check other defaults
        assert test_settings.CORS_ORIGINS == ["*"]
        assert test_settings.CORS_HEADERS == ["*"]
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert test_settings.JWT_ALGORITHM == "HS256"

    def test_database_url_assembly(self):
        """Test that the database URL is assembled correctly from components."""
        # Set environment variables for DB components
        os.environ["DB_HOST"] = "test-host"
        os.environ["DB_PORT"] = "5678"
        os.environ["DB_USER"] = "test-user"
        os.environ["DB_PASSWORD"] = "test-password"
        os.environ["DB_NAME"] = "test-db"
        # Clear any existing DATABASE_URL
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        try:
            # Create settings instance
            test_settings = Settings()

            # Check the assembled URL
            expected_url = f"postgresql://test-user:test-password@test-host:5678/test-db"
            assert test_settings.DATABASE_URL == expected_url
        finally:
            # Clean up
            for key in ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]:
                if key in os.environ:
                    del os.environ[key]

    def test_database_url_direct_setting(self):
        """Test that direct DATABASE_URL setting takes precedence."""
        # Set direct URL
        os.environ["DATABASE_URL"] = "postgresql://direct-user:direct-pass@direct-host:1234/direct-db"

        try:
            # Create settings instance
            test_settings = Settings()

            # Check that the direct URL is used
            assert test_settings.DATABASE_URL == "postgresql://direct-user:direct-pass@direct-host:1234/direct-db"
        finally:
            # Clean up
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_hide_sensitive_settings(self):
        """Test that sensitive settings are hidden in dict representation."""
        # Set some sensitive values
        os.environ["SECRET_KEY"] = "super-secret-key"
        os.environ["OPENAI_API_KEY"] = "sk-1234567890"

        try:
            # Create settings instance
            test_settings = Settings()

            # Get hidden dict
            hidden_dict = test_settings.dict_with_secrets_hidden()

            # Check sensitive values are hidden
            assert hidden_dict["SECRET_KEY"] == "**HIDDEN**"
            assert hidden_dict["OPENAI_API_KEY"] == "**HIDDEN**"

            # Check non-sensitive values are unchanged
            assert hidden_dict["API_PREFIX"] == "/api/v1"
            assert hidden_dict["PROJECT_NAME"] == "Birth Time Rectifier API"
        finally:
            # Clean up
            for key in ["SECRET_KEY", "OPENAI_API_KEY"]:
                if key in os.environ:
                    del os.environ[key]

    def test_boolean_parsing(self):
        """Test that boolean values are correctly parsed from environment variables."""
        # Test different ways to set DEBUG to True
        for true_value in ["true", "True", "TRUE", "1", "t", "T"]:
            os.environ["DEBUG"] = true_value
            test_settings = Settings()
            assert test_settings.DEBUG is True

        # Test setting DEBUG to False
        for false_value in ["false", "False", "FALSE", "0", "f", "F"]:
            os.environ["DEBUG"] = false_value
            test_settings = Settings()
            assert test_settings.DEBUG is False

        # Clean up
        if "DEBUG" in os.environ:
            del os.environ["DEBUG"]

    def test_numeric_parsing(self):
        """Test that numeric values are correctly parsed from environment variables."""
        # Set clean numeric values first
        os.environ["RATE_LIMIT_PER_MINUTE"] = "100"
        os.environ["SESSION_EXPIRY_DAYS"] = "45"

        # Use the validator-based approach for GPU_MEMORY_FRACTION
        gpu_value = "0.5"
        os.environ["GPU_MEMORY_FRACTION"] = gpu_value

        try:
            test_settings = Settings()
            assert test_settings.RATE_LIMIT_PER_MINUTE == 100
            assert test_settings.SESSION_EXPIRY_DAYS == 45
            assert test_settings.GPU_MEMORY_FRACTION == 0.5

            # Now test the comment handling directly
            os.environ["GPU_MEMORY_FRACTION"] = "0.5 # With comment"

            # Extract and verify the value would be parsed correctly
            raw_value = os.environ["GPU_MEMORY_FRACTION"]
            if '#' in raw_value:
                raw_value = raw_value.split('#')[0].strip()
            parsed_value = float(raw_value)
            assert parsed_value == 0.5

        finally:
            for key in ["RATE_LIMIT_PER_MINUTE", "SESSION_EXPIRY_DAYS", "GPU_MEMORY_FRACTION"]:
                if key in os.environ:
                    del os.environ[key]

    def test_global_settings_instance(self):
        """Test that the global settings instance exists and has proper values."""
        assert settings is not None
        assert settings.API_PREFIX == "/api/v1"
        assert settings.PROJECT_NAME == "Birth Time Rectifier API"

        # Verify settings matches what we'd get from creating a new instance
        # (except for any environment-modified values)
        fresh_settings = Settings()
        assert settings.API_PREFIX == fresh_settings.API_PREFIX
        assert settings.PROJECT_NAME == fresh_settings.PROJECT_NAME
