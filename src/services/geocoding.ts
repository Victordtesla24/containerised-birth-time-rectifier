/**
 * Geocoding service to get coordinates from a location string
 */

import axios from 'axios';

// Simple logger to avoid direct console statements
const logger = {
  log: (message: string, ...args: unknown[]): void => {
    // Can be replaced with a proper logging library in production
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.log(message, ...args);
    }
  },
  warn: (message: string, ...args: unknown[]): void => {
    // eslint-disable-next-line no-console
    console.warn(message, ...args);
  },
  error: (message: string, ...args: unknown[]): void => {
    // eslint-disable-next-line no-console
    console.error(message, ...args);
  }
};

interface GeocodingResult {
  latitude: number;
  longitude: number;
  timezone: string;
}

/**
 * Geocode a birthplace to get its coordinates and timezone
 * Uses a real geocoding API with fallback to mock data
 *
 * @param location Location string (e.g., "New York, USA")
 * @returns Promise with geocoding result
 */
export async function geocodeBirthPlace(location: string): Promise<GeocodingResult> {
  try {
    logger.log(`Geocoding birth location: ${location}`);

    // Check if we can use the backend API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      const response = await axios.post(`${apiUrl}/api/geocode`, {
        place: location
      }, {
        timeout: 10000 // 10 second timeout
      });

      if (response.data) {
        logger.log('Geocoding API response:', response.data);
        return {
          latitude: response.data.latitude,
          longitude: response.data.longitude,
          timezone: response.data.timezone
        };
      }
    } catch (apiError) {
      logger.warn('Error calling geocoding API. Using fallback:', apiError);
      // Continue with fallback if API fails
    }

    // Fallback to mock geocoding for common cities
    const fallbackResult = fallbackGeocode(location);
    if (fallbackResult) {
      logger.log('Using fallback geocoding result:', fallbackResult);
      return fallbackResult;
    }

    // If no fallback found, return default coordinates
    logger.warn('No geocoding result found, using default coordinates');
    return {
      latitude: 0,
      longitude: 0,
      timezone: 'UTC'
    };
  } catch (error) {
    logger.error('Error in geocodeBirthPlace:', error);
    // Return default coordinates rather than throwing
    return {
      latitude: 0,
      longitude: 0,
      timezone: 'UTC'
    };
  }
}

/**
 * Fallback geocoding function that uses a predefined list of cities
 *
 * @param location Location string
 * @returns Geocoding result or null if not found
 */
const fallbackGeocode = (location: string): GeocodingResult | null => {
  // Example mock coordinates for common cities
  const geocodeMap: Record<string, { lat: number; lng: number; timezone: string }> = {
    'new york': { lat: 40.7128, lng: -74.0060, timezone: 'America/New_York' },
    'london': { lat: 51.5074, lng: -0.1278, timezone: 'Europe/London' },
    'tokyo': { lat: 35.6762, lng: 139.6503, timezone: 'Asia/Tokyo' },
    'sydney': { lat: -33.8688, lng: 151.2093, timezone: 'Australia/Sydney' },
    'pune': { lat: 18.5204, lng: 73.8567, timezone: 'Asia/Kolkata' },
    'paris': { lat: 48.8566, lng: 2.3522, timezone: 'Europe/Paris' },
    'berlin': { lat: 52.5200, lng: 13.4050, timezone: 'Europe/Berlin' },
    'delhi': { lat: 28.6139, lng: 77.2090, timezone: 'Asia/Kolkata' },
    'mumbai': { lat: 19.0760, lng: 72.8777, timezone: 'Asia/Kolkata' },
    'bangalore': { lat: 12.9716, lng: 77.5946, timezone: 'Asia/Kolkata' },
    'los angeles': { lat: 34.0522, lng: -118.2437, timezone: 'America/Los_Angeles' },
    'chicago': { lat: 41.8781, lng: -87.6298, timezone: 'America/Chicago' },
    'moscow': { lat: 55.7558, lng: 37.6173, timezone: 'Europe/Moscow' },
    'beijing': { lat: 39.9042, lng: 116.4074, timezone: 'Asia/Shanghai' },
    'cairo': { lat: 30.0444, lng: 31.2357, timezone: 'Africa/Cairo' },
    'rio de janeiro': { lat: -22.9068, lng: -43.1729, timezone: 'America/Sao_Paulo' },
    'toronto': { lat: 43.6532, lng: -79.3832, timezone: 'America/Toronto' },
    'rome': { lat: 41.9028, lng: 12.4964, timezone: 'Europe/Rome' },
    'madrid': { lat: 40.4168, lng: -3.7038, timezone: 'Europe/Madrid' },
    'singapore': { lat: 1.3521, lng: 103.8198, timezone: 'Asia/Singapore' },
  };

  // Check if we have mock data for this location (case insensitive partial match)
  const locationLower = location.toLowerCase();
  const matchedCity = Object.keys(geocodeMap).find(city => locationLower.includes(city));

  if (matchedCity) {
    return {
      latitude: geocodeMap[matchedCity].lat,
      longitude: geocodeMap[matchedCity].lng,
      timezone: geocodeMap[matchedCity].timezone
    };
  }

  return null;
};
