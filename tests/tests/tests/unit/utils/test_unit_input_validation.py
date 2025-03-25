"""
Unit tests for input validation logic.

These tests verify that the validation functions correctly identify valid and invalid inputs.
"""
import pytest
import asyncio
from typing import Dict, Any

from ai_service.core.validators import validate_birth_details

# Sample test data - valid inputs
VALID_BIRTH_DATE = "1985-10-25"
VALID_BIRTH_TIME = "14:30:00"
VALID_LATITUDE = 18.5213738
VALID_LONGITUDE = 73.8545071
VALID_TIMEZONE = "Asia/Kolkata"

@pytest.mark.asyncio
async def test_validate_birth_details_valid_input():
    """Test that validation passes with valid birth details."""
    # Arrange: Set up valid input parameters
    birth_date = VALID_BIRTH_DATE
    birth_time = VALID_BIRTH_TIME
    latitude = VALID_LATITUDE
    longitude = VALID_LONGITUDE
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation passes and input values are returned
    assert result["valid"] is True, f"Validation failed with errors: {result.get('errors')}"
    assert result["errors"] is None, "Expected no errors for valid input"
    assert result["birth_date"] == birth_date
    assert result["birth_time"] == birth_time
    assert result["latitude"] == latitude
    assert result["longitude"] == longitude
    assert result["timezone"] == timezone

@pytest.mark.asyncio
async def test_validate_birth_details_invalid_date():
    """Test that validation fails with invalid date format."""
    # Arrange: Set up input with invalid date
    birth_date = "25-10-1985"  # Wrong format, should be YYYY-MM-DD
    birth_time = VALID_BIRTH_TIME
    latitude = VALID_LATITUDE
    longitude = VALID_LONGITUDE
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for invalid date format"
    assert result["errors"] is not None, "Expected errors for invalid date format"
    assert any("date format" in error.lower() for error in result["errors"]), "Error should mention date format"
    assert result["birth_date"] is None, "Expected birth_date to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_impossible_date():
    """Test that validation fails with impossible date."""
    # Arrange: Set up input with impossible date
    birth_date = "1985-02-30"  # February 30 doesn't exist
    birth_time = VALID_BIRTH_TIME
    latitude = VALID_LATITUDE
    longitude = VALID_LONGITUDE
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for impossible date"
    assert result["errors"] is not None, "Expected errors for impossible date"
    assert result["birth_date"] is None, "Expected birth_date to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_invalid_time():
    """Test that validation fails with invalid time format."""
    # Arrange: Set up input with invalid time
    birth_date = VALID_BIRTH_DATE
    birth_time = "14:30"  # Missing seconds
    latitude = VALID_LATITUDE
    longitude = VALID_LONGITUDE
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for invalid time format"
    assert result["errors"] is not None, "Expected errors for invalid time format"
    assert any("time format" in error.lower() for error in result["errors"]), "Error should mention time format"
    assert result["birth_time"] is None, "Expected birth_time to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_out_of_range_time():
    """Test that validation fails with out of range time values."""
    # Arrange: Set up input with impossible time
    birth_date = VALID_BIRTH_DATE
    birth_time = "25:70:00"  # Hours > 23, minutes > 59
    latitude = VALID_LATITUDE
    longitude = VALID_LONGITUDE
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for out of range time"
    assert result["errors"] is not None, "Expected errors for out of range time"
    assert any("must be" in error.lower() for error in result["errors"]), "Error should mention valid ranges"
    assert result["birth_time"] is None, "Expected birth_time to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_invalid_latitude():
    """Test that validation fails with invalid latitude."""
    # Arrange: Set up input with invalid latitude
    birth_date = VALID_BIRTH_DATE
    birth_time = VALID_BIRTH_TIME
    latitude = 91.5  # Latitude > 90
    longitude = VALID_LONGITUDE
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for invalid latitude"
    assert result["errors"] is not None, "Expected errors for invalid latitude"
    assert any("latitude" in error.lower() for error in result["errors"]), "Error should mention latitude"
    assert result["latitude"] is None, "Expected latitude to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_invalid_longitude():
    """Test that validation fails with invalid longitude."""
    # Arrange: Set up input with invalid longitude
    birth_date = VALID_BIRTH_DATE
    birth_time = VALID_BIRTH_TIME
    latitude = VALID_LATITUDE
    longitude = -181.0  # Longitude < -180
    timezone = VALID_TIMEZONE

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for invalid longitude"
    assert result["errors"] is not None, "Expected errors for invalid longitude"
    assert any("longitude" in error.lower() for error in result["errors"]), "Error should mention longitude"
    assert result["longitude"] is None, "Expected longitude to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_empty_timezone():
    """Test that validation fails with empty timezone."""
    # Arrange: Set up input with empty timezone
    birth_date = VALID_BIRTH_DATE
    birth_time = VALID_BIRTH_TIME
    latitude = VALID_LATITUDE
    longitude = VALID_LONGITUDE
    timezone = ""  # Empty timezone

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with appropriate error
    assert result["valid"] is False, "Validation should fail for empty timezone"
    assert result["errors"] is not None, "Expected errors for empty timezone"
    assert any("timezone" in error.lower() for error in result["errors"]), "Error should mention timezone"
    assert result["timezone"] is None, "Expected timezone to be None for invalid input"

@pytest.mark.asyncio
async def test_validate_birth_details_multiple_errors():
    """Test that validation captures multiple errors."""
    # Arrange: Set up input with multiple invalid values
    birth_date = "invalid-date"
    birth_time = "invalid-time"
    latitude = 100.0  # > 90
    longitude = 200.0  # > 180
    timezone = ""  # Empty

    # Act: Call the validation function
    result = await validate_birth_details(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Assert: Verify validation fails with multiple errors
    assert result["valid"] is False, "Validation should fail for multiple errors"
    assert result["errors"] is not None, "Expected multiple errors"
    assert len(result["errors"]) >= 4, f"Expected at least 4 errors, got: {result['errors']}"
    # All values should be None for invalid input
    assert result["birth_date"] is None
    assert result["birth_time"] is None
    assert result["latitude"] is None
    assert result["longitude"] is None
    assert result["timezone"] is None
