"""
Test module for chart_calculator.py
Tests the accuracy of astrological calculations, especially Ketu and Ascendant positions
"""

import datetime
import math
from ai_service.core.chart_calculator import (
    calculate_chart,
    calculate_ketu_position,
    calculate_ascendant,
    julian_day_ut,
    get_zodiac_sign,
    normalize_longitude
)

# Test data from a verified chart for comparison
TEST_CHART_DATA = {
    "date": "1990-01-15",
    "time": "12:30:00",
    "latitude": 28.6139,  # Delhi, India
    "longitude": 77.2090,
    "expected_ascendant_sign": "Aries",
    "expected_ketu_sign": "Virgo",
    "expected_ketu_longitude": 164.32,  # Approximate value
    "expected_house_system": "placidus",
    "expected_ayanamsa": 23.6647,  # Lahiri ayanamsa
    "expected_node_type": "true"
}

def test_ketu_position_calculation():
    """Test that Ketu's position is calculated correctly (opposite to Rahu)"""
    # Create a test datetime for calculation
    dt = datetime.datetime.strptime(
        f"{TEST_CHART_DATA['date']} {TEST_CHART_DATA['time']}",
        '%Y-%m-%d %H:%M:%S'
    )

    # Calculate Julian day
    jd_ut = julian_day_ut(dt)

    # Calculate Ketu position
    ketu_data = calculate_ketu_position(jd_ut, node_type=TEST_CHART_DATA["expected_node_type"])

    # Test that Ketu longitude is normalized and within acceptable range
    assert 0 <= ketu_data["longitude"] < 360, "Ketu longitude should be normalized between 0 and 360"

    # Test that Ketu is in the expected sign
    sign, _ = get_zodiac_sign(ketu_data["longitude"])
    assert sign == TEST_CHART_DATA["expected_ketu_sign"], f"Expected Ketu in {TEST_CHART_DATA['expected_ketu_sign']} but got {sign}"

    # Test Ketu longitude is within acceptable range of expected value (±1 degree tolerance)
    tolerance = 1.0
    assert abs(ketu_data["longitude"] - TEST_CHART_DATA["expected_ketu_longitude"]) <= tolerance, \
           f"Ketu longitude {ketu_data['longitude']} differs from expected {TEST_CHART_DATA['expected_ketu_longitude']} by more than {tolerance} degrees"

def test_ascendant_calculation():
    """Test that Ascendant is calculated correctly"""
    # Parse the date and time
    dt = datetime.datetime.strptime(
        f"{TEST_CHART_DATA['date']} {TEST_CHART_DATA['time']}",
        '%Y-%m-%d %H:%M:%S'
    )

    # Calculate Julian day
    jd_ut = julian_day_ut(dt)

    # Calculate Ascendant
    ascendant = calculate_ascendant(
        jd_ut,
        TEST_CHART_DATA["latitude"],
        TEST_CHART_DATA["longitude"]
    )

    # Get sign from longitude
    sign, _ = get_zodiac_sign(ascendant)

    # Test that Ascendant is in the expected sign
    assert sign == TEST_CHART_DATA["expected_ascendant_sign"], \
           f"Expected Ascendant in {TEST_CHART_DATA['expected_ascendant_sign']} but got {sign}"

def test_full_chart_calculation():
    """Test the full chart calculation with all components"""
    # Calculate the chart
    chart_data = calculate_chart(
        TEST_CHART_DATA["date"],
        TEST_CHART_DATA["time"],
        TEST_CHART_DATA["latitude"],
        TEST_CHART_DATA["longitude"],
        "Test Location",
        TEST_CHART_DATA["expected_house_system"],
        TEST_CHART_DATA["expected_ayanamsa"],
        TEST_CHART_DATA["expected_node_type"]
    )

    # Test that the chart contains all expected components
    assert "birth_details" in chart_data, "Chart should include birth details"
    assert "calculation_params" in chart_data, "Chart should include calculation parameters"
    assert "ascendant" in chart_data, "Chart should include ascendant data"
    assert "planets" in chart_data, "Chart should include planet data"
    assert "houses" in chart_data, "Chart should include house data"

    # Test Ketu presence and position
    assert "ketu" in chart_data["planets"], "Chart should include Ketu data"
    assert chart_data["planets"]["ketu"]["sign"] == TEST_CHART_DATA["expected_ketu_sign"], \
           f"Expected Ketu in {TEST_CHART_DATA['expected_ketu_sign']} but got {chart_data['planets']['ketu']['sign']}"

    # Test ascendant sign
    assert chart_data["ascendant"]["sign"] == TEST_CHART_DATA["expected_ascendant_sign"], \
           f"Expected Ascendant in {TEST_CHART_DATA['expected_ascendant_sign']} but got {chart_data['ascendant']['sign']}"

    # Test that house calculation is complete
    assert len(chart_data["houses"]) == 12, "Chart should have 12 houses"

    # Verify that planets have house positions
    for planet, data in chart_data["planets"].items():
        assert "house" in data, f"Planet {planet} should have a house position"
        assert 1 <= data["house"] <= 12, f"House position for {planet} should be between 1 and 12"

def test_chart_consistency():
    """Test the consistency of the chart calculation by comparing results for the same inputs"""
    # Calculate the chart twice with same inputs
    chart1 = calculate_chart(
        TEST_CHART_DATA["date"],
        TEST_CHART_DATA["time"],
        TEST_CHART_DATA["latitude"],
        TEST_CHART_DATA["longitude"]
    )

    chart2 = calculate_chart(
        TEST_CHART_DATA["date"],
        TEST_CHART_DATA["time"],
        TEST_CHART_DATA["latitude"],
        TEST_CHART_DATA["longitude"]
    )

    # Test that the results are identical
    assert chart1["ascendant"]["longitude"] == chart2["ascendant"]["longitude"], \
           "Repeated calculations should yield the same ascendant longitude"

    assert chart1["planets"]["ketu"]["longitude"] == chart2["planets"]["ketu"]["longitude"], \
           "Repeated calculations should yield the same Ketu longitude"

    # Check all planet positions are identical
    for planet in chart1["planets"]:
        assert chart1["planets"][planet]["longitude"] == chart2["planets"][planet]["longitude"], \
               f"Repeated calculations should yield the same longitude for {planet}"

def test_normalize_longitude():
    """Test that longitude normalization works correctly"""
    test_cases = [
        (0, 0),
        (180, 180),
        (359.99, 359.99),
        (360, 0),
        (361, 1),
        (720, 0),
        (-1, 359),
        (-180, 180),
        (-360, 0),
    ]

    for input_val, expected in test_cases:
        result = normalize_longitude(input_val)
        assert math.isclose(result, expected, abs_tol=1e-10), \
               f"normalize_longitude({input_val}) should return {expected}, got {result}"
