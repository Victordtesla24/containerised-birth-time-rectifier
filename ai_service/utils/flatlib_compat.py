"""
Flatlib compatibility module.

This module provides a simplified implementation of the functionality we need from
flatlib, avoiding the dependency on the older pyswisseph version.
"""

import logging
from datetime import datetime
from .astro_calculator import AstroCalculator, SIGNS

logger = logging.getLogger(__name__)

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
        self._calculator = AstroCalculator()
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
        sign_index = SIGNS.index(self.sign)
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
        sign_index = SIGNS.index(self.sign)
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
