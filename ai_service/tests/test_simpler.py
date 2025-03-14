"""
Simpler tests for chart verification with OpenAI using direct mocking
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
import copy
import json

from ai_service.core.chart_calculator import (
    calculate_verified_chart,
    EnhancedChartCalculator
)

# Sample chart data
SAMPLE_CHART = {
    "ascendant": {
        "sign": "Libra",
        "degree": 15.5
    },
    "planets": {
        "saturn": {
            "sign": "Capricorn",
            "degree": 18.56
        }
    },
    "verification": {
        "verified": True,
        "confidence_score": 90.0,
        "corrections_applied": False
    }
}

# Sample corrections
CORRECTIONS_DATA = [
    {
        "type": "planet",
        "name": "saturn",
        "corrected": {"degree": 19.12}
    },
    {
        "type": "ascendant",
        "name": "ascendant",
        "corrected": {"degree": 16.2}
    }
]

# Create a corrected chart for testing
CORRECTED_CHART = copy.deepcopy(SAMPLE_CHART)
CORRECTED_CHART["planets"]["saturn"]["degree"] = 19.12
CORRECTED_CHART["ascendant"]["degree"] = 16.2
CORRECTED_CHART["verification"]["corrections_applied"] = True


class AsyncMock(MagicMock):
    """Mock for async functions"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.mark.asyncio
async def test_apply_corrections():
    """Test that corrections are properly applied to chart data"""
    # Create an instance of EnhancedChartCalculator
    calculator = EnhancedChartCalculator()

    # Apply corrections to the chart
    result = calculator._apply_corrections(SAMPLE_CHART, CORRECTIONS_DATA)

    # Verify the corrections were applied
    assert result["planets"]["saturn"]["degree"] == 19.12
    assert result["ascendant"]["degree"] == 16.2
    assert result["verification"]["corrections_applied"] is True


@pytest.mark.asyncio
async def test_chart_verification_with_mock():
    """Test chart verification with completely mocked dependencies"""
    # Create our mocks
    mock_openai = MagicMock()
    mock_openai.generate_completion = AsyncMock()

    # Set up the mock OpenAI service response
    verification_response = {
        "needs_correction": True,
        "confidence_score": 85.0,
        "message": "Corrections needed",
        "corrections": CORRECTIONS_DATA
    }

    mock_openai.generate_completion.return_value = {
        "content": json.dumps(verification_response),
        "model_used": "gpt-4"
    }

    # Create calculator with our mock
    calculator = EnhancedChartCalculator(openai_service=mock_openai)

    # Also mock the _apply_corrections method to return our pre-corrected chart
    calculator._apply_corrections = MagicMock(return_value=CORRECTED_CHART)

    # Mock the initial chart calculation to return our sample chart
    with patch('ai_service.core.chart_calculator.calculate_chart', return_value=SAMPLE_CHART):
        # Call the function
        result = await calculator.calculate_verified_chart(
            birth_date="1990-01-15",
            birth_time="14:30:00",
            latitude=40.0,
            longitude=-74.0
        )

        # Verify the result
        assert result["verification"]["confidence_score"] == 85.0  # Matches the mocked verification response
        assert result["verification"]["corrections_applied"] is True
        assert result["planets"]["saturn"]["degree"] == 19.12
        assert result["ascendant"]["degree"] == 16.2

        # Verify our methods were called
        mock_openai.generate_completion.assert_called_once()
        calculator._apply_corrections.assert_called_once()
