"""
Unit tests for the chart comparison service.
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch

from ai_service.services.chart_comparison_service import ChartComparisonService
from ai_service.models.chart_comparison import DifferenceType, ChartComparisonResponse
from ai_service.api.routers.consolidated_chart.utils import chart_storage

# Sample chart data for testing
SAMPLE_CHART1 = {
    "chart_id": "chart_123",
    "birth_details": {
        "name": "Test Person",
        "date": "2000-01-01",
        "time": "12:00:00",
        "location": "New York, NY, USA"
    },
    "ascendant": {
        "sign": "Aries",
        "degree": 15.5
    },
    "planets": [
        {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 10},
        {"name": "Moon", "sign": "Taurus", "degree": 5.2, "house": 2},
        {"name": "Mercury", "sign": "Capricorn", "degree": 8.3, "house": 10}
    ],
    "houses": [
        {"house": 1, "sign": "Aries", "degree": 15.5},
        {"house": 2, "sign": "Taurus", "degree": 10.2},
        {"house": 3, "sign": "Gemini", "degree": 5.8}
    ]
}

SAMPLE_CHART2 = {
    "chart_id": "chart_456",
    "birth_details": {
        "name": "Test Person",
        "date": "2000-01-01",
        "time": "12:15:00",  # Slightly different time
        "location": "New York, NY, USA"
    },
    "ascendant": {
        "sign": "Aries",
        "degree": 18.2  # Different degree
    },
    "planets": [
        {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 10},
        {"name": "Moon", "sign": "Taurus", "degree": 5.2, "house": 2},
        {"name": "Mercury", "sign": "Capricorn", "degree": 8.3, "house": 10}
    ],
    "houses": [
        {"house": 1, "sign": "Aries", "degree": 18.2},
        {"house": 2, "sign": "Taurus", "degree": 12.5},
        {"house": 3, "sign": "Gemini", "degree": 7.1}
    ]
}

@pytest.fixture
def chart_comparison_service():
    """Fixture for chart comparison service"""
    return ChartComparisonService()

@pytest.fixture
def setup_chart_storage():
    """Fixture to set up and tear down chart storage"""
    # Store original chart storage
    original_storage = chart_storage.copy()

    # Clear chart storage for tests
    chart_storage.clear()

    # Add test charts to storage
    chart_storage["chart_123"] = SAMPLE_CHART1
    chart_storage["chart_456"] = SAMPLE_CHART2

    yield

    # Restore original chart storage
    chart_storage.clear()
    chart_storage.update(original_storage)

def test_compare_charts_with_valid_data(setup_chart_storage, chart_comparison_service):
    """Test comparing charts with valid data"""
    # Call the service
    result = chart_comparison_service.compare_charts("chart_123", "chart_456")

    # Verify the result
    assert isinstance(result, ChartComparisonResponse)
    assert result.chart1_id == "chart_123"
    assert result.chart2_id == "chart_456"
    assert len(result.differences) > 0

    # Check that we have an ascendant difference
    ascendant_diffs = [d for d in result.differences if d.type == DifferenceType.ASCENDANT_SHIFT]
    assert len(ascendant_diffs) > 0

def test_compare_charts_with_missing_chart(setup_chart_storage, chart_comparison_service):
    """Test comparing charts when one chart is missing"""
    # Call the service - should handle the missing chart gracefully
    result = chart_comparison_service.compare_charts("chart_123", "missing_chart")

    # Verify the result contains an error message
    assert isinstance(result, ChartComparisonResponse)
    assert result.chart1_id == "chart_123"
    assert result.chart2_id == "missing_chart"
    assert result.summary is not None and "Error" in result.summary
    assert len(result.differences) == 0

def test_compare_charts_with_string_indices(setup_chart_storage, chart_comparison_service):
    """Test comparing charts with string indices in the data"""
    # Create a chart with string indices that would previously cause errors
    string_index_chart = {
        "chart_id": "chart_string_indices",
        "birth_details": {
            "name": "Test Person",
            "date": "2000-01-01",
            "time": "12:00:00",
            "location": "New York, NY, USA"
        },
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": "10"},  # String house
            {"name": "Moon", "sign": "Taurus", "degree": "5.2", "house": 2},  # String degree
            {"name": "Mercury", "sign": "Capricorn", "degree": 8.3, "house": 10}
        ],
        "houses": [
            {"house": "1", "sign": "Aries", "degree": 15.5},  # String house
            {"house": 2, "sign": "Taurus", "degree": "10.2"},  # String degree
            {"house": 3, "sign": "Gemini", "degree": 5.8}
        ]
    }

    # Add the string index chart to storage
    chart_storage["chart_string_indices"] = string_index_chart

    # Call the service - should handle string indices gracefully
    result = chart_comparison_service.compare_charts("chart_123", "chart_string_indices")

    # Verify the result doesn't have an error
    assert isinstance(result, ChartComparisonResponse)
    assert result.chart1_id == "chart_123"
    assert result.chart2_id == "chart_string_indices"
    assert result.summary is None  # No error summary for "differences" type

def test_compare_charts_with_missing_data(setup_chart_storage, chart_comparison_service):
    """Test comparing charts with missing data fields"""
    # Create a chart with missing data that would previously cause errors
    incomplete_chart = {
        "chart_id": "chart_incomplete",
        # Missing birth_details
        # Missing ascendant
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "degree": 10.5}  # Missing house
        ]
        # Missing houses
    }

    # Add the incomplete chart to storage
    chart_storage["chart_incomplete"] = incomplete_chart

    # Call the service - should handle missing data gracefully
    result = chart_comparison_service.compare_charts("chart_123", "chart_incomplete")

    # Verify the result
    assert isinstance(result, ChartComparisonResponse)
    assert result.chart1_id == "chart_123"
    assert result.chart2_id == "chart_incomplete"
    assert len(result.differences) >= 0  # May or may not have differences
