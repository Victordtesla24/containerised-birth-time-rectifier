import axios from 'axios';

// Define the response structure for geocoding
interface GeocodingResult {
  latitude: number;
  longitude: number;
  timezone?: string;
}

/**
 * Geocode a birth place to get coordinates and timezone
 * @param birthPlace The birth place to geocode
 * @returns The geocoded result with latitude, longitude and timezone
 */
export const geocodeBirthPlace = async (birthPlace: string): Promise<GeocodingResult> => {
  try {
    // Always make real API request to geocoding service without mock fallbacks
    const response = await axios.get('/api/v1/geocode', {
      params: { address: birthPlace }
    });

    if (response.data && response.data.results && response.data.results.length > 0) {
      const { latitude, longitude, timezone } = response.data.results[0];
      return { latitude, longitude, timezone };
    }

    throw new Error('No results found for this location');
  } catch (error) {
    console.error('Geocoding error:', error);
    throw new Error('Failed to geocode location');
  }
};

/**
 * Geocode a location to get coordinates
 * @param location The location to geocode
 * @param placeId Optional place ID for more accurate geocoding
 * @returns The geocoded result with latitude and longitude
 */
export const geocodeLocation = async (location: string, placeId?: string): Promise<GeocodingResult> => {
  try {
    // Always make real API request to geocoding service without mock fallbacks
    const response = await axios.get('/api/v1/geocode', {
      params: {
        address: location,
        place_id: placeId
      }
    });

    if (response.data && response.data.results && response.data.results.length > 0) {
      const { latitude, longitude, timezone } = response.data.results[0];
      return { latitude, longitude, timezone };
    }

    throw new Error('No results found for this location');
  } catch (error) {
    console.error('Geocoding error:', error);
    throw new Error('Failed to geocode location');
  }
};

/**
 * Get a formatted display string for coordinates
 * @param latitude Latitude coordinate
 * @param longitude Longitude coordinate
 * @returns Formatted string with cardinal directions
 */
export const formatCoordinates = (latitude: number, longitude: number): string => {
  const latDir = latitude >= 0 ? 'N' : 'S';
  const longDir = longitude >= 0 ? 'E' : 'W';
  return `${Math.abs(latitude).toFixed(4)}° ${latDir}, ${Math.abs(longitude).toFixed(4)}° ${longDir}`;
};
