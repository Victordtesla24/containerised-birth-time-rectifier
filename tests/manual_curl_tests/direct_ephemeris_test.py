"""
Temporary endpoint to test direct ephemeris calculations without mocks
"""
import os
import sys
import json
from datetime import datetime
import uuid

# Ensure the current directory is in the path to import properly
sys.path.insert(0, os.path.abspath('.'))

# Import Swiss Ephemeris directly
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    print("Swiss Ephemeris not available")

def calculate_chart(year, month, day, hour, minute, latitude, longitude):
    """
    Calculate a birth chart using Swiss Ephemeris directly
    """
    # Set ephemeris path if available
    ephe_path = os.environ.get('SWISSEPH_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ai_service', 'ephemeris'))
    if os.path.exists(ephe_path):
        swe.set_ephe_path(ephe_path)
    else:
        # Try to find ephemeris files in standard locations
        possible_paths = [
            '/app/ephemeris',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ephemeris'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ai_service', 'ephemeris')
        ]
        for path in possible_paths:
            if os.path.exists(path):
                swe.set_ephe_path(path)
                break

    # Set the sidereal mode to Lahiri (commonly used in Vedic astrology)
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # Convert date and time to Julian day
    birth_datetime = datetime(year, month, day, hour, minute)
    jd = swe.julday(
        year, month, day,
        hour + minute / 60.0
    )

    # Calculate houses
    houses_result = swe.houses(jd, latitude, longitude, b'P')  # Use Placidus house system
    house_cusps = houses_result[0]
    ascmc = houses_result[1]

    # Initialize chart data
    chart_data = {
        "chart_id": f"chart_{uuid.uuid4().hex[:10]}",
        "date": birth_datetime.strftime("%Y-%m-%d"),
        "time": birth_datetime.strftime("%H:%M"),
        "latitude": latitude,
        "longitude": longitude,
        "calculation_type": "real_ephemeris",
        "houses": [float(h) for h in house_cusps[1:13]],  # House cusps
        "angles": {
            "asc": {
                "name": "Ascendant",
                "longitude": float(ascmc[0]),
                "sign": get_zodiac_sign(float(ascmc[0])),
                "degree": float(ascmc[0]) % 30
            },
            "mc": {
                "name": "Midheaven",
                "longitude": float(ascmc[1]),
                "sign": get_zodiac_sign(float(ascmc[1])),
                "degree": float(ascmc[1]) % 30
            }
        },
        "planets": {}
    }

    # Calculate planet positions
    planets = [
        (swe.SUN, "Sun"),
        (swe.MOON, "Moon"),
        (swe.MERCURY, "Mercury"),
        (swe.VENUS, "Venus"),
        (swe.MARS, "Mars"),
        (swe.JUPITER, "Jupiter"),
        (swe.SATURN, "Saturn"),
        (swe.URANUS, "Uranus"),
        (swe.NEPTUNE, "Neptune"),
        (swe.PLUTO, "Pluto"),
        (swe.MEAN_NODE, "North Node")
    ]

    for planet_id, planet_name in planets:
        try:
            # Calculate position
            result = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
            lon = result[0][0]  # Longitude
            lat = result[0][1]  # Latitude
            speed = result[0][3]  # Speed in longitude

            # Get zodiac sign
            sign = get_zodiac_sign(lon)

            # Get house position
            house = get_house_position(chart_data["houses"], lon)

            # Add to chart data
            chart_data["planets"][planet_name.lower()] = {
                "name": planet_name,
                "longitude": float(lon),
                "latitude": float(lat),
                "speed": float(speed),
                "sign": sign,
                "house": house,
                "retrograde": speed < 0
            }
        except Exception as e:
            chart_data["planets"][planet_name.lower()] = {
                "name": planet_name,
                "error": str(e)
            }

    return chart_data

def get_zodiac_sign(longitude):
    """Get the zodiac sign for a given longitude"""
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

def get_house_position(houses, longitude):
    """Get the house position for a given longitude"""
    # Normalize to 0-360 range
    longitude = longitude % 360

    # Loop through houses to find which one contains the longitude
    for i in range(12):
        house_start = houses[i]
        house_end = houses[(i+1) % 12]

        # Handle case where house crosses 0 degrees
        if house_end < house_start:
            if longitude >= house_start or longitude < house_end:
                return i + 1
        else:
            if house_start <= longitude < house_end:
                return i + 1

    # Default to house 1 if not found (shouldn't happen)
    return 1

# Main function to test the calculation
if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: python direct_ephemeris_test.py YYYY MM DD HH MM latitude longitude")
        sys.exit(1)

    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        day = int(sys.argv[3])
        hour = int(sys.argv[4])
        minute = int(sys.argv[5])
        latitude = float(sys.argv[6])
        longitude = float(sys.argv[7])

        if SWISSEPH_AVAILABLE:
            result = calculate_chart(year, month, day, hour, minute, latitude, longitude)
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps({"error": "Swiss Ephemeris not available"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
