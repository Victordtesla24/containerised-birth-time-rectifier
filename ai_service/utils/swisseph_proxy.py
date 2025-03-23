"""
Swiss Ephemeris Proxy Module

This module serves as a compatibility layer for Swiss Ephemeris.
It imports pyswisseph and re-exports its functionality under the 'swisseph' namespace.
"""

import logging
import os
import sys
from typing import Any, List, Dict, Tuple, Callable

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

# House systems
HOUSES_PLACIDUS = b'P'
HOUSES_KOCH = b'K'
HOUSES_PORPHYRIUS = b'O'
HOUSES_REGIOMONTANUS = b'R'
HOUSES_CAMPANUS = b'C'
HOUSES_EQUAL = b'E'
HOUSES_WHOLE_SIGN = b'W'

# Set ephemeris path from environment
EPHE_PATH = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")

# Define real implementations using pyswisseph
def _real_calc(jd, planet, iflag=0):
    """Calculate planet positions."""
    return _swe.calc(jd, planet, iflag)

def _real_calc_ut(jd, planet, iflag=0):
    """Calculate planet positions using UT."""
    return _swe.calc_ut(jd, planet, iflag)

def _real_julday(year, month, day, hour):
    """Calculate Julian day."""
    return _swe.julday(year, month, day, hour)

def _real_houses(jd, lat, lon, hsys=b'P'):
    """Calculate houses."""
    return _swe.houses(jd, lat, lon, hsys)

def _real_houses_ex(jd, lat, lon, hsys=b'P'):
    """Calculate houses with extra information."""
    return _swe.houses_ex(jd, lat, lon, hsys)

def _real_set_ephe_path(path):
    """Set ephemeris path."""
    return _swe.set_ephe_path(path)

def _real_set_sid_mode(sid_mode, t0=0, ayan_t0=0):
    """Set sidereal mode."""
    return _swe.set_sid_mode(sid_mode, t0, ayan_t0)

def _real_get_ayanamsa_ut(jd_ut):
    """Get ayanamsa value for UT time."""
    return _swe.get_ayanamsa_ut(jd_ut)

def _real_get_ayanamsa_name(sidmode):
    """Get ayanamsa name."""
    return _swe.get_ayanamsa_name(sidmode)

def _real_set_topo(lon, lat, alt):
    """Set topocentric location."""
    return _swe.set_topo(lon, lat, alt)

# Define fallback implementations
def _fallback_calc(jd, planet, iflag=0):
    """Fallback calculation function."""
    logger.warning(f"Using fallback calculation for planet {planet} (no pyswisseph)")
    return [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0]

def _fallback_calc_ut(jd, planet, iflag=0):
    """Fallback calculation function using UT."""
    logger.warning(f"Using fallback calculation for planet {planet} (no pyswisseph)")
    return [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0]

def _fallback_julday(year, month, day, hour):
    """Simple Julian day calculation without pyswisseph."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jd = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd += (hour / 24.0)
    return jd

def _fallback_houses(jd, lat, lon, hsys=b'P'):
    """Fallback houses calculation."""
    logger.warning("Using fallback houses calculation (no pyswisseph)")
    # Return a minimal structure that won't cause code to crash
    house_cusps = [float(i * 30) for i in range(13)]  # 12 houses plus extra value
    ascmc = [0.0, 90.0, 180.0, 270.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # Basic angles
    return [house_cusps, ascmc]

def _fallback_houses_ex(jd, lat, lon, hsys=b'P'):
    """Fallback houses calculation with extra information."""
    logger.warning("Using fallback houses_ex calculation (no pyswisseph)")
    house_cusps, ascmc = _fallback_houses(jd, lat, lon, hsys)
    # Extra dummy data to match the structure
    return [house_cusps, ascmc, 0.0]

def _fallback_set_ephe_path(path):
    """Dummy ephemeris path setter."""
    logger.warning(f"Ignoring set_ephe_path({path}) - pyswisseph not available")
    return None

def _fallback_set_sid_mode(sid_mode, t0=0, ayan_t0=0):
    """Dummy sidereal mode setter."""
    logger.warning(f"Ignoring set_sid_mode({sid_mode}) - pyswisseph not available")
    return None

def _fallback_get_ayanamsa_ut(jd_ut):
    """Fallback ayanamsa calculation."""
    logger.warning(f"Using fallback ayanamsa calculation (no pyswisseph)")
    return 23.0  # Common approximate value for Lahiri ayanamsa

def _fallback_get_ayanamsa_name(sidmode):
    """Fallback ayanamsa name getter."""
    ayanamsa_names = ["Fagan/Bradley", "Lahiri", "De Luce", "Raman", "Ushashashi", "Krishnamurti"]
    if 0 <= sidmode < len(ayanamsa_names):
        return ayanamsa_names[sidmode]
    return "Unknown"

def _fallback_set_topo(lon, lat, alt):
    """Dummy topocentric setter."""
    logger.warning(f"Ignoring set_topo({lon}, {lat}, {alt}) - pyswisseph not available")
    return None

# Try to import pyswisseph and initialize the module
try:
    import pyswisseph as _swe
    logger.info("Successfully imported pyswisseph")

    # Initialize the ephemeris path
    _swe.set_ephe_path(EPHE_PATH)
    logger.info(f"Swiss Ephemeris path set to: {EPHE_PATH}")

    # Assign the real implementation functions
    calc = _real_calc
    calc_ut = _real_calc_ut
    julday = _real_julday
    houses = _real_houses
    houses_ex = _real_houses_ex
    set_ephe_path = _real_set_ephe_path
    set_sid_mode = _real_set_sid_mode
    get_ayanamsa_ut = _real_get_ayanamsa_ut
    get_ayanamsa_name = _real_get_ayanamsa_name
    set_topo = _real_set_topo

    SWISSEPH_AVAILABLE = True

except ImportError:
    logger.warning("Could not import pyswisseph. Using fallback calculations.")

    # Assign the fallback implementation functions
    calc = _fallback_calc
    calc_ut = _fallback_calc_ut
    julday = _fallback_julday
    houses = _fallback_houses
    houses_ex = _fallback_houses_ex
    set_ephe_path = _fallback_set_ephe_path
    set_sid_mode = _fallback_set_sid_mode
    get_ayanamsa_ut = _fallback_get_ayanamsa_ut
    get_ayanamsa_name = _fallback_get_ayanamsa_name
    set_topo = _fallback_set_topo

    SWISSEPH_AVAILABLE = False

# Export symbols for module users
__all__ = [
    "SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN",
    "URANUS", "NEPTUNE", "PLUTO", "MEAN_NODE", "TRUE_NODE", "CHIRON",
    "SIDM_FAGAN_BRADLEY", "SIDM_LAHIRI", "SIDM_RAMAN", "SIDM_KRISHNAMURTI",
    "SIDM_DJWHAL_KHUL", "FLG_SWIEPH", "FLG_SPEED", "SEFLG_SIDEREAL",
    "calc", "calc_ut", "julday", "houses", "houses_ex",
    "set_ephe_path", "set_sid_mode", "get_ayanamsa_ut", "get_ayanamsa_name", "set_topo",
    "SWISSEPH_AVAILABLE"
]
