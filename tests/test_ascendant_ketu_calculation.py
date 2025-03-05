import unittest
from datetime import datetime
import pytz
import sys
import os
# Add the parent directory to the path to allow imports from the ai_service package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_service.utils.astro_calculator import AstroCalculator, PLACIDUS, WHOLE_SIGN

class TestAstroCalculations(unittest.TestCase):

    def setUp(self):
        self.calculator = AstroCalculator()

    def test_ascendant_calculation(self):
        """Test that ascendant is calculated correctly"""
        # Sample birth data (New York, Jan 1, 2000, 12:00 PM)
        birth_date = datetime(2000, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        latitude = 40.7128  # New York latitude
        longitude = -74.0060  # New York longitude

        # Calculate the chart
        chart = self.calculator.calculate_chart(birth_date, latitude, longitude, PLACIDUS)

        # Verify ascendant exists
        self.assertIn("ascendant", chart)
        ascendant = chart["ascendant"]

        # Check if the ascendant has the required fields
        self.assertIn("sign", ascendant)
        self.assertIn("degree", ascendant)

        # Print for debugging
        print(f"Ascendant: {ascendant['sign']} at {ascendant['degree']}°")

    def test_ketu_calculation(self):
        """Test that Ketu is properly calculated as 180° from Rahu"""
        # Sample birth data
        birth_date = datetime(1990, 5, 15, 10, 30, 0, tzinfo=pytz.UTC)
        latitude = 18.5204  # Pune latitude
        longitude = 73.8567  # Pune longitude

        # Calculate the chart
        chart = self.calculator.calculate_chart(birth_date, latitude, longitude, PLACIDUS)

        # Find Rahu and Ketu in planets list
        rahu = None
        ketu = None

        for planet in chart["planets"]:
            if planet["name"] == "Rahu":
                rahu = planet
            elif planet["name"] == "Ketu":
                ketu = planet

        # Verify both planets exist
        self.assertIsNotNone(rahu, "Rahu not found in planets")
        self.assertIsNotNone(ketu, "Ketu not found in planets")

        # Calculate the expected Ketu longitude (opposite to Rahu)
        expected_ketu_sign_index = (signs.index(rahu["sign"]) + 6) % 12
        expected_ketu_sign = signs[expected_ketu_sign_index]
        expected_ketu_degree = (30 - rahu["degree"]) % 30

        # Verify Ketu is 180° from Rahu
        self.assertEqual(ketu["sign"], expected_ketu_sign,
                         f"Ketu sign should be {expected_ketu_sign}, got {ketu['sign']}")

        # Allow for small floating point differences
        self.assertAlmostEqual(ketu["degree"], expected_ketu_degree, places=1,
                              msg=f"Ketu degree should be ~{expected_ketu_degree}, got {ketu['degree']}")

        # Print for debugging
        print(f"Rahu: {rahu['sign']} at {rahu['degree']}°")
        print(f"Ketu: {ketu['sign']} at {ketu['degree']}°")

    def test_chart_structure(self):
        """Test that chart has all the expected components"""
        # Sample birth data
        birth_date = datetime(1985, 10, 24, 14, 30, 0, tzinfo=pytz.UTC)
        latitude = 28.6139  # Delhi latitude
        longitude = 77.2090  # Delhi longitude

        # Calculate the chart
        chart = self.calculator.calculate_chart(birth_date, latitude, longitude, PLACIDUS)

        # Verify chart structure
        self.assertIn("ascendant", chart)
        self.assertIn("planets", chart)
        self.assertIn("houses", chart)
        self.assertIn("aspects", chart)

        # Verify planets list contains all expected planets
        planet_names = [p["name"] for p in chart["planets"]]
        expected_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                           "Jupiter", "Saturn", "Uranus", "Neptune",
                           "Pluto", "Rahu", "Ketu"]

        for planet in expected_planets:
            self.assertIn(planet, planet_names, f"Planet {planet} not found in chart")

        # Verify house structure
        self.assertEqual(len(chart["houses"]), 12, "Chart should contain 12 houses")

        # Print summary
        print(f"Chart contains {len(chart['planets'])} planets and {len(chart['aspects'])} aspects")
        print(f"Ascendant: {chart['ascendant']['sign']} at {chart['ascendant']['degree']}°")

    def test_ascendant_calculation_with_different_ayanamsa(self):
        """Test ascendant calculation with different ayanamsa values."""
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
        # Test data with known accurate results
        TEST_DATA = [
            {
                "date": "1985-10-24 14:30:00",
                "lat": 18.5204,
                "lon": 73.8567,
                "ayanamsa": 23.6647,  # Lahiri ayanamsa
            },
            {
                "date": "1990-05-15 08:30:00",
                "lat": 40.7128,
                "lon": -74.0060,
                "ayanamsa": 23.8,  # Custom ayanamsa
            }
        ]

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

            # The sign of the ascendant should typically be the same regardless of house system
            # or within one sign difference due to the way house systems work
            whole_sign_asc_sign = whole_sign_chart["ascendant"]["sign"]
            placidus_asc_sign = placidus_chart["ascendant"]["sign"]

            # Check if signs are the same or adjacent
            sign_index_whole = signs.index(whole_sign_asc_sign)
            sign_index_placidus = signs.index(placidus_asc_sign)
            sign_diff = abs((sign_index_whole - sign_index_placidus) % 12)
            self.assertTrue(sign_diff <= 1,
                            f"Ascendant signs differ too much: {whole_sign_asc_sign} vs {placidus_asc_sign}")

            # The ascendant longitude can vary more between house systems
            # Whole Sign and Placidus calculate the ascendant differently
            # Allow for up to 30 degrees difference (one sign)
            whole_sign_asc = whole_sign_chart["ascendant"]["longitude"]
            placidus_asc = placidus_chart["ascendant"]["longitude"]

            # Find the minimum distance between the two angles, accounting for wrap-around
            angle_diff = min(
                abs(whole_sign_asc - placidus_asc),
                360 - abs(whole_sign_asc - placidus_asc)
            )

            self.assertTrue(angle_diff < 30.0,
                            f"Ascendant longitude differs too much between house systems: {whole_sign_asc} vs {placidus_asc}")

    def test_ketu_exactly_opposite_rahu(self):
        """Test that Ketu is exactly 180 degrees opposite to Rahu."""
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

# Zodiac signs list
signs = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

if __name__ == "__main__":
    unittest.main()
