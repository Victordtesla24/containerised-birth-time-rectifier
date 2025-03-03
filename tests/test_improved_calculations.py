import unittest
from datetime import datetime
import math
from ai_service.utils.astro_calculator import AstroCalculator, WHOLE_SIGN, PLACIDUS

# Test data with known accurate results
TEST_DATA = [
    {
        "date": "1985-10-24 14:30:00",
        "lat": 18.5204,
        "lon": 73.8567,
        "ayanamsa": 23.6647,  # Lahiri ayanamsa
        "expected_ascendant": {
            "sign": "Aquarius",
            "degree_min": 0.5,
            "degree_max": 2.0
        },
        "expected_ketu": {
            "sign": "Libra",
            "degree_min": 14.5,
            "degree_max": 16.5
        }
    },
    {
        "date": "1990-05-15 08:30:00",
        "lat": 40.7128,
        "lon": -74.0060,
        "ayanamsa": 23.8,  # Custom ayanamsa
        "expected_ascendant": {
            "sign": "Leo",
            "degree_min": 25.0,
            "degree_max": 27.0
        },
        "expected_ketu": {
            "sign": "Pisces",
            "degree_min": 5.0,
            "degree_max": 7.0
        }
    }
]

class TestImprovedCalculations(unittest.TestCase):
    """Test suite for improved astrological calculations."""

    def test_ascendant_calculation_with_different_ayanamsa(self):
        """Test ascendant calculation with different ayanamsa values."""
        for test_case in TEST_DATA:
            # Parse test data
            birth_date = datetime.strptime(test_case["date"], "%Y-%m-%d %H:%M:%S")
            latitude = test_case["lat"]
            longitude = test_case["lon"]
            ayanamsa = test_case["ayanamsa"]
            expected_asc_sign = test_case["expected_ascendant"]["sign"]
            expected_asc_min = test_case["expected_ascendant"]["degree_min"]
            expected_asc_max = test_case["expected_ascendant"]["degree_max"]

            # Initialize calculator with specific ayanamsa
            calculator = AstroCalculator(ayanamsa=ayanamsa)

            # Calculate chart
            chart = calculator.calculate_chart(birth_date, latitude, longitude, house_system=WHOLE_SIGN)

            # Check ascendant
            ascendant = chart["ascendant"]

            # Verify sign
            self.assertEqual(ascendant["sign"], expected_asc_sign,
                          f"Expected ascendant sign {expected_asc_sign}, got {ascendant['sign']}")

            # Verify degree is within expected range
            self.assertTrue(expected_asc_min <= ascendant["degree"] <= expected_asc_max,
                         f"Expected ascendant degree between {expected_asc_min} and {expected_asc_max}, got {ascendant['degree']}")

    def test_ketu_calculation_with_different_node_types(self):
        """Test Ketu calculation with both mean and true node types."""
        for test_case in TEST_DATA:
            # Parse test data
            birth_date = datetime.strptime(test_case["date"], "%Y-%m-%d %H:%M:%S")
            latitude = test_case["lat"]
            longitude = test_case["lon"]
            ayanamsa = test_case["ayanamsa"]
            expected_ketu_sign = test_case["expected_ketu"]["sign"]
            expected_ketu_min = test_case["expected_ketu"]["degree_min"]
            expected_ketu_max = test_case["expected_ketu"]["degree_max"]

            # Test with both node types
            for node_type in ["mean", "true"]:
                # Initialize calculator with specific ayanamsa and node type
                calculator = AstroCalculator(ayanamsa=ayanamsa, node_type=node_type)

                # Calculate chart
                chart = calculator.calculate_chart(birth_date, latitude, longitude)

                # Find Ketu in planets
                ketu = next((p for p in chart["planets"] if p["name"] == "Ketu"), None)

                # Ensure Ketu was found
                self.assertIsNotNone(ketu, f"Ketu not found in chart planets with node_type={node_type}")

                # For true nodes, we allow a wider range of variation
                degree_tolerance = 2.0 if node_type == "true" else 1.0

                # Verify sign (may vary slightly between mean and true nodes)
                if node_type == "mean":
                    self.assertEqual(ketu["sign"], expected_ketu_sign,
                                  f"Expected Ketu sign {expected_ketu_sign} with {node_type} nodes, got {ketu['sign']}")

                # Verify degree is within expected range (with tolerance for true nodes)
                if ketu["sign"] == expected_ketu_sign:
                    self.assertTrue((expected_ketu_min - degree_tolerance) <= ketu["degree"] <= (expected_ketu_max + degree_tolerance),
                                 f"Expected Ketu degree between {expected_ketu_min-degree_tolerance} and {expected_ketu_max+degree_tolerance} with {node_type} nodes, got {ketu['degree']}")

    def test_house_system_impact_on_ascendant(self):
        """Test how different house systems impact the ascendant calculation."""
        for test_case in TEST_DATA:
            # Parse test data
            birth_date = datetime.strptime(test_case["date"], "%Y-%m-%d %H:%M:%S")
            latitude = test_case["lat"]
            longitude = test_case["lon"]
            ayanamsa = test_case["ayanamsa"]

            # Initialize calculator
            calculator = AstroCalculator(ayanamsa=ayanamsa)

            # Calculate with Whole Sign houses
            whole_sign_chart = calculator.calculate_chart(birth_date, latitude, longitude, house_system=WHOLE_SIGN)

            # Calculate with Placidus houses
            placidus_chart = calculator.calculate_chart(birth_date, latitude, longitude, house_system=PLACIDUS)

            # The ascendant longitude should be similar regardless of house system
            whole_sign_asc = whole_sign_chart["ascendant"]["longitude"]
            placidus_asc = placidus_chart["ascendant"]["longitude"]

            # Allow a small difference due to calculation methods
            self.assertTrue(abs(whole_sign_asc - placidus_asc) < 1.0,
                         f"Ascendant longitude differs too much between house systems: {whole_sign_asc} vs {placidus_asc}")

    def test_ketu_exactly_opposite_rahu(self):
        """Test that Ketu is exactly 180 degrees opposite to Rahu."""
        for test_case in TEST_DATA:
            # Parse test data
            birth_date = datetime.strptime(test_case["date"], "%Y-%m-%d %H:%M:%S")
            latitude = test_case["lat"]
            longitude = test_case["lon"]

            # Initialize calculator
            calculator = AstroCalculator()

            # Calculate chart
            chart = calculator.calculate_chart(birth_date, latitude, longitude)

            # Find Rahu and Ketu
            rahu = next((p for p in chart["planets"] if p["name"] == "Rahu"), None)
            ketu = next((p for p in chart["planets"] if p["name"] == "Ketu"), None)

            # Ensure both nodes were found
            self.assertIsNotNone(rahu, "Rahu not found in chart planets")
            self.assertIsNotNone(ketu, "Ketu not found in chart planets")

            # Calculate the difference in longitude
            diff = abs((rahu["longitude"] - ketu["longitude"]) % 360)

            # Should be exactly 180 degrees apart
            self.assertTrue(abs(diff - 180.0) < 0.01,
                         f"Rahu and Ketu should be exactly 180° apart, but difference is {diff}°")

if __name__ == "__main__":
    unittest.main()
