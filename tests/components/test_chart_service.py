"""
Component tests for ChartService.
These tests validate the chart service against the sequence diagram flow.
"""

import pytest
import asyncio
import os
from datetime import datetime
import json
from typing import Dict, Any, List

from ai_service.services.chart_service import ChartService, ChartVerifier
from ai_service.api.services.openai.service import OpenAIService
from ai_service.core.astro_calculator import AstroCalculator

@pytest.fixture
async def chart_service():
    """Create a real chart service with real dependencies."""
    # Check if OpenAI API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("Skipping tests that require OpenAI: No API key available")

    # Create OpenAI service first
    openai_service = OpenAIService()

    # Create chart verifier with the OpenAI service
    chart_verifier = ChartVerifier(openai_service=openai_service)

    # Create astro calculator
    astro_calculator = AstroCalculator()

    # Create chart service with all real components
    service = ChartService(
        openai_service=openai_service,
        chart_verifier=chart_verifier,
        astro_calculator=astro_calculator
    )

    return service

@pytest.mark.asyncio
async def test_generate_chart_with_verification(chart_service):
    """Test generating a chart with OpenAI verification."""
    # Test data
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Generate chart with verification
    result = await chart_service.generate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        verify_with_openai=True
    )

    # Check result structure
    assert isinstance(result, dict)
    assert "chart_id" in result
    assert "planets" in result
    assert "houses" in result
    assert "aspects" in result

    # Check verification results
    assert "verification" in result
    verification = result["verification"]
    assert "verified" in verification
    assert isinstance(verification["verified"], bool)
    assert "confidence_score" in verification
    assert isinstance(verification["confidence_score"], (int, float))
    assert "message" in verification

    # Check that chart data looks reasonable
    planets = result["planets"]
    assert "Sun" in planets
    assert "Moon" in planets
    assert "longitude" in planets["Sun"]
    assert "house" in planets["Sun"]

@pytest.mark.asyncio
async def test_generate_chart_without_verification(chart_service):
    """Test generating a chart without OpenAI verification."""
    # Test data
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Generate chart without verification
    result = await chart_service.generate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        verify_with_openai=False
    )

    # Check result structure
    assert isinstance(result, dict)
    assert "chart_id" in result
    assert "planets" in result
    assert "houses" in result
    assert "aspects" in result

    # Verification should be skipped
    assert "verification" not in result

    # Check that chart data looks reasonable
    houses = result["houses"]
    assert len(houses) > 0

    # Check ascendant
    assert "ascendant" in result
    assert "longitude" in result["ascendant"]

@pytest.mark.asyncio
async def test_compare_charts(chart_service):
    """Test comparing two charts."""
    # First, generate two charts with different birth times
    chart1 = await chart_service.generate_chart(
        birth_date="1990-01-01",
        birth_time="12:00:00",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        verify_with_openai=False
    )

    chart2 = await chart_service.generate_chart(
        birth_date="1990-01-01",
        birth_time="12:30:00",  # 30 minutes difference
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        verify_with_openai=False
    )

    # Save both charts
    chart1_saved = await chart_service.save_chart(chart1)
    chart2_saved = await chart_service.save_chart(chart2)

    # Get chart IDs
    chart1_id = chart1_saved.get("chart_id")
    chart2_id = chart2_saved.get("chart_id")

    # Compare the charts
    comparison = await chart_service.compare_charts(chart1_id, chart2_id)

    # Check comparison structure
    assert isinstance(comparison, dict)
    assert "differences" in comparison
    assert isinstance(comparison["differences"], list)
    assert "summary" in comparison
    assert isinstance(comparison["summary"], str)

    # There should be at least some differences due to the time change
    assert len(comparison["differences"]) > 0

    # Check the first difference
    if comparison["differences"]:
        diff = comparison["differences"][0]
        assert "element_type" in diff
        assert "element_name" in diff
        assert "chart1_value" in diff
        assert "chart2_value" in diff
        assert "significance" in diff

@pytest.mark.asyncio
async def test_chart_verifier(chart_service):
    """Test the chart verifier component directly."""
    # Get chart verifier from service
    chart_verifier = chart_service._chart_verifier

    # Create test chart data
    verification_data = {
        "birth_details": {
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        "chart_data": {
            "planets": {
                "Sun": {"longitude": 280.5, "house": 10},
                "Moon": {"longitude": 120.3, "house": 4},
                "Mercury": {"longitude": 275.2, "house": 10}
            },
            "houses": {"1": 85.5, "10": 355.2},
            "ascendant": {"longitude": 85.5}
        }
    }

    # Verify the chart
    result = await chart_verifier.verify_chart(verification_data)

    # Check result structure
    assert isinstance(result, dict)
    assert "verified" in result
    assert isinstance(result["verified"], bool)
    assert "confidence_score" in result
    assert isinstance(result["confidence_score"], (int, float))
    assert "message" in result
    assert isinstance(result["message"], str)

@pytest.mark.asyncio
async def test_export_chart(chart_service):
    """Test exporting a chart."""
    # Generate a chart
    chart = await chart_service.generate_chart(
        birth_date="1990-01-01",
        birth_time="12:00:00",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        verify_with_openai=False
    )

    # Save the chart
    saved_chart = await chart_service.save_chart(chart)
    chart_id = saved_chart.get("chart_id")

    # Export the chart
    export_result = await chart_service.export_chart(chart_id, format="pdf")

    # Check result structure
    assert isinstance(export_result, dict)
    assert "download_url" in export_result
    assert isinstance(export_result["download_url"], str)
    assert "file_path" in export_result
    assert "format" in export_result
    assert export_result["format"] == "pdf"

@pytest.mark.asyncio
async def test_get_chart(chart_service):
    """Test getting a chart by ID."""
    # Generate and save a chart
    chart = await chart_service.generate_chart(
        birth_date="1990-01-01",
        birth_time="12:00:00",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        verify_with_openai=False
    )

    saved_chart = await chart_service.save_chart(chart)
    chart_id = saved_chart.get("chart_id")

    # Retrieve the chart
    retrieved_chart = await chart_service.get_chart(chart_id)

    # Check that the retrieved chart matches the original
    assert retrieved_chart is not None
    assert retrieved_chart.get("chart_id") == chart_id
    assert "birth_details" in retrieved_chart
    assert "planets" in retrieved_chart
    assert "houses" in retrieved_chart
