"""
Compatibility module for swisseph.
This module forwards all imports to the installed swisseph package.
"""

import logging
import os
from typing import Dict, Any

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

# Try to import the real Swiss Ephemeris library
try:
    # Try the standard import first
    import swisseph as swe

    logger.info(f"Using swisseph package with Moshier theory calculations")

    # Initialize the ephemeris path just in case files are available
    swe.set_ephe_path(EPHE_PATH)

    # Always use Moshier mode (built-in) since ephemeris files might not be available
    # This ensures we always get real calculations, not fallbacks
    def calc(jd, planet, iflag=0):
        iflag |= SEFLG_MOSEPH  # Always use Moshier theory
        return swe.calc(jd, planet, iflag)

    def calc_ut(jd, planet, iflag=0):
        iflag |= SEFLG_MOSEPH  # Always use Moshier theory
        return swe.calc_ut(jd, planet, iflag)

    # Export other functions directly
    julday = swe.julday
    houses = swe.houses
    houses_ex = swe.houses_ex
    set_ephe_path = swe.set_ephe_path
    set_sid_mode = swe.set_sid_mode
    get_ayanamsa_ut = swe.get_ayanamsa_ut
    get_ayanamsa_name = swe.get_ayanamsa_name
    set_topo = swe.set_topo

except (ImportError, AttributeError) as e:
    # If import fails, try alternative pyswisseph
    try:
        import pyswisseph as swe  # type: ignore

        logger.info(f"Using pyswisseph package with Moshier theory calculations")

        # Initialize the ephemeris path just in case files are available
        swe.set_ephe_path(EPHE_PATH)

        # Always use Moshier mode (built-in) since ephemeris files might not be available
        swe.set_ephe_path(None)  # This forces Moshier mode

        # Define functions with Moshier flag always set
        def calc(jd, planet, iflag=0):
            iflag |= SEFLG_MOSEPH  # Always use Moshier theory
            return swe.calc(jd, planet, iflag)

        def calc_ut(jd, planet, iflag=0):
            iflag |= SEFLG_MOSEPH  # Always use Moshier theory
            return swe.calc_ut(jd, planet, iflag)

        # Export other functions directly
        julday = swe.julday
        houses = swe.houses
        houses_ex = swe.houses_ex
        set_ephe_path = swe.set_ephe_path
        set_sid_mode = swe.set_sid_mode
        get_ayanamsa_ut = swe.get_ayanamsa_ut
        get_ayanamsa_name = swe.get_ayanamsa_name
        set_topo = swe.set_topo

    except ImportError:
        # Create a fallback module if pyswisseph is not available
        logger.warning("Swiss Ephemeris (pyswisseph) is not available. Using fallback implementation.")

        # Create a dummy module for the SwissEph functions to prevent crashes
        class DummySwe:
            """Fallback implementation for SwissEph when the library is not available."""

            def set_ephe_path(self, path):
                logger.warning("SwissEph not available - set_ephe_path has no effect")
                return 0

            def set_sid_mode(self, mode, t0=0, ayan_t0=0):
                logger.warning("SwissEph not available - set_sid_mode has no effect")
                return 0

            def get_ayanamsa_ut(self, jd_ut):
                logger.warning("SwissEph not available - returning default ayanamsa 23.0")
                return 23.0

            def get_ayanamsa_name(self, ayanamsa_flag):
                return "SwissEph Not Available"

            def set_topo(self, lon, lat, alt):
                logger.warning("SwissEph not available - set_topo has no effect")
                return 0

            def calc(self, jd, planet, iflag=0):
                logger.warning(f"SwissEph not available - returning default position for planet {planet}")
                return [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)], 0

            def calc_ut(self, jd, planet, iflag=0):
                logger.warning(f"SwissEph not available - returning default position for planet {planet}")
                return [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)], 0

            def houses_ex(self, jd_ut, lat, lon, hsys):
                logger.warning("SwissEph not available - returning default houses")
                return [[0.0] * 13, [0.0] * 13, [0.0] * 13, [0.0] * 13, [0.0] * 13, 0.0]

            def julday(self, year, month, day, hour):
                import datetime
                dt = datetime.datetime(year, month, day, int(hour), int((hour % 1) * 60))
                # Simple calculation of Julian day
                a = (14 - month) // 12
                y = year + 4800 - a
                m = month + 12 * a - 3
                jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
                return jdn + (hour - 12) / 24

            def houses(self, jd_ut, lat, lon, hsys):
                logger.warning("SwissEph not available - returning default houses")
                return [[0.0] * 13, [0.0] * 13, 0.0]

        swe = DummySwe()
