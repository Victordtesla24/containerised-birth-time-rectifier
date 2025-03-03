"""
Compatibility module for swisseph.
This module forwards all imports to the installed swisseph package.
"""

import logging
logger = logging.getLogger(__name__)

# Define constants that might be used if swisseph is not available
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

# Try two different import approaches to handle different installation methods
SWISSEPH_AVAILABLE = False
try:
    # First try the standard import
    import swisseph as swe
    # Copy all the symbols from swisseph to make them available
    for attr in dir(swe):
        if not attr.startswith('_'):
            globals()[attr] = getattr(swe, attr)
    SWISSEPH_AVAILABLE = True
    logger.info("Successfully imported swisseph package")
except ImportError:
    # If that fails, try the direct import approach
    try:
        from swisseph.swisseph import *
        SWISSEPH_AVAILABLE = True
        logger.info("Successfully imported swisseph.swisseph")
    except ImportError:
        # As a last resort, try importing from swisseph directly
        try:
            from swisseph import *
            SWISSEPH_AVAILABLE = True
            logger.info("Successfully imported swisseph through direct import")
        except ImportError:
            # If all import methods fail, create fallback functions
            logger.warning("Could not import swisseph package using any known method. Using fallback calculations.")

            # Fallback implementations
            def julday(year, month, day, hour):
                """Simple Julian day calculation without swisseph"""
                a = (14 - month) // 12
                y = year + 4800 - a
                m = month + 12 * a - 3
                jd = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
                jd += (hour / 24.0)
                return jd

            def calc_ut(jd, planet, flags=0):
                """
                Calculate planet position for given Julian day.

                Args:
                    jd: Julian day
                    planet: Planet ID
                    flags: Calculation flags

                Returns:
                    Position tuple in the format (longitude, latitude, distance, speed_longitude, speed_latitude, speed_distance)
                """
                if SWISSEPH_AVAILABLE:
                    try:
                        return swe.calc_ut(jd, planet, flags)
                    except Exception as e:
                        logger.error(f"Error in Swiss Ephemeris calculation: {e}")
                        logger.info("Falling back to simplified calculation")

                # Fallback calculation if Swiss Ephemeris fails or is not available
                # Return very simplified positions based on average daily motion
                # This is extremely simplified and not accurate
                # Speeds are approximate degrees per day
                planet_speeds = {
                    SUN: 1.0,
                    MOON: 13.2,
                    MERCURY: 1.4,
                    VENUS: 1.2,
                    MARS: 0.5,
                    JUPITER: 0.08,
                    SATURN: 0.03,
                    URANUS: 0.01,
                    NEPTUNE: 0.006,
                    PLUTO: 0.004,
                    MEAN_NODE: -0.05,
                    TRUE_NODE: -0.05  # Using same speed for True Node as Mean Node in fallback
                }

                # Base epoch J2000.0 (January 1, 2000, 12:00 UT)
                j2000 = 2451545.0
                days_since_j2000 = jd - j2000

                # Very basic position calculation
                speed = planet_speeds.get(planet, 1.0)
                position = (days_since_j2000 * speed) % 360

                # For planets with retrograde periods, add simplified retrograde simulation
                retrograde = False
                if planet in [MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO]:
                    # Simple retrograde simulation - not accurate
                    retrograde_cycle = {
                        MERCURY: 116,  # Mercury retrogrades about every 116 days
                        VENUS: 584,    # Venus has retrograde cycles about every 584 days
                        MARS: 780,     # Mars retrogrades about every 26 months
                        JUPITER: 399,  # Jupiter retrogrades yearly
                        SATURN: 378,   # Saturn retrogrades yearly
                        URANUS: 369,   # Uranus retrogrades yearly
                        NEPTUNE: 367,  # Neptune retrogrades yearly
                        PLUTO: 367     # Pluto retrogrades yearly
                    }
                    cycle_length = retrograde_cycle.get(planet, 365)
                    retrograde_phase = (days_since_j2000 % cycle_length) / cycle_length

                    # Retrograde for about 1/6 of the cycle
                    if 0.4 < retrograde_phase < 0.6:
                        retrograde = True

                # Return tuple of (longitude, latitude, distance, speed)
                return (position, 0.0, 1.0, -speed if retrograde else speed)

            def calc(jd, planet):
                """Simple wrapper for calc_ut"""
                return calc_ut(jd, planet)

            def houses(jd, lat, lon, hsys):
                """Fallback house calculation"""
                # Very basic equal house system
                # This is extremely simplified and not accurate

                # Calculate approximate ARMC (Sidereal Time)
                j2000 = 2451545.0
                t = (jd - j2000) / 36525.0
                theta = 280.46061837 + 360.98564736629 * (jd - j2000) + 0.000387933 * t * t - t * t * t / 38710000.0
                theta = theta % 360

                # Add local longitude contribution (15° per hour)
                theta += lon * 24.0 / 360.0

                # Calculate ascendant (simplified)
                ascendant = (theta + 90) % 360

                # Create equal houses
                cusps = [0.0] * 13  # House cusps array
                cusps[1] = ascendant

                # Equal house system - each house is 30 degrees
                for i in range(2, 13):
                    cusps[i] = (cusps[1] + (i - 1) * 30.0) % 360

                # Return tuple of (cusps, ascendant, mc, armc, vertex, equatorial_ascendant)
                return (cusps, ascendant, (ascendant + 270) % 360, theta, 0.0, 0.0)

            def set_ephe_path(path=None):
                """Dummy function for setting ephemeris path"""
                logger.warning("Ephemeris path cannot be set because swisseph is not available")
                return

            # Add more fallback functions as needed

            logger.warning("Using fallback calculations - results will be approximate")
