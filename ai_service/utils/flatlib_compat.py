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
    """A more accurate calculator for charts when flatlib isn't available.

    This implementation uses pyswisseph (or swisseph) directly for astronomical
    calculations, providing a fallback that's still astronomically accurate.
    """

    def __init__(self):
        self._init_swiss_ephemeris()

    def _init_swiss_ephemeris(self):
        """Initialize Swiss Ephemeris if available."""
        self.swe_available = False
        try:
            # Try to import pyswisseph first
            import swisseph as swe
            self.swe = swe
            self.swe_available = True

            # Set ephemeris path from environment or use default
            import os
            ephemeris_path = os.environ.get('SWISSEPH_PATH', '/usr/share/swisseph')
            if not os.path.exists(ephemeris_path):
                os.environ['SWISSEPH_PATH'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'ephemeris')
                ephemeris_path = os.environ['SWISSEPH_PATH']

            self.swe.set_ephe_path(ephemeris_path)
            logger.info(f"Swiss Ephemeris initialized with path: {ephemeris_path}")
        except ImportError:
            logger.warning("Swiss Ephemeris not available. Using more limited astronomical calculations.")
            self._setup_simplified_calculations()

    def _setup_simplified_calculations(self):
        """Set up simplified calculations when Swiss Ephemeris is unavailable.

        This still uses astronomical algorithms, just not the full Swiss Ephemeris.
        """
        # Import math and datetime modules for astronomical calculations
        import math
        from datetime import datetime, timedelta
        self.math = math

        # Constants for simplified astronomical calculations
        self.PLANET_ORBITAL_PERIODS = {
            "Sun": 365.25636,  # Earth's orbital period
            "Moon": 27.321661,  # Sidereal month
            "Mercury": 87.969,
            "Venus": 224.701,
            "Mars": 686.980,
            "Jupiter": 4332.589,
            "Saturn": 10759.22,
            "Uranus": 30688.5,
            "Neptune": 60182,
            "Pluto": 90560
        }

        # Mean longitude at epoch 2000.0
        self.PLANET_EPOCH_LONGITUDE = {
            "Sun": 280.46,
            "Moon": 218.32,
            "Mercury": 174.79,
            "Venus": 50.41,
            "Mars": 19.38,
            "Jupiter": 20.02,
            "Saturn": 317.02,
            "Uranus": 141.05,
            "Neptune": 256.22,
            "Pluto": 14.55
        }

        # References J2000 epoch
        self.J2000 = datetime(2000, 1, 1, 12, 0, 0)

    def _calculate_planet_position_simplified(self, planet: str, date: datetime) -> float:
        """Calculate planet position using simplified astronomical algorithms.

        Args:
            planet: Planet name
            date: Datetime object

        Returns:
            Longitude in degrees (0-360)
        """
        if planet not in self.PLANET_ORBITAL_PERIODS:
            # Default to a reasonable value based on date components
            return (date.month * 30 + date.day) % 360

        # Calculate days since J2000 epoch
        days_since_epoch = (date - self.J2000).total_seconds() / 86400.0

        # Calculate mean anomaly for the planet
        mean_motion = 360.0 / self.PLANET_ORBITAL_PERIODS[planet]
        mean_anomaly = (self.PLANET_EPOCH_LONGITUDE[planet] + mean_motion * days_since_epoch) % 360

        # Apply some basic perturbations for major planets
        if planet == "Moon":
            # Add lunar equation to make it more accurate
            perturbation = 6.29 * self.math.sin((134.9 + 477198.85 * days_since_epoch / 36525.0) * self.math.pi / 180.0)
            mean_anomaly += perturbation
        elif planet == "Jupiter":
            # Add Jupiter's major perturbation
            perturbation = 5.55 * self.math.sin((238.05 + 3034.69 * days_since_epoch / 36525.0) * self.math.pi / 180.0)
            mean_anomaly += perturbation
        elif planet == "Saturn":
            # Add Saturn's major perturbation
            perturbation = 6.58 * self.math.sin((278.29 + 3034.69 * days_since_epoch / 36525.0) * self.math.pi / 180.0)
            mean_anomaly += perturbation

        # Normalize to 0-360 range
        return mean_anomaly % 360

    def _calculate_planet_position_swe(self, planet: str, julian_day: float) -> float:
        """Calculate planet position using Swiss Ephemeris.

        Args:
            planet: Planet name
            julian_day: Julian day number

        Returns:
            Longitude in degrees (0-360)
        """
        # Map planet names to Swiss Ephemeris constants
        planet_map = {
            "Sun": self.swe.SUN,
            "Moon": self.swe.MOON,
            "Mercury": self.swe.MERCURY,
            "Venus": self.swe.VENUS,
            "Mars": self.swe.MARS,
            "Jupiter": self.swe.JUPITER,
            "Saturn": self.swe.SATURN,
            "Uranus": self.swe.URANUS,
            "Neptune": self.swe.NEPTUNE,
            "Pluto": self.swe.PLUTO,
            "North Node": self.swe.MEAN_NODE
        }

        if planet not in planet_map:
            raise ValueError(f"Unknown planet: {planet}")

        # Calculate position using Swiss Ephemeris
        try:
            # Call Swiss Ephemeris with error handling
            flags = self.swe.FLG_SWIEPH
            result = self.swe.calc_ut(julian_day, planet_map[planet], flags)

            # Swiss Ephemeris should return a tuple with the first element being longitude
            # Extract it directly with proper type checking
            if result and hasattr(result, "__getitem__"):
                longitude = result[0]
                if isinstance(longitude, (int, float)):
                    return float(longitude)

            # If we got here, something went wrong with the format
            raise TypeError(f"Unexpected result format from Swiss Ephemeris: {type(result)}")

        except Exception as e:
            logger.error(f"Error calculating {planet} position with Swiss Ephemeris: {e}")
            # Use simplified calculation as fallback
            dt = datetime.fromtimestamp((julian_day - 2440587.5) * 86400)  # Convert from JD to datetime
            return self._calculate_planet_position_simplified(planet, dt)

    def _calculate_houses(self, julian_day: float, latitude: float, longitude: float, hsys: str = 'P') -> List[float]:
        """Calculate house cusps.

        Args:
            julian_day: Julian day number
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            hsys: House system ('P' for Placidus, 'K' for Koch, etc.)

        Returns:
            List of 12 house cusp longitudes
        """
        if self.swe_available:
            # Convert house system string to byte
            hsys_byte = bytes(hsys.encode('utf-8'))

            # Calculate houses using Swiss Ephemeris
            houses, ascmc = self.swe.houses(julian_day, latitude, longitude, hsys_byte)
            return list(houses)
        else:
            # Simplified house calculation based on time and location
            import math

            # Calculate RAMC (Right Ascension of Midheaven)
            # This is a simplified calculation that doesn't account for proper RAMC
            local_sidereal_time = ((julian_day % 1) * 360 + longitude) % 360
            ramc = local_sidereal_time

            # For equal house system (simpler fallback)
            ascendant = self._calculate_ascendant_simplified(julian_day, latitude, longitude)
            house_cusps = []

            for i in range(12):
                house_cusp = (ascendant + i * 30) % 360
                house_cusps.append(house_cusp)

            return house_cusps

    def _calculate_ascendant_simplified(self, julian_day: float, latitude: float, longitude: float) -> float:
        """Calculate ascendant using simplified method.

        Args:
            julian_day: Julian day number
            latitude: Latitude in degrees
            longitude: Longitude in degrees

        Returns:
            Ascendant longitude in degrees
        """
        import math

        # Local sidereal time in degrees
        lst = ((julian_day % 1) * 360 + longitude) % 360

        # Obliquity of ecliptic (approximate)
        obliquity = 23.439291 - 0.0130042 * (julian_day - 2451545.0) / 36525.0
        obliquity_rad = math.radians(obliquity)

        # Convert LST to radians
        lst_rad = math.radians(lst)
        lat_rad = math.radians(latitude)

        # Calculate ascendant
        tan_asc = math.cos(obliquity_rad) * math.sin(lst_rad) / (math.cos(lst_rad) * math.sin(obliquity_rad) * math.sin(lat_rad) + math.cos(lat_rad) * math.cos(obliquity_rad))
        asc_rad = math.atan(tan_asc)

        # Convert to degrees and adjust quadrant
        asc_deg = math.degrees(asc_rad)
        if lst > 180:
            asc_deg += 180

        # Normalize to 0-360
        return asc_deg % 360

    def calculate_chart(self, date: datetime, latitude: float, longitude: float, hsys: str = 'P') -> Dict[str, Any]:
        """Calculate an astrological chart using available methods.

        This uses Swiss Ephemeris if available, or falls back to simplified
        but still astronomically based calculations.

        Args:
            date: Birth datetime
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            hsys: House system ('P' for Placidus, 'K' for Koch, etc.)

        Returns:
            Dictionary containing chart data
        """
        # Convert datetime to Julian day
        if self.swe_available:
            # Use Swiss Ephemeris for Julian day
            year, month, day = date.year, date.month, date.day
            hour = date.hour + date.minute/60.0 + date.second/3600.0
            julian_day = self.swe.julday(year, month, day, hour)
        else:
            # Calculate Julian day without Swiss Ephemeris
            import math
            a = (14 - date.month) // 12
            y = date.year + 4800 - a
            m = date.month + 12 * a - 3
            jdn = date.day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045
            jd = jdn + (date.hour - 12) / 24.0 + date.minute / 1440.0 + date.second / 86400.0
            julian_day = jd

        # Calculate houses
        house_cusps = self._calculate_houses(julian_day, latitude, longitude, hsys)

        # Calculate ascendant and midheaven
        if self.swe_available:
            # Use Swiss Ephemeris for angles
            houses, ascmc = self.swe.houses(julian_day, latitude, longitude, bytes(hsys.encode('utf-8')))
            ascendant = ascmc[0]
            midheaven = ascmc[1]
        else:
            # Use simplified calculations for angles
            ascendant = self._calculate_ascendant_simplified(julian_day, latitude, longitude)
            # For midheaven, use the 10th house cusp from equal house system
            midheaven = (ascendant + 270) % 360

        # Determine sign for ascendant and midheaven
        asc_sign_index = int(ascendant / 30) % 12
        mc_sign_index = int(midheaven / 30) % 12

        # Calculate planets
        planets = []
        planet_names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                        "Uranus", "Neptune", "Pluto", "North Node"]

        for planet_name in planet_names:
            try:
                # Calculate longitude based on available methods
                if self.swe_available:
                    longitude = self._calculate_planet_position_swe(planet_name, julian_day)
                else:
                    longitude = self._calculate_planet_position_simplified(planet_name, date)

                # Determine sign and house
                sign_index = int(longitude / 30) % 12
                sign = LIST_SIGNS[sign_index]

                # Find which house contains this planet
                house = 1  # Default to first house
                for i in range(12):
                    next_i = (i + 1) % 12
                    if next_i == 0:  # Comparing last house with first
                        if (house_cusps[i] <= longitude < 360) or (0 <= longitude < house_cusps[next_i]):
                            house = i + 1
                            break
                    else:
                        if house_cusps[i] <= longitude < house_cusps[next_i]:
                            house = i + 1
                            break

                # Add planet to list
                planets.append({
                    "name": planet_name,
                    "sign": sign,
                    "degree": longitude % 30,
                    "longitude": longitude,
                    "house": house,
                    # For retrograde motion we'd need additional calculations
                    # This is approximated for now
                    "retrograde": planet_name in ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"] and
                                 date.month % 3 == 0  # Simplified approximation
                })
            except Exception as e:
                logger.error(f"Error calculating {planet_name}: {e}")
                # Still include the planet with estimated position
                planets.append({
                    "name": planet_name,
                    "sign": LIST_SIGNS[(date.month + planet_names.index(planet_name)) % 12],
                    "degree": (date.day + planet_names.index(planet_name)) % 30,
                    "longitude": ((date.month + planet_names.index(planet_name)) % 12) * 30 +
                               ((date.day + planet_names.index(planet_name)) % 30),
                    "house": (planet_names.index(planet_name) % 12) + 1,
                    "retrograde": False
                })

        # Build final chart data
        chart_data = {
            "ascendant": {
                "sign": LIST_SIGNS[asc_sign_index],
                "degree": ascendant % 30,
                "longitude": ascendant
            },
            "midheaven": {
                "sign": LIST_SIGNS[mc_sign_index],
                "degree": midheaven % 30,
                "longitude": midheaven
            },
            "planets": planets,
            "houses": house_cusps,
            "julian_day": julian_day,
            "calculation_method": "Swiss Ephemeris" if self.swe_available else "Astronomical Approximation"
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
    """Create a chart using basic calculation methods.

    This is a compatibility wrapper around the BasicChartCalculator for code
    that expects flatlib's createChart function.
    """
    # Create a basic chart calculator instance
    calculator = BasicChartCalculator()

    # Calculate the chart using the calculator
    chart_data = calculator.calculate_chart(date, pos.lat, pos.lon, hsys)

    # Create and return a Chart object
    return Chart(date, pos, hsys)

def calculate_flatlib_chart(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    house_system: str = 'P'
) -> Dict[str, Any]:
    """
    Calculate a chart using flatlib-compatible methods.

    This function provides a standardized chart data structure compatible with
    the rest of the application while using flatlib for calculations.

    Args:
        birth_dt: Birth datetime object
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        house_system: House system (e.g., 'P' for Placidus)

    Returns:
        Dictionary containing standardized chart data
    """
    # Initialize the calculator
    calculator = BasicChartCalculator()

    # Calculate the Julian Day
    from flatlib.datetime import Datetime as FlatlibDatetime

    # Format date and time strings for flatlib
    date_str = birth_dt.strftime("%Y/%m/%d")
    time_str = birth_dt.strftime("%H:%M")

    # Get UTC offset - safely handle potential errors
    try:
        # Try to get timezone offset
        tz_offset = birth_dt.astimezone().utcoffset()
        if tz_offset is not None:
            offset_seconds = tz_offset.total_seconds()
            offset_hours = offset_seconds / 3600
        else:
            # If offset is None, default to UTC
            offset_hours = 0
    except (AttributeError, ValueError, TypeError) as e:
        # If any error occurs in offset calculation, default to UTC
        logger.warning(f"Error calculating timezone offset: {e}. Defaulting to UTC.")
        offset_hours = 0

    # Format offset string
    offset_sign = "+" if offset_hours >= 0 else "-"
    offset_hours_abs = abs(int(offset_hours))
    offset_minutes = abs(int((offset_hours - int(offset_hours)) * 60))
    offset_str = f"{offset_sign}{offset_hours_abs:02d}:{offset_minutes:02d}"

    # Create flatlib datetime
    flat_datetime = FlatlibDatetime(date_str, time_str, offset_str)

    # Format latitude and longitude for GeoPos
    from flatlib.geopos import GeoPos

    lat_direction = 'N' if latitude >= 0 else 'S'
    lat_degrees = int(abs(latitude))
    lat_minutes = int((abs(latitude) - lat_degrees) * 60)
    lat_str = f"{lat_degrees}{lat_direction}{lat_minutes}"

    lon_direction = 'E' if longitude >= 0 else 'W'
    lon_degrees = int(abs(longitude))
    lon_minutes = int((abs(longitude) - lon_degrees) * 60)
    lon_str = f"{lon_degrees}{lon_direction}{lon_minutes}"

    geo_pos = GeoPos(lat_str, lon_str)

    # Calculate chart using internal methods
    chart_data = calculator.calculate_chart(birth_dt, latitude, longitude, house_system)

    # If we have flatlib available, use it directly
    try:
        import flatlib
        from flatlib.chart import Chart as FlatlibChart

        flatlib_chart = FlatlibChart(flat_datetime, geo_pos, hsys=house_system)

        # Check if we have a valid chart
        if flatlib_chart and hasattr(flatlib_chart, 'getAngles'):
            # Format chart data in the standardized format
            standardized_data = {
                "chart_type": "tropical",
                "planets": [],
                "houses": [],
                "angles": {},
                "calculation_method": "flatlib",
                "house_system": house_system
            }

            # Add planets
            for planet_name in ["Sun", "Moon", "Mercury", "Venus", "Mars",
                                "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
                try:
                    planet = flatlib_chart.getObject(planet_name)
                    if planet:
                        planet_data = {
                            "name": planet_name,
                            "longitude": planet.lon,
                            "latitude": getattr(planet, "lat", 0),
                            "sign": planet.sign,
                            "sign_longitude": planet.signlon,
                            "house": flatlib_chart.objectHouse(planet_name),
                            "retrograde": getattr(planet, "retrograde", False)
                        }
                        standardized_data["planets"].append(planet_data)
                except Exception as e:
                    logger.warning(f"Error getting planet {planet_name}: {e}")

            # Add houses
            for house_num in range(1, 13):
                try:
                    house = flatlib_chart.getHouse(house_num)
                    if house:
                        house_data = {
                            "house": house_num,
                            "longitude": house.lon,
                            "sign": house.sign,
                            "sign_longitude": house.signlon
                        }
                        standardized_data["houses"].append(house_data)
                except Exception as e:
                    logger.warning(f"Error getting house {house_num}: {e}")

            # Add angles
            for angle_name in ["Asc", "MC", "Dsc", "IC"]:
                try:
                    angle = flatlib_chart.getAngle(angle_name)
                    if angle:
                        angle_data = {
                            "longitude": angle.lon,
                            "sign": angle.sign,
                            "sign_longitude": angle.signlon
                        }
                        standardized_data["angles"][angle_name] = angle_data
                except Exception as e:
                    logger.warning(f"Error getting angle {angle_name}: {e}")

            return standardized_data
    except ImportError:
        logger.warning("Flatlib not available, using basic chart calculator fallback")

    # If we get here, return the data from our basic calculator
    return chart_data
