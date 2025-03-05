"""
Chart service for Birth Time Rectifier API.
Handles astrological chart calculations and management.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ai_service.utils.astro_calculator import AstroCalculator

# Configure logging
logger = logging.getLogger(__name__)

class ChartService:
    """Service for chart calculations and management"""

    def __init__(self):
        self.astro_calculator = AstroCalculator()
        self.chart_storage = {}  # Simple in-memory storage

    def generate_chart(self,
                      birth_date: str,
                      birth_time: str,
                      latitude: float,
                      longitude: float,
                      timezone: str,
                      house_system: str = "placidus",
                      ayanamsa: float = 23.6647,
                      node_type: str = "true",
                      zodiac_type: str = "sidereal") -> Dict[str, Any]:
        """
        Generate a chart based on birth details

        Args:
            birth_date: Birth date in format YYYY-MM-DD
            birth_time: Birth time in format HH:MM or HH:MM:SS
            latitude: Birth latitude
            longitude: Birth longitude
            timezone: Timezone name (e.g. 'Asia/Kolkata')
            house_system: House system to use
            ayanamsa: Ayanamsa value for sidereal calculations
            node_type: Type of nodes calculation ('true' or 'mean')
            zodiac_type: Type of zodiac ('sidereal' or 'tropical')

        Returns:
            Dictionary containing chart data
        """
        try:
            # Parse the date and time
            date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()

            # Calculate the chart
            chart_data = self.astro_calculator.calculate_chart(
                date_obj,
                birth_time,
                latitude,
                longitude,
                timezone=timezone,
                house_system=house_system,
                ayanamsa=ayanamsa
            )

            # Generate a unique ID and store the chart
            chart_id = f"chart_{len(self.chart_storage) + 1}"
            self.chart_storage[chart_id] = chart_data

            # Add chart ID to the data
            chart_data["id"] = chart_id

            return chart_data

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            raise

    def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a chart by ID

        Args:
            chart_id: ID of the chart to retrieve

        Returns:
            Chart data or None if not found
        """
        return self.chart_storage.get(chart_id)

    def compare_charts(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two charts and calculate differences

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            Dictionary with comparison results
        """
        differences = {
            "ascendant": self._compare_ascendants(chart1.get("ascendant", {}), chart2.get("ascendant", {})),
            "planets": self._compare_planets(chart1.get("planets", []), chart2.get("planets", [])),
            "houses": self._compare_houses(chart1.get("houses", []), chart2.get("houses", []))
        }

        # Calculate overall difference percentage
        total_diff = 0
        count = 0

        # Add ascendant difference
        if isinstance(differences["ascendant"], dict) and "difference_degrees" in differences["ascendant"]:
            total_diff += min(differences["ascendant"]["difference_degrees"], 30) / 30
            count += 1

        # Add planet differences
        for planet_diff in differences["planets"]:
            if "difference_degrees" in planet_diff:
                total_diff += min(planet_diff["difference_degrees"], 30) / 30
                count += 1

        # Add house differences
        for house_diff in differences["houses"]:
            if "difference_degrees" in house_diff:
                total_diff += min(house_diff["difference_degrees"], 30) / 30
                count += 1

        # Calculate average difference
        if count > 0:
            average_diff = total_diff / count
            differences["overall_difference_percentage"] = round(average_diff * 100, 2)
        else:
            differences["overall_difference_percentage"] = 0

        return differences

    def _compare_ascendants(self, asc1: Dict[str, Any], asc2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare ascendants between two charts"""
        result = {
            "original_sign": asc1.get("sign"),
            "rectified_sign": asc2.get("sign"),
            "sign_changed": asc1.get("sign") != asc2.get("sign")
        }

        # Calculate degree difference if possible
        if "degree" in asc1 and "degree" in asc2 and "sign" in asc1 and "sign" in asc2:
            # Calculate total degrees (sign position * 30 + degree)
            sign_index1 = self._get_sign_index(asc1["sign"])
            sign_index2 = self._get_sign_index(asc2["sign"])

            total_degrees1 = (sign_index1 * 30) + asc1["degree"]
            total_degrees2 = (sign_index2 * 30) + asc2["degree"]

            # Calculate smallest angle between the two positions
            diff = abs(total_degrees1 - total_degrees2)
            if diff > 180:
                diff = 360 - diff

            result["difference_degrees"] = round(diff, 2)
            result["significance"] = self._calculate_significance(diff)

        return result

    def _compare_planets(self, planets1: List[Dict[str, Any]], planets2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare planets between two charts"""
        results = []

        # Create a map of planets by name for the second chart
        planet_map2 = {p["name"]: p for p in planets2}

        for planet1 in planets1:
            name = planet1["name"]
            if name in planet_map2:
                planet2 = planet_map2[name]

                result = {
                    "planet": name,
                    "original_sign": planet1.get("sign"),
                    "rectified_sign": planet2.get("sign"),
                    "sign_changed": planet1.get("sign") != planet2.get("sign"),
                    "original_house": planet1.get("house"),
                    "rectified_house": planet2.get("house"),
                    "house_changed": planet1.get("house") != planet2.get("house")
                }

                # Calculate degree difference if possible
                if "degree" in planet1 and "degree" in planet2 and "sign" in planet1 and "sign" in planet2:
                    # Calculate total degrees
                    sign_index1 = self._get_sign_index(planet1["sign"])
                    sign_index2 = self._get_sign_index(planet2["sign"])

                    total_degrees1 = (sign_index1 * 30) + planet1["degree"]
                    total_degrees2 = (sign_index2 * 30) + planet2["degree"]

                    # Calculate smallest angle between the two positions
                    diff = abs(total_degrees1 - total_degrees2)
                    if diff > 180:
                        diff = 360 - diff

                    result["difference_degrees"] = round(diff, 2)
                    result["significance"] = self._calculate_significance(diff)

                results.append(result)

        return results

    def _compare_houses(self, houses1: List[Dict[str, Any]], houses2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare houses between two charts"""
        results = []

        # Create a map of houses by number for the second chart
        house_map2 = {h["number"]: h for h in houses2}

        for house1 in houses1:
            number = house1["number"]
            if number in house_map2:
                house2 = house_map2[number]

                result = {
                    "house": number,
                    "original_sign": house1.get("sign"),
                    "rectified_sign": house2.get("sign"),
                    "sign_changed": house1.get("sign") != house2.get("sign")
                }

                # Calculate degree difference if possible
                if "degree" in house1 and "degree" in house2 and "sign" in house1 and "sign" in house2:
                    # Calculate total degrees
                    sign_index1 = self._get_sign_index(house1["sign"])
                    sign_index2 = self._get_sign_index(house2["sign"])

                    total_degrees1 = (sign_index1 * 30) + house1["degree"]
                    total_degrees2 = (sign_index2 * 30) + house2["degree"]

                    # Calculate smallest angle between the two positions
                    diff = abs(total_degrees1 - total_degrees2)
                    if diff > 180:
                        diff = 360 - diff

                    result["difference_degrees"] = round(diff, 2)
                    result["significance"] = self._calculate_significance(diff)

                results.append(result)

        return results

    def _get_sign_index(self, sign: str) -> int:
        """Get the index of a zodiac sign (0-11)"""
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        try:
            return signs.index(sign)
        except ValueError:
            return 0  # Default to Aries if sign not found

    def _calculate_significance(self, degrees: float) -> str:
        """Calculate significance based on degree difference"""
        if degrees < 1:
            return "very high"
        elif degrees < 3:
            return "high"
        elif degrees < 7:
            return "moderate"
        elif degrees < 15:
            return "low"
        else:
            return "very low"
