"""
Flatlib compatibility module.

This module provides a simplified implementation of the functionality we need from
flatlib, avoiding the dependency on the older pyswisseph version.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Import constants from flatlib if available, otherwise define our own
try:
    from flatlib.const import LIST_SIGNS
except ImportError:
    # Define fallback constants if flatlib is not available
    LIST_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

logger = logging.getLogger(__name__)

# Define a simple chart calculator class
class BasicChartCalculator:
    """A basic calculator for charts when real calculations aren't needed."""

    def calculate_chart(self, date: datetime, latitude: float, longitude: float) -> Dict[str, Any]:
        """Calculate a basic chart with minimum required data."""
        # This is a placeholder implementation that returns a minimal chart
        # In a real implementation, this would call actual astronomical calculations

        # Calculate a very basic ascendant based on birth time
        hour = date.hour
        minute = date.minute
        total_minutes = hour * 60 + minute
        # Each sign gets 2 hours, so divide by 120 minutes to get sign index
        asc_sign_index = (total_minutes // 120) % 12
        asc_degree = (total_minutes % 120) / 4  # 0-30 degree range

        chart_data = {
            "ascendant": {
                "sign": LIST_SIGNS[asc_sign_index],
                "degree": asc_degree
            },
            "planets": [
                # Placeholder planets - in reality, these would be calculated properly
                {"name": "Sun", "sign": LIST_SIGNS[date.month % 12], "degree": date.day, "house": 1},
                {"name": "Moon", "sign": LIST_SIGNS[(date.month + 3) % 12], "degree": 15, "house": 4},
                {"name": "Mercury", "sign": LIST_SIGNS[date.month % 12], "degree": 10, "house": 1},
                {"name": "Venus", "sign": LIST_SIGNS[(date.month + 1) % 12], "degree": 20, "house": 2},
                {"name": "Mars", "sign": LIST_SIGNS[(date.month + 5) % 12], "degree": 25, "house": 6},
                {"name": "Jupiter", "sign": LIST_SIGNS[(date.month + 8) % 12], "degree": 15, "house": 9},
                {"name": "Saturn", "sign": LIST_SIGNS[(date.month + 10) % 12], "degree": 5, "house": 11}
            ],
            "houses": [
                # Placeholder house cusps - these would be calculated based on actual house systems
                (asc_sign_index * 30 + asc_degree) % 360,
                (asc_sign_index * 30 + asc_degree + 30) % 360,
                (asc_sign_index * 30 + asc_degree + 60) % 360,
                (asc_sign_index * 30 + asc_degree + 90) % 360,
                (asc_sign_index * 30 + asc_degree + 120) % 360,
                (asc_sign_index * 30 + asc_degree + 150) % 360,
                (asc_sign_index * 30 + asc_degree + 180) % 360,
                (asc_sign_index * 30 + asc_degree + 210) % 360,
                (asc_sign_index * 30 + asc_degree + 240) % 360,
                (asc_sign_index * 30 + asc_degree + 270) % 360,
                (asc_sign_index * 30 + asc_degree + 300) % 360,
                (asc_sign_index * 30 + asc_degree + 330) % 360
            ]
        }
        return chart_data

class Chart:
    """Simplified Chart class to replace flatlib.Chart."""

    def __init__(self, date, pos, hsys='P'):
        """
        Initialize a Chart.

        Args:
            date: Datetime object or ISO format string
            pos: Tuple of (latitude, longitude)
            hsys: House system (default: Placidus)
        """
        if isinstance(date, str):
            self.date = datetime.fromisoformat(date)
        else:
            self.date = date

        self.latitude, self.longitude = pos
        self.hsys = hsys
        self._calculator = BasicChartCalculator()
        self._chart_data = self._calculator.calculate_chart(
            self.date, self.latitude, self.longitude
        )

    def getObject(self, name):
        """
        Get a celestial object by name.

        Args:
            name: Planet or point name (Sun, Moon, etc.)

        Returns:
            Object with sign and degree information
        """
        for planet in self._chart_data['planets']:
            if planet['name'].lower() == name.lower():
                return PlanetObject(
                    name=planet['name'],
                    sign=planet['sign'],
                    degree=planet['degree'],
                    house=planet['house'],
                    retrograde=planet.get('retrograde', False)
                )

        # If not found, check if it's the ascendant
        if name.lower() == 'asc':
            asc = self._chart_data['ascendant']
            return PointObject(
                name='Asc',
                sign=asc['sign'],
                degree=asc['degree']
            )

        # If we get here, the object wasn't found
        logger.warning(f"Object '{name}' not found in chart")
        return None

    def getHouse(self, house_num):
        """
        Get a house by number.

        Args:
            house_num: House number (1-12)

        Returns:
            House object with sign and degree information
        """
        if 'houses' not in self._chart_data or not self._chart_data['houses']:
            logger.warning(f"Houses not available in chart data")
            return None

        houses = self._chart_data['houses']
        if isinstance(houses, list) and 1 <= house_num <= len(houses):
            # Handle houses as a list of longitudes or objects
            house_data = houses[house_num - 1]
            if isinstance(house_data, dict):
                # If house data is already a dictionary with sign/degree
                return HouseObject(
                    number=house_num,
                    sign=house_data.get('sign', ''),
                    degree=house_data.get('degree', 0)
                )
            else:
                # If house data is just a longitude
                longitude = float(house_data)
                sign_index = int(longitude / 30) % 12
                sign = LIST_SIGNS[sign_index]
                degree = longitude % 30
                return HouseObject(number=house_num, sign=sign, degree=degree)
        elif isinstance(houses, dict) and str(house_num) in houses:
            # Handle houses as a dictionary
            house_data = houses[str(house_num)]
            return HouseObject(
                number=house_num,
                sign=house_data.get('sign', ''),
                degree=house_data.get('degree', 0)
            )

        logger.warning(f"House {house_num} not found in chart")
        return None

    def object_house(self, object_name):
        """
        Get the house number for a celestial object.

        Args:
            object_name: Name of the celestial object

        Returns:
            House number (1-12) or None if not found
        """
        obj = self.getObject(object_name)
        # Check if the object is a PlanetObject with a house attribute
        if obj and isinstance(obj, PlanetObject) and hasattr(obj, 'house'):
            return obj.house

        # For point objects like Asc, determine the house based on longitude
        if obj:
            longitude = obj.lon()
            # Find which house contains this longitude
            houses_longitudes = []
            for i in range(1, 13):
                house_obj = self.getHouse(i)
                if house_obj:
                    houses_longitudes.append((i, house_obj.lon()))

            if houses_longitudes:
                # Sort by longitude
                houses_longitudes.sort(key=lambda x: x[1])

                # Find which house contains the object
                for i in range(len(houses_longitudes)):
                    current_house, current_lon = houses_longitudes[i]
                    next_house, next_lon = houses_longitudes[(i+1) % len(houses_longitudes)]

                    if next_lon < current_lon:  # Crossing 0 degrees
                        if longitude >= current_lon or longitude < next_lon:
                            return current_house
                    elif longitude >= current_lon and longitude < next_lon:
                        return current_house

        return 1  # Default to house 1 if not found

    def getAngle(self, angle_name):
        """
        Get an angle (Asc, MC) by name.

        Args:
            angle_name: Angle name (Asc, MC)

        Returns:
            Angle object
        """
        if angle_name.lower() == 'asc':
            asc = self._chart_data['ascendant']
            return PointObject(
                name='Asc',
                sign=asc['sign'],
                degree=asc['degree']
            )

        # For now, we don't support other angles
        logger.warning(f"Angle '{angle_name}' not supported")
        return None


class PlanetObject:
    """Simplified Planet object to replace flatlib.objects.Planet."""

    def __init__(self, name, sign, degree, house, retrograde=False):
        self.name = name
        self.sign = sign
        self.degree = degree
        self.house = house
        self.retrograde = retrograde

    def __str__(self):
        ret_str = " (R)" if self.retrograde else ""
        return f"{self.name}: {self.sign} {self.degree:.2f}°{ret_str}"

    def __repr__(self):
        return self.__str__()

    def signlon(self):
        """Get the longitude within the sign (0-30)."""
        return self.degree

    def lon(self):
        """Get the absolute longitude (0-360)."""
        sign_index = LIST_SIGNS.index(self.sign)
        return sign_index * 30 + self.degree


class PointObject:
    """Simplified Point object to replace flatlib.objects.Point."""

    def __init__(self, name, sign, degree):
        self.name = name
        self.sign = sign
        self.degree = degree

    def __str__(self):
        return f"{self.name}: {self.sign} {self.degree:.2f}°"

    def __repr__(self):
        return self.__str__()

    def signlon(self):
        """Get the longitude within the sign (0-30)."""
        return self.degree

    def lon(self):
        """Get the absolute longitude (0-360)."""
        sign_index = LIST_SIGNS.index(self.sign)
        return sign_index * 30 + self.degree


class HouseObject:
    """Simplified House object to replace flatlib.objects.House."""

    def __init__(self, number, sign, degree):
        self.number = number
        self.sign = sign
        self.degree = degree

    def __str__(self):
        return f"House {self.number}: {self.sign} {self.degree:.2f}°"

    def __repr__(self):
        return self.__str__()

    def signlon(self):
        """Get the longitude within the sign (0-30)."""
        return self.degree

    def lon(self):
        """Get the absolute longitude (0-360)."""
        sign_index = LIST_SIGNS.index(self.sign)
        return sign_index * 30 + self.degree


def createChart(date, pos, hsys='P'):
    """
    Create a Chart object (compatibility function).

    Args:
        date: Datetime object or ISO format string
        pos: Tuple of (latitude, longitude)
        hsys: House system (default: Placidus)

    Returns:
        Chart object
    """
    return Chart(date, pos, hsys)
