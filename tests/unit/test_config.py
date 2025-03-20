"""
Unit tests for config.py
Tests the configuration settings loaded from environment variables.
"""

import os
import pytest
from typing import Dict, Any
from ai_service.core.config import Settings, settings

class TestConfig:
    """Test the configuration settings functionality."""

    def test_settings_default_values(self):
        """Test that default values are correctly set."""
        test_settings = Settings()

        # Check API settings
        assert test_settings.API_PREFIX == "/api/v1"
        assert test_settings.PROJECT_NAME == "Birth Time Rectifier API"
        assert test_settings.VERSION == "1.0.0"

        # Check CORS settings
        assert test_settings.CORS_ORIGINS == ["*"]
        assert test_settings.CORS_HEADERS == ["*"]

        # Check auth settings
        assert test_settings.JWT_ALGORITHM == "HS256"
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

        # Check chart calculation settings
        assert test_settings.DEFAULT_HOUSE_SYSTEM == "P"
        assert test_settings.DEFAULT_ZODIAC_TYPE == "sidereal"
        assert pytest.approx(test_settings.DEFAULT_AYANAMSA, 0.0001) == 23.6647

    def test_database_url_assembly(self):
        """Test that the DATABASE_URL is correctly assembled from components."""
        # Setup environment with no DATABASE_URL
        if "DATABASE_URL" in os.environ:
            original_db_url = os.environ["DATABASE_URL"]
            del os.environ["DATABASE_URL"]
        else:
            original_db_url = None

        # Set specific DB components
        os.environ["DB_HOST"] = "testhost"
        os.environ["DB_PORT"] = "5433"
        os.environ["DB_USER"] = "testuser"
        os.environ["DB_PASSWORD"] = "testpass"
        os.environ["DB_NAME"] = "testdb"

        try:
            # Create settings and check DB URL
            test_settings = Settings()
            expected_url = "postgresql://testuser:testpass@testhost:5433/testdb"
            assert test_settings.DATABASE_URL == expected_url
        finally:
            # Restore original environment
            for key in ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]:
                if key in os.environ:
                    del os.environ[key]

            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url

    def test_database_url_direct_setting(self):
        """Test that an explicitly set DATABASE_URL is used without modification."""
        # Set explicit DATABASE_URL
        os.environ["DATABASE_URL"] = "postgresql://explicit:pass@host:5432/explicitdb"

        try:
            test_settings = Settings()
            assert test_settings.DATABASE_URL == "postgresql://explicit:pass@host:5432/explicitdb"
        finally:
            del os.environ["DATABASE_URL"]

    def test_hide_sensitive_settings(self):
        """Test that sensitive settings are hidden in the dict representation."""
        # Set sensitive values
        os.environ["SECRET_KEY"] = "super_secret_key"
        os.environ["OPENAI_API_KEY"] = "sk-12345openaikey"

        try:
            test_settings = Settings()
            hidden_dict = test_settings.dict_with_secrets_hidden()

            # Check sensitive values are hidden
            assert hidden_dict["SECRET_KEY"] == "**HIDDEN**"
            assert hidden_dict["OPENAI_API_KEY"] == "**HIDDEN**"

            # Check non-sensitive values are preserved
            assert hidden_dict["API_PREFIX"] == "/api/v1"
            assert hidden_dict["PROJECT_NAME"] == "Birth Time Rectifier API"
        finally:
            del os.environ["SECRET_KEY"]
            del os.environ["OPENAI_API_KEY"]

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
        os.environ["RATE_LIMIT_PER_MINUTE"] = "100"
        os.environ["SESSION_EXPIRY_DAYS"] = "45"
        os.environ["GPU_MEMORY_FRACTION"] = "0.5 # With comment"

        try:
            test_settings = Settings()
            assert test_settings.RATE_LIMIT_PER_MINUTE == 100
            assert test_settings.SESSION_EXPIRY_DAYS == 45
            assert test_settings.GPU_MEMORY_FRACTION == 0.5
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
