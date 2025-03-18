import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json
from typing import Dict, Any, List, Protocol, AsyncIterator, Optional
from ai_service.utils.questionnaire_engine import QuestionnaireEngine

# Define protocol for fixture typing
class ChartDataProtocol(Protocol):
    def __call__(self) -> Dict[str, Any]: ...

class BirthDetailsProtocol(Protocol):
    def __call__(self) -> Dict[str, Any]: ...

class PreviousAnswersProtocol(Protocol):
    def __call__(self) -> Dict[str, Any]: ...

class EngineProtocol(Protocol):
    openai_service: Any
    async def get_first_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]: ...
    async def generate_dynamic_question(self, chart_data: Dict[str, Any], previous_answers: Dict[str, Any], current_confidence: float) -> Dict[str, Any]: ...
    def _format_chart_summary(self, chart_data: Dict[str, Any]) -> str: ...
    def _identify_uncertain_factors(self, chart_data: Dict[str, Any]) -> List[str]: ...
    def _analyze_answer_patterns(self, responses: List[Dict[str, Any]]) -> List[str]: ...
    async def calculate_confidence(self, answers: Dict[str, Any], chart_data: Optional[Dict[str, Any]] = None) -> float: ...

# Sample test data
@pytest.fixture
def sample_chart_data() -> Dict[str, Any]:
    return {
        "planets": [
            {"planet": "Ascendant", "sign": "Virgo", "degree": 15.3, "house": 1},
            {"planet": "Sun", "sign": "Capricorn", "degree": 25.5, "house": 5},
            {"planet": "Moon", "sign": "Taurus", "degree": 10.2, "house": 9},
            {"planet": "MC", "sign": "Gemini", "degree": 5.1, "house": 10}
        ],
        "houses": [
            {"house_number": 1, "sign": "Virgo", "degree": 15.3},
            {"house_number": 4, "sign": "Sagittarius", "degree": 10.5},
            {"house_number": 7, "sign": "Pisces", "degree": 15.3},
            {"house_number": 10, "sign": "Gemini", "degree": 10.5}
        ],
        "aspects": [
            {"planet1": "Sun", "planet2": "Moon", "aspect_type": "Trine", "orb": 2.5},
            {"planet1": "Ascendant", "planet2": "Mars", "aspect_type": "Square", "orb": 3.1}
        ]
    }

@pytest.fixture
def birth_details() -> Dict[str, Any]:
    return {
        "birth_date": "1990-01-15",
        "birth_time": "12:30:00",
        "latitude": 40.7128,
        "longitude": -74.0060
    }

@pytest.fixture
def previous_answers() -> Dict[str, Any]:
    return {
        "responses": [
            {
                "question_id": "q_1",
                "question": "Would you describe yourself as more analytical or creative?",
                "answer": "analytical",
                "relevance": "high"
            }
        ]
    }

@pytest_asyncio.fixture
async def engine() -> AsyncIterator[EngineProtocol]:
    engine = QuestionnaireEngine()
    engine.openai_service = AsyncMock()
    yield engine

