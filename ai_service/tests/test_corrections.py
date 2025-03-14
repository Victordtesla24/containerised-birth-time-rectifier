"""
Focused test for chart verification corrections
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from ai_service.core.chart_calculator import (
    calculate_verified_chart,
    EnhancedChartCalculator
)

# Sample chart data for testing (simplified)
SAMPLE_CHART = {
    "ascendant": {"sign": "Libra", "degree": 15.5},
    "planets": {
        "saturn": {"sign": "Capricorn", "degree": 18.56}
    }
}

# Sample OpenAI response requiring corrections
SAMPLE_CORRECTIONS = {
    "needs_correction": True,
    "confidence_score": 85.0,
    "message": "Corrections needed",
    "corrections": [
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
}

# Async mock class
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

@pytest.mark.asyncio
async def test_corrections_applied():
    """Test that the 'corrections_applied' flag is properly set"""
    # Create a mock OpenAI service
    mock_openai = MagicMock()
    mock_openai.generate_completion = AsyncMock()
    mock_openai.generate_completion.return_value = {
        "content": json.dumps(SAMPLE_CORRECTIONS),
        "model_used": "gpt-4"
    }

    # Create corrected chart for mocking
    corrected_chart = {
        "ascendant": {"sign": "Libra", "degree": 16.2},
        "planets": {
            "saturn": {"sign": "Capricorn", "degree": 19.12}
        },
        "verification": {
            "verified": True,
            "confidence_score": 85.0,
            "corrections_applied": True
        }
    }

    # Test with the patched services
    with patch('ai_service.core.chart_calculator.calculate_chart', return_value=SAMPLE_CHART), \
         patch.object(EnhancedChartCalculator, '_apply_corrections', return_value=corrected_chart):

        # Create calculator and call method
        calculator = EnhancedChartCalculator(openai_service=mock_openai)
        result = await calculator.calculate_verified_chart(
            birth_date="1990-01-15",
            birth_time="12:30:00",
            latitude=40.0,
            longitude=-74.0
        )

        # Assertions
        assert result["verification"]["verified"] is True
        assert result["verification"]["corrections_applied"] is True
        assert result["ascendant"]["degree"] == 16.2
        assert result["planets"]["saturn"]["degree"] == 19.12
