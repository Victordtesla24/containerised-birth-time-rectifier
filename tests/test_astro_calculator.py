import unittest
from datetime import datetime
import pytz
from ai_service.utils.astro_calculator import AstroCalculator, PLACIDUS

class TestAstroCalculator(unittest.TestCase):

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
        self.assertIn("ascendant", chart, "Chart should include ascendant data")
        ascendant = chart["ascendant"]

        # Check if the ascendant has the required fields
        self.assertIn("sign", ascendant, "Ascendant data should include zodiac sign")
        self.assertIn("degree", ascendant, "Ascendant data should include degree")

        # Ascendant should be a valid zodiac sign
        self.assertIn(ascendant["sign"], ZODIAC_SIGNS,
                      f"Ascendant sign {ascendant['sign']} should be a valid zodiac sign")

        # Ascendant degree should be between 0 and 30
        degree = ascendant["degree"]
        self.assertGreaterEqual(degree, 0, "Ascendant degree should be >= 0")
        self.assertLess(degree, 30, "Ascendant degree should be < 30")

        print(f"Ascendant: {ascendant['sign']} at {ascendant['degree']}°")

    def test_ketu_calculation(self):
        """Test that Ketu is properly calculated as 180° from Rahu"""
        # Sample birth data
        birth_date = datetime(1990, 5, 15, 10, 30, 0, tzinfo=pytz.UTC)
        latitude = 18.5204  # Pune latitude
        longitude = 73.8567  # Pune longitude

        # Calculate the chart
        chart = self.calculator.calculate_chart(birth_date, latitude, longitude, PLACIDUS)

        # Verify planets list exists
        self.assertIn("planets", chart, "Chart should include planets data")
        planets = chart["planets"]

        # Extract Rahu and Ketu from planets list
        rahu_planet = None
        ketu_planet = None
        for planet in planets:
            if planet["name"] == "Rahu":
                rahu_planet = planet
            elif planet["name"] == "Ketu":
                ketu_planet = planet

        # Verify both planets exist
        self.assertIsNotNone(rahu_planet, "Rahu should be included in the chart")
        self.assertIsNotNone(ketu_planet, "Ketu should be included in the chart")

        # Skip further tests if either planet is not found
        if not rahu_planet or not ketu_planet:
            self.skipTest("Rahu or Ketu not found in planets list")
            return

        # Get Rahu and Ketu signs and degrees
        rahu_sign = rahu_planet["sign"]
        rahu_degree = rahu_planet["degree"]
        ketu_sign = ketu_planet["sign"]
        ketu_degree = ketu_planet["degree"]

        # Validate Rahu and Ketu are in opposite signs (6 signs apart)
        rahu_sign_index = ZODIAC_SIGNS.index(rahu_sign)
        expected_ketu_sign_index = (rahu_sign_index + 6) % 12
        expected_ketu_sign = ZODIAC_SIGNS[expected_ketu_sign_index]

        self.assertEqual(ketu_sign, expected_ketu_sign,
                         f"Ketu sign should be {expected_ketu_sign} (opposite to Rahu's {rahu_sign})")

        # Validate Ketu's degree is approximately opposite to Rahu's within the sign
        # In traditional calculation, Ketu should be at the opposite degree as Rahu within the sign
        # This means if Rahu is at 11°, Ketu should be at 19° (30 - 11) in the opposite sign
        expected_ketu_degree = (30 - rahu_degree) % 30
        self.assertAlmostEqual(ketu_degree, expected_ketu_degree, delta=1.0,
                              msg=f"Ketu degree should be ~{expected_ketu_degree}°, but got {ketu_degree}°")

        print(f"Rahu: {rahu_sign} at {rahu_degree}°")
        print(f"Ketu: {ketu_sign} at {ketu_degree}°")

    def test_planet_positions(self):
        """Test that all planets are calculated and have required properties"""
        # Sample birth data
        birth_date = datetime(1985, 10, 24, 14, 30, 0, tzinfo=pytz.UTC)
        latitude = 28.6139  # Delhi latitude
        longitude = 77.2090  # Delhi longitude

        # Calculate the chart
        chart = self.calculator.calculate_chart(birth_date, latitude, longitude, PLACIDUS)

        # Verify planets list exists
        self.assertIn("planets", chart, "Chart should include planets data")
        planets = chart["planets"]

        # Define expected planets
        expected_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                           "Jupiter", "Saturn", "Uranus", "Neptune",
                           "Pluto", "Rahu", "Ketu"]

        # Get list of planet names in the chart
        planet_names = [p["name"] for p in planets]

        # Verify all expected planets are included
        for planet_name in expected_planets:
            self.assertIn(planet_name, planet_names,
                          f"Chart should include {planet_name}")

        # Verify each planet has required properties
        for planet in planets:
            self.assertIn("name", planet, "Planet should have a name")
            self.assertIn("sign", planet, "Planet should have a zodiac sign")
            self.assertIn("degree", planet, "Planet should have a degree")
            self.assertIn("house", planet, "Planet should have a house")

            # Validate sign
            self.assertIn(planet["sign"], ZODIAC_SIGNS,
                          f"Planet sign {planet['sign']} should be a valid zodiac sign")

            # Validate degree
            degree = planet["degree"]
            self.assertGreaterEqual(degree, 0, "Planet degree should be >= 0")
            self.assertLess(degree, 30, "Planet degree should be < 30")

            # Validate house
            house = planet["house"]
            self.assertGreaterEqual(house, 1, "House number should be >= 1")
            self.assertLessEqual(house, 12, "House number should be <= 12")

        print(f"Verified {len(planets)} planets in the chart")

    def test_houses(self):
        """Test that houses are correctly calculated"""
        # Sample birth data
        birth_date = datetime(1980, 3, 15, 8, 0, 0, tzinfo=pytz.UTC)
        latitude = 51.5074  # London latitude
        longitude = -0.1278  # London longitude

        # Calculate the chart
        chart = self.calculator.calculate_chart(birth_date, latitude, longitude, PLACIDUS)

        # Verify houses list exists
        self.assertIn("houses", chart, "Chart should include houses data")
        houses = chart["houses"]

        # Verify we have 12 houses
        self.assertEqual(len(houses), 12, "Chart should have 12 houses")

        # Verify each house has required properties
        for house in houses:
            self.assertIn("number", house, "House should have a number")
            self.assertIn("sign", house, "House should have a zodiac sign")

            # Validate house number
            number = house["number"]
            self.assertGreaterEqual(number, 1, "House number should be >= 1")
            self.assertLessEqual(number, 12, "House number should be <= 12")

            # Validate sign
            self.assertIn(house["sign"], ZODIAC_SIGNS,
                          f"House sign {house['sign']} should be a valid zodiac sign")

        print(f"Verified all 12 houses in the chart")


# Define zodiac signs for testing
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

if __name__ == "__main__":
    unittest.main()
