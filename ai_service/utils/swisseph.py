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
SEFLG_MOSEPH = 4
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

# Try two different import approaches to handle different installation methods
SWISSEPH_AVAILABLE = False
try:
    # Try the standard import first
    import pyswisseph as swe # type: ignore
    logger.info("Using standard pyswisseph package")
    SWISSEPH_AVAILABLE = True

    # Re-export all functions and constants
    calc = swe.calc
    calc_ut = swe.calc_ut
    julday = swe.julday
    houses = swe.houses
    houses_ex = swe.houses_ex
    set_ephe_path = swe.set_ephe_path
    set_sid_mode = swe.set_sid_mode
    get_ayanamsa_ut = swe.get_ayanamsa_ut
    get_ayanamsa_name = swe.get_ayanamsa_name
    set_topo = swe.set_topo

except ImportError:
    try:
        # Try alternative import path (for some environments)
        import swisseph as swe
        logger.info("Using alternative swisseph package")
        SWISSEPH_AVAILABLE = True

        # Re-export all functions and constants
        calc = swe.calc
        calc_ut = swe.calc_ut
        julday = swe.julday
        houses = swe.houses
        houses_ex = swe.houses_ex
        set_ephe_path = swe.set_ephe_path
        set_sid_mode = swe.set_sid_mode
        get_ayanamsa_ut = swe.get_ayanamsa_ut
        get_ayanamsa_name = swe.get_ayanamsa_name
        set_topo = swe.set_topo

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

        def houses_ex(jd, lat, lon, hsys):
            """Extended house calculation - fallback implementation"""
            # Get basic house data
            cusps, ascendant, mc, armc, vertex, equatorial_ascendant = houses(jd, lat, lon, hsys)

            # Add additional data for houses_ex
            # This is a simplified version
            return {
                'cusps': cusps,
                'ascendant': ascendant,
                'mc': mc,
                'armc': armc,
                'vertex': vertex,
                'equatorial_ascendant': equatorial_ascendant
            }

        def set_ephe_path(path=None):
            """Dummy function for setting ephemeris path"""
            logger.warning("Ephemeris path cannot be set because swisseph is not available")
            return

        def set_sid_mode(sid_mode, t0=0, ayan_t0=0):
            """Dummy function for setting sidereal mode"""
            logger.warning("Setting sidereal mode not available because swisseph is not available")
            return

        def get_ayanamsa_ut(jd_ut):
            """Dummy function for getting ayanamsa"""
            # Return a reasonable default value for Lahiri ayanamsa
            return 23.6647

        def get_ayanamsa_name(sid_mode):
            """Dummy function for getting ayanamsa name"""
            ayanamsa_names = {
                SIDM_FAGAN_BRADLEY: "Fagan/Bradley",
                SIDM_LAHIRI: "Lahiri",
                SIDM_DELUCE: "De Luce",
                SIDM_RAMAN: "Raman",
                SIDM_USHASHASHI: "Ushashashi",
                SIDM_KRISHNAMURTI: "Krishnamurti",
                SIDM_DJWHAL_KHUL: "Djwhal Khul",
                SIDM_YUKTESHWAR: "Yukteshwar",
                SIDM_JN_BHASIN: "JN Bhasin",
                SIDM_BABYL_KUGLER1: "Babylonian Kugler 1",
                SIDM_BABYL_KUGLER2: "Babylonian Kugler 2",
                SIDM_BABYL_KUGLER3: "Babylonian Kugler 3",
                SIDM_BABYL_HUBER: "Babylonian Huber",
                SIDM_BABYL_ETPSC: "Babylonian ETPSC",
                SIDM_ALDEBARAN_15TAU: "Aldebaran 15 Taurus",
                SIDM_HIPPARCHOS: "Hipparchos",
                SIDM_SASSANIAN: "Sassanian",
                SIDM_GALCENT_0SAG: "Galactic Center at 0 Sagittarius",
                SIDM_J2000: "J2000",
                SIDM_J1900: "J1900",
                SIDM_B1950: "B1950",
                SIDM_SURYASIDDHANTA: "Suryasiddhanta",
                SIDM_SURYASIDDHANTA_MSUN: "Suryasiddhanta Mean Sun",
                SIDM_ARYABHATA: "Aryabhata",
                SIDM_ARYABHATA_MSUN: "Aryabhata Mean Sun",
                SIDM_SS_REVATI: "SS Revati",
                SIDM_SS_CITRA: "SS Citra",
                SIDM_TRUE_CITRA: "True Citra",
                SIDM_TRUE_REVATI: "True Revati",
                SIDM_TRUE_PUSHYA: "True Pushya",
                SIDM_GALCENT_RGILBRAND: "Galactic Center (Gil Brand)",
                SIDM_GALEQU_IAU1958: "Galactic Equator IAU 1958",
                SIDM_GALEQU_TRUE: "True Galactic Equator",
                SIDM_GALEQU_MULA: "Galactic Equator Mula",
                SIDM_GALALIGN_MARDYKS: "Galactic Alignment (Mardyks)",
                SIDM_TRUE_MULA: "True Mula",
                SIDM_GALCENT_MULA_WILHELM: "Galactic Center Mula (Wilhelm)",
                SIDM_ARYABHATA_522: "Aryabhata 522",
                SIDM_BABYL_BRITTON: "Babylonian (Britton)",
                SIDM_TRUE_SHEORAN: "True Sheoran",
                SIDM_GALCENT_COCHRANE: "Galactic Center (Cochrane)",
                SIDM_GALEQU_FIORENZA: "Galactic Equator (Fiorenza)",
                SIDM_VALENS_MOON: "Valens Moon",
                SIDM_LAHIRI_1940: "Lahiri 1940",
                SIDM_LAHIRI_VP285: "Lahiri VP285",
                SIDM_KRISHNAMURTI_VP291: "Krishnamurti VP291",
                SIDM_LAHIRI_ICRC: "Lahiri ICRC"
            }
            return ayanamsa_names.get(sid_mode, "Unknown")

        def set_topo(lon: float, lat: float, alt: float = 0.0):
            """
            Set the geographic location for topocentric planet computation.

            Args:
                lon: Geographic longitude (eastern is positive, western is negative)
                lat: Geographic latitude (northern is positive, southern is negative)
                alt: Altitude above sea in meters (optional, default=0)
            """
            logger.warning("set_topo is not implemented in fallback mode, using pass-through")
            # This is a stub - in fallback mode, this function does nothing
            # But we record the values for potential use in other functions
            global _geo_lon, _geo_lat, _geo_alt
            _geo_lon = lon
            _geo_lat = lat
            _geo_alt = alt
            return

        # Initialize geographic position variables for fallback calculations
        _geo_lon = 0.0
        _geo_lat = 0.0
        _geo_alt = 0.0

        logger.warning("Using fallback calculations - results will be approximate")
