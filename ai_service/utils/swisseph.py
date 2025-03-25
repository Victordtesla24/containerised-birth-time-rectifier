"""
Compatibility module for swisseph.
This module forwards all imports to the installed swisseph package.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Define our constants directly to avoid attribute lookup issues
# Planet constants
SUN = 0
MOON = 1
MERCURY = 2
VENUS = 3
MARS = 4
JUPITER = 5
SATURN = 6
URANUS = 7
NEPTUNE = 8
PLUTO = 9
MEAN_NODE = 10  # Rahu (North Node)
TRUE_NODE = 11
MEAN_APOG = 12  # Lilith (Mean Black Moon)
OSCU_APOG = 13  # Osculating Lilith
EARTH = 14
CHIRON = 15
PHOLUS = 16
CERES = 17
PALLAS = 18
JUNO = 19
VESTA = 20

# Ayanamsa constants
SIDM_FAGAN_BRADLEY = 0
SIDM_LAHIRI = 1
SIDM_DELUCE = 2
SIDM_RAMAN = 3
SIDM_USHASHASHI = 4
SIDM_KRISHNAMURTI = 5
SIDM_DJWHAL_KHUL = 6
SIDM_YUKTESHWAR = 7
SIDM_JN_BHASIN = 8
SIDM_BABYL_KUGLER1 = 9
SIDM_BABYL_KUGLER2 = 10
SIDM_BABYL_KUGLER3 = 11
SIDM_BABYL_HUBER = 12
SIDM_BABYL_ETPSC = 13
SIDM_ALDEBARAN_15TAU = 14
SIDM_HIPPARCHOS = 15
SIDM_SASSANIAN = 16
SIDM_GALCENT_0SAG = 17
SIDM_J2000 = 18
SIDM_J1900 = 19
SIDM_B1950 = 20
SIDM_SURYASIDDHANTA = 21
SIDM_SURYASIDDHANTA_MSUN = 22
SIDM_ARYABHATA = 23
SIDM_ARYABHATA_MSUN = 24
SIDM_SS_REVATI = 25
SIDM_SS_CITRA = 26
SIDM_TRUE_CITRA = 27
SIDM_TRUE_REVATI = 28
SIDM_TRUE_PUSHYA = 29
SIDM_GALCENT_RGILBRAND = 30
SIDM_GALEQU_IAU1958 = 31
SIDM_GALEQU_TRUE = 32
SIDM_GALEQU_MULA = 33
SIDM_GALALIGN_MARDYKS = 34
SIDM_TRUE_MULA = 35
SIDM_GALCENT_MULA_WILHELM = 36
SIDM_ARYABHATA_522 = 37
SIDM_BABYL_BRITTON = 38
SIDM_TRUE_SHEORAN = 39
SIDM_GALCENT_COCHRANE = 40
SIDM_GALEQU_FIORENZA = 41
SIDM_VALENS_MOON = 42
SIDM_LAHIRI_1940 = 43
SIDM_LAHIRI_VP285 = 44
SIDM_KRISHNAMURTI_VP291 = 45
SIDM_LAHIRI_ICRC = 46
SIDM_USER = 255

# Ephemeris flags
SEFLG_JPLEPH = 1
SEFLG_SWIEPH = 2
SEFLG_MOSEPH = 4  # Moshier theory - no ephemeris files needed
SEFLG_HELCTR = 8
SEFLG_TRUEPOS = 16
SEFLG_J2000 = 32
SEFLG_NONUT = 64
SEFLG_SPEED = 128
SEFLG_NOGDEFL = 256
SEFLG_NOABERR = 512
SEFLG_EQUATORIAL = 1024
SEFLG_XYZ = 2048
SEFLG_RADIANS = 4096
SEFLG_BARYCTR = 8192
SEFLG_TOPOCTR = 16384
SEFLG_SIDEREAL = 32768

# Aliases for compatibility
FLG_JPLEPH = SEFLG_JPLEPH
FLG_SWIEPH = SEFLG_SWIEPH
FLG_MOSEPH = SEFLG_MOSEPH
FLG_HELCTR = SEFLG_HELCTR
FLG_TRUEPOS = SEFLG_TRUEPOS
FLG_J2000 = SEFLG_J2000
FLG_NONUT = SEFLG_NONUT
FLG_SPEED = SEFLG_SPEED
FLG_NOGDEFL = SEFLG_NOGDEFL
FLG_NOABERR = SEFLG_NOABERR
FLG_EQUATORIAL = SEFLG_EQUATORIAL
FLG_XYZ = SEFLG_XYZ
FLG_RADIANS = SEFLG_RADIANS
FLG_BARYCTR = SEFLG_BARYCTR
FLG_TOPOCTR = SEFLG_TOPOCTR
FLG_SIDEREAL = SEFLG_SIDEREAL

# Set ephemeris path from environment
EPHE_PATH = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")

# Attempt to import Swiss Ephemeris
try:
    import pyswisseph as swe
    # Verify that the module has the required attributes
    required_attributes = ['julday', 'calc', 'calc_ut', 'houses', 'set_ephe_path', 'SUN']

    for attr in required_attributes:
        if not hasattr(swe, attr):
            raise AttributeError(f"Swiss Ephemeris module missing required attribute: {attr}")

    SWISS_EPHEMERIS_AVAILABLE = True
    logger.info("Swiss Ephemeris successfully imported with all required attributes")
except (ImportError, AttributeError) as e:
    try:
        # Fall back to swisseph if pyswisseph is not available (for backward compatibility)
        import swisseph as swe
        required_attributes = ['julday', 'calc', 'calc_ut', 'houses', 'set_ephe_path', 'SUN']

        for attr in required_attributes:
            if not hasattr(swe, attr):
                raise AttributeError(f"Swiss Ephemeris module missing required attribute: {attr}")

        SWISS_EPHEMERIS_AVAILABLE = True
        logger.warning("Using swisseph instead of pyswisseph. Consider upgrading to pyswisseph.")
    except (ImportError, AttributeError) as e2:
        logger.error(f"Failed to import Swiss Ephemeris (pyswisseph/swisseph) or missing required attributes: {e2}")
        SWISS_EPHEMERIS_AVAILABLE = False

# Set ephemeris path if available
if SWISS_EPHEMERIS_AVAILABLE:
    # Check for ephemeris path in environment variable
    ephe_path = os.environ.get('EPHEMERIS_PATH')

    # If not in environment, check common locations
    if not ephe_path:
        possible_paths = [
            # Check current directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ephe'),
            # Check parent directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ephe'),
            # Check root directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ephe'),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                ephe_path = path
                break

    # Set the ephemeris path if found
    if ephe_path:
        try:
            # Use safe attribute checking
            set_ephe_path_fn = getattr(swe, 'set_ephe_path', None)
            if set_ephe_path_fn and callable(set_ephe_path_fn):
                set_ephe_path_fn(ephe_path)
                logger.info(f"Set Swiss Ephemeris path to: {ephe_path}")
            else:
                logger.warning("set_ephe_path function not available in swisseph module")
        except Exception as e:
            logger.warning(f"Failed to set Swiss Ephemeris path: {e}")
    else:
        logger.warning("No ephemeris files found. Swiss Ephemeris will use internal planets only.")

class SwissEphError(Exception):
    """Exception raised for Swiss Ephemeris errors."""
    pass

def initialize_swiss_ephemeris():
    """
    Initialize the Swiss Ephemeris library.

    Raises:
        SwissEphError: If Swiss Ephemeris is not available
    """
    if not SWISS_EPHEMERIS_AVAILABLE:
        raise SwissEphError("Swiss Ephemeris (swisseph) is required but not available")

    logger.info("Swiss Ephemeris initialized successfully")
    return True

def verify_ephemeris_files() -> bool:
    """
    Verify that ephemeris files are available.

    This function checks if the Swiss Ephemeris library can calculate planetary positions,
    which requires ephemeris files for accurate results.

    Returns:
        True if ephemeris files are available, False otherwise

    Raises:
        SwissEphError: If Swiss Ephemeris is not available
    """
    if not SWISS_EPHEMERIS_AVAILABLE:
        raise SwissEphError("Swiss Ephemeris (swisseph) is required but not available")

    # Try to calculate a simple planetary position
    try:
        # Check if necessary functions exist using safe attribute access
        julday_fn = getattr(swe, 'julday', None)
        if not julday_fn or not callable(julday_fn):
            logger.error("julday function not available in swisseph module")
            return False

        calc_fn = getattr(swe, 'calc', None)
        if not calc_fn or not callable(calc_fn):
            logger.error("calc function not available in swisseph module")
            return False

        # Current Julian day using safe function access
        jd = julday_fn(2023, 1, 1, 0)

        # Try to calculate Sun's position
        SUN = getattr(swe, 'SUN', 0)  # Default to 0 if not defined
        res, flags = calc_fn(jd, SUN)

        # If we got a result, ephemeris files are available
        return True
    except Exception as e:
        logger.error(f"Failed to verify ephemeris files: {e}")
        return False

def calculate_chart(birth_dt: datetime, latitude: float, longitude: float, house_system: str = 'P') -> Dict[str, Any]:
    """
    Calculate a full astrological chart.

    Args:
        birth_dt: Birth date and time
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        house_system: House system to use ('P' for Placidus, etc.)

    Returns:
        Dictionary with chart data

    Raises:
        SwissEphError: If Swiss Ephemeris is not available or calculation fails
    """
    if not SWISS_EPHEMERIS_AVAILABLE:
        raise SwissEphError("Swiss Ephemeris (swisseph) is required but not available")

    try:
        # Get Julian day using safe function access
        julday_fn = getattr(swe, 'julday', None)
        if not julday_fn or not callable(julday_fn):
            raise SwissEphError("julday function not available in swisseph module")

        jd = julday_fn(
            birth_dt.year,
            birth_dt.month,
            birth_dt.day,
            birth_dt.hour + birth_dt.minute / 60.0 + birth_dt.second / 3600.0
        )

        # Calculate houses using safe function access
        houses_fn = getattr(swe, 'houses', None)
        if not houses_fn or not callable(houses_fn):
            raise SwissEphError("houses function not available in swisseph module")

        houses_result = houses_fn(jd, latitude, longitude, bytes(house_system, 'utf-8'))

        # Calculate planets using safe function access
        calc_ut_fn = getattr(swe, 'calc_ut', None)
        if not calc_ut_fn or not callable(calc_ut_fn):
            raise SwissEphError("calc_ut function not available in swisseph module")

        # Calculate planet positions
        planets = {}
        for planet_name, planet_id in get_planets_list().items():
            try:
                # Calculate planet position
                result, flags = calc_ut_fn(jd, planet_id)

                # Get zodiac sign and house
                sign = get_zodiac_sign(result[0])
                house = get_house_position(houses_result, result[0])

                # Store planet data
                planets[planet_name] = {
                    'longitude': result[0],
                    'latitude': result[1],
                    'distance': result[2],
                    'speed': result[3],
                    'sign': sign,
                    'house': house
                }
            except Exception as e:
                logger.error(f"Error calculating position for {planet_name}: {e}")
                raise SwissEphError(f"Failed to calculate {planet_name} position: {e}")

        # Build chart data
        chart_data = {
            'planets': planets,
            'houses': {i+1: houses_result[i+1] for i in range(12)},
            'ascendant': houses_result[0],
            'midheaven': houses_result[1],
            'birth_details': {
                'birth_date': birth_dt.strftime('%Y-%m-%d'),
                'birth_time': birth_dt.strftime('%H:%M:%S'),
                'latitude': latitude,
                'longitude': longitude
            },
            'house_system': house_system
        }

        return chart_data

    except Exception as e:
        error_msg = f"Chart calculation failed: {str(e)}"
        logger.error(error_msg)
        raise SwissEphError(error_msg) from e

def get_planets_list() -> Dict[str, int]:
    """
    Get a dictionary of planets and their IDs.

    Returns:
        Dictionary mapping planet names to Swiss Ephemeris IDs

    Raises:
        SwissEphError: If Swiss Ephemeris is not available
    """
    if not SWISS_EPHEMERIS_AVAILABLE:
        raise SwissEphError("Swiss Ephemeris is required for astrological calculations")

    return {
        'Sun': swe.SUN,
        'Moon': swe.MOON,
        'Mercury': swe.MERCURY,
        'Venus': swe.VENUS,
        'Mars': swe.MARS,
        'Jupiter': swe.JUPITER,
        'Saturn': swe.SATURN,
        'Uranus': swe.URANUS,
        'Neptune': swe.NEPTUNE,
        'Pluto': swe.PLUTO,
        'North Node': swe.MEAN_NODE,
        'Chiron': swe.CHIRON
    }

def get_zodiac_sign(longitude: float) -> str:
    """
    Get the zodiac sign for a given longitude.

    Args:
        longitude: Longitude in degrees

    Returns:
        Zodiac sign name
    """
    # Normalize to 0-360 range
    longitude = longitude % 360

    # Define zodiac signs
    signs = [
        'Aries', 'Taurus', 'Gemini', 'Cancer',
        'Leo', 'Virgo', 'Libra', 'Scorpio',
        'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]

    # Calculate sign index (each sign is 30 degrees)
    sign_index = int(longitude / 30)

    return signs[sign_index]

def get_house_position(houses: List[float], longitude: float) -> int:
    """
    Get the house position for a given longitude.

    Args:
        houses: List of house cusps
        longitude: Longitude in degrees

    Returns:
        House number (1-12)
    """
    # Normalize to 0-360 range
    longitude = longitude % 360

    # Check each house
    for i in range(12):
        house_start = houses[i+1]
        house_end = houses[(i+2) % 12]

        # Handle case where house crosses 0 degrees
        if house_end < house_start:
            if longitude >= house_start or longitude < house_end:
                return i + 1
        else:
            if house_start <= longitude < house_end:
                return i + 1

    # If we get here, we couldn't find the house (shouldn't happen)
    return 1