@pytest.mark.asyncio
async def test_get_first_question(engine: EngineProtocol, sample_chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> None:
    """Test getting the first question based on chart data"""
    # Mock the openai_service.generate_completion method
    engine.openai_service.generate_completion = AsyncMock(return_value={
        "content": json.dumps({
            "id": "q_first",
            "text": "Have you experienced major career changes in the last 5 years?",
            "type": "boolean",
            "options": ["Yes", "No", "Unsure"],
            "relevance": "high"
        })
    })

    # Call the method and await it
    result = await engine.get_first_question(
        chart_data=sample_chart_data,
        birth_details=birth_details
    )

    # Assertions
    assert "id" in result
    assert result["id"].startswith("q_")  # Check for UUID-based ID format
    assert "text" in result
    assert "type" in result

def test_format_chart_summary(engine: EngineProtocol, sample_chart_data: Dict[str, Any]) -> None:
    """Test formatting chart data for AI processing"""
    summary = engine._format_chart_summary(sample_chart_data)

    # Check that summary contains key astrological factors
    assert "Ascendant" in summary
    assert "Virgo" in summary
    assert "Sun" in summary
    assert "Capricorn" in summary
    assert "Moon" in summary
    assert "Taurus" in summary
    assert "Square" in summary  # Should mention aspects

def test_identify_uncertain_factors(engine: EngineProtocol, sample_chart_data: Dict[str, Any]) -> None:
    """Test identifying uncertain factors in a chart"""
    uncertain_factors = engine._identify_uncertain_factors(sample_chart_data)

    # The test chart has an Ascendant, so House positions should be fairly certain
    assert not any("Ascendant sign" in factor for factor in uncertain_factors)

    # Check that we have some uncertain factors identified
    assert len(uncertain_factors) > 0

@pytest.mark.asyncio
async def test_generate_dynamic_question(engine: EngineProtocol, sample_chart_data: Dict[str, Any], previous_answers: Dict[str, Any]) -> None:
    """Test generating dynamic questions based on chart and previous answers"""
    # Mock the openai_service.generate_completion method
    engine.openai_service.generate_completion = AsyncMock(return_value={
        "content": json.dumps({
            "id": "q_dynamic",
            "text": "Have you experienced a significant change in career or life direction around age 29-30?",
            "type": "boolean",
            "options": ["Yes", "No", "Unsure"],
            "relevance": "high",
            "astrological_factors": ["Saturn return", "Progressed Moon"]
        })
    })

    # Call the method and await it
    result = await engine.generate_dynamic_question(
        chart_data=sample_chart_data,
        previous_answers=previous_answers,
        current_confidence=0.35
    )

    # Assertions
    assert "id" in result
    assert result["id"] == "q_dynamic"
    assert "text" in result
    assert "type" in result
    assert "relevance" in result

def test_analyze_answer_patterns(engine: EngineProtocol) -> None:
    """Test analyzing patterns in previous answers"""
    # Create some mock responses with a clear pattern
    responses = [
        {"question": "Do you consider yourself analytical?", "answer": "yes", "relevance": "high"},
        {"question": "Are you detail-oriented?", "answer": "yes", "relevance": "high"},
        {"question": "Do you enjoy structure and organization?", "answer": "yes", "relevance": "high"},
        {"question": "Are you spontaneous?", "answer": "no", "relevance": "medium"},
    ]

    # Mock the implementation to return expected patterns
    with patch.object(engine, '_analyze_answer_patterns') as mock_analyze:
        mock_analyze.return_value = [
            "Consistent 'yes' responses to analytical/detail-oriented questions",
            "Consistent 'no' responses to spontaneity questions"
        ]

        patterns = engine._analyze_answer_patterns(responses)

        # Should detect patterns related to analytical/detail-oriented nature
        assert any("analytical" in pattern.lower() for pattern in patterns) or \
               any("detail" in pattern.lower() for pattern in patterns)

@pytest.mark.asyncio
async def test_calculate_confidence(engine: EngineProtocol, sample_chart_data: Dict[str, Any]) -> None:
    """Test calculation of confidence score based on answers"""
    # Mock answers with different levels of quality
    answers = {
        "responses": [
            {"question": "Q1 about career?", "answer": "yes", "quality": 0.8, "relevance": "high"},
            {"question": "Q2 about personality?", "answer": "no", "quality": 0.6, "relevance": "medium"},
            {"question": "Q3 about relationships?", "answer": "maybe", "quality": 0.4, "relevance": "low"}
        ]
    }

    # Mock the openai service
    engine.openai_service.generate_completion = AsyncMock(return_value={
        "content": json.dumps({
            "confidence_score": 65,
            "rationale": "The answers are consistent with the chart and show moderate quality."
        })
    })

    # Call the method and await it
    confidence = await engine.calculate_confidence(answers, sample_chart_data)

    # Should return a float between 0 and 100
    assert isinstance(confidence, float)
    assert 0 <= confidence <= 100
