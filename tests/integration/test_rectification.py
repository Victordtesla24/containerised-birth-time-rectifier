"""
Integration tests for birth time rectification.
These tests validate the rectification functionality against the sequence diagram flow.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, List, Tuple

from ai_service.core.rectification import (
    rectify_birth_time,
    extract_life_events_from_answers,
    calculate_chart,
    comprehensive_rectification
)
from ai_service.api.services.openai.service import OpenAIService

@pytest.fixture
async def openai_service():
    """Create a real OpenAI service."""
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not available")
    return OpenAIService()

@pytest.mark.asyncio
async def test_extract_life_events_from_answers():
    """Test extracting life events from questionnaire answers."""
    # Create test answers with embedded life events
    answers = [
        {
            "question": "When did you get married?",
            "answer": "I got married on 2015-06-15 in a beautiful ceremony."
        },
        {
            "question": "Have you experienced any major career changes?",
            "answer": "Yes, I changed careers in 2018 from teaching to software engineering."
        },
        {
            "question": "Did you ever relocate to a different city?",
            "answer": "I moved from New York to San Francisco at age 25."
        },
        {
            "question": "Have you experienced any health challenges?",
            "answer": "I was diagnosed with a minor condition in 2020 but recovered fully."
        }
    ]

    # Extract life events
    life_events = extract_life_events_from_answers(answers)

    # Verify life events were extracted
    assert isinstance(life_events, list)
    assert len(life_events) > 0

    # Verify structure of extracted events
    for event in life_events:
        assert "event_type" in event
        assert "event_date" in event
        assert "description" in event
        assert "confidence" in event

    # Verify specific events were extracted correctly
    marriage_event = next((e for e in life_events if e["event_type"] == "marriage"), None)
    assert marriage_event is not None

    career_event = next((e for e in life_events if e["event_type"] == "career_change"), None)
    assert career_event is not None

    relocation_event = next((e for e in life_events if e["event_type"] == "relocation"), None)
    assert relocation_event is not None

    health_event = next((e for e in life_events if e["event_type"] == "major_illness"), None)
    assert health_event is not None

@pytest.mark.asyncio
async def test_calculate_chart():
    """Test calculation of astrological chart."""
    # Test data
    birth_date = datetime(1990, 1, 1, 12, 0)
    latitude = 40.7128  # New York
    longitude = -74.0060
    timezone_str = "America/New_York"

    # Calculate chart
    chart = calculate_chart(birth_date, latitude, longitude, timezone_str)

    # Verify chart was calculated
    assert chart is not None

    # Verify basic chart functionality
    sun = chart.getObject("Sun")
    assert sun is not None
    assert hasattr(sun, "lon")
    assert 0 <= sun.lon < 360

    # Check house system
    ascendant = chart.getAngle("Asc")
    assert ascendant is not None
    assert hasattr(ascendant, "lon")
    assert 0 <= ascendant.lon < 360

    # Check houses
    for i in range(1, 13):
        house = chart.getHouse(i)
        assert house is not None
        assert hasattr(house, "lon")
        assert 0 <= house.lon < 360

@pytest.mark.asyncio
async def test_rectify_birth_time_basic(openai_service):
    """Test birth time rectification with minimal inputs."""
    # Test data - Birth in New York at 12:00
    birth_dt = datetime(1990, 1, 1, 12, 0)
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Basic answers
    answers = [
        {
            "question": "Were you born during daylight hours?",
            "answer": "Yes, I was born during the day."
        },
        {
            "question": "When did you get married?",
            "answer": "I got married on 2015-06-15."
        },
        {
            "question": "Have you ever relocated to a different city?",
            "answer": "Yes, I moved to Chicago in 2018."
        }
    ]

    # Rectify birth time
    rectified_time, confidence = await rectify_birth_time(
        birth_dt=birth_dt,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        answers=answers
    )

    # Verify rectified time
    assert isinstance(rectified_time, datetime)
    assert isinstance(confidence, float)

    # Verify confidence is in reasonable range
    assert 0 <= confidence <= 100

    # Verify rectified time is within a reasonable range (not more than 6 hours from input)
    time_difference = abs((rectified_time - birth_dt).total_seconds())
    assert time_difference <= 6 * 3600  # 6 hours in seconds

@pytest.mark.asyncio
async def test_comprehensive_rectification(openai_service):
    """Test comprehensive birth time rectification with life events."""
    # Test data - Birth in New York at estimated time 12:00
    birth_dt = datetime(1990, 1, 1, 12, 0)
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Create detailed answers with life events
    answers = [
        {
            "question": "Were you born during daylight hours?",
            "answer": "Yes, I believe I was born around noon."
        },
        {
            "question": "When did you get married?",
            "answer": "I got married on 2015-06-15 in a beautiful ceremony."
        },
        {
            "question": "Have you experienced any major career changes?",
            "answer": "Yes, I changed careers in 2018 from teaching to software engineering."
        },
        {
            "question": "Did you ever relocate to a different city?",
            "answer": "I moved from New York to San Francisco in 2012-03."
        },
        {
            "question": "Have you had any children?",
            "answer": "I had my first child on 2020-04-10."
        }
    ]

    # Extract life events
    events = extract_life_events_from_answers(answers)

    # Verify events extraction
    assert len(events) > 0

    # Comprehensive rectification
    result = await comprehensive_rectification(
        birth_dt=birth_dt,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        answers=answers,
        events=events
    )

    # Verify result structure
    assert isinstance(result, dict)
    assert "rectified_time" in result
    assert "confidence" in result
    assert "methods" in result
    assert "explanation" in result

    # Verify rectified time
    rectified_time = result["rectified_time"]
    confidence = result["confidence"]

    assert isinstance(rectified_time, (datetime, str))
    assert isinstance(confidence, float)

    # Verify methods used
    methods = result["methods"]
    assert isinstance(methods, list)
    assert len(methods) > 0

    # Verify explanation
    explanation = result["explanation"]
    assert isinstance(explanation, str)
    assert len(explanation) > 0

@pytest.mark.asyncio
async def test_rectification_sequence(openai_service):
    """Test the full birth time rectification sequence as per the sequence diagram."""
    # Step 1: User provides birth details and questionnaire answers
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Convert strings to datetime
    birth_dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M:%S")
    tz = pytz.timezone(timezone)
    birth_dt = tz.localize(birth_dt)

    # Step 2: Create questionnaire answers
    answers = [
        {
            "question": "Were you born during daylight hours?",
            "answer": "Yes, my mother said I was born around noon."
        },
        {
            "question": "Have you experienced any significant career changes?",
            "answer": "I changed careers from teaching to programming in 2016."
        },
        {
            "question": "When did you get married?",
            "answer": "I got married on June 15, 2015."
        },
        {
            "question": "Have you had any children?",
            "answer": "I had my first child on April 10, 2020."
        }
    ]

    # Step 3: Extract life events from answers
    events = extract_life_events_from_answers(answers)

    # Verify events extraction
    assert len(events) > 0

    # Step 4: Perform comprehensive rectification
    result = await comprehensive_rectification(
        birth_dt=birth_dt,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        answers=answers,
        events=events
    )

    # Verify result contains all expected components
    assert "rectified_time" in result
    assert "confidence" in result
    assert "methods" in result
    assert "explanation" in result
    assert "supporting_evidence" in result

    # Verify rectified time is reasonable
    rectified_time = result["rectified_time"]
    if isinstance(rectified_time, datetime):
        # Calculate time difference in hours
        diff_hours = abs((rectified_time - birth_dt).total_seconds() / 3600)
        # Rectification typically doesn't shift by more than 6 hours
        assert diff_hours <= 6
    elif isinstance(rectified_time, str):
        # If returned as a string, should contain time information
        assert ":" in rectified_time

    # Verify confidence is in reasonable range
    confidence = result["confidence"]
    assert 0 <= confidence <= 100

    # Verify methods list is not empty
    assert len(result["methods"]) > 0

    # Verify explanation and supporting evidence
    assert len(result["explanation"]) > 0
    assert "supporting_evidence" in result

    # Output result summary
    print(f"\nRectification result:")
    print(f"Original birth time: {birth_time}")
    print(f"Rectified time: {rectified_time}")
    print(f"Confidence: {confidence}%")
    print(f"Methods used: {', '.join(result['methods'])}")
    print(f"Explanation summary: {result['explanation'][:100]}...")
