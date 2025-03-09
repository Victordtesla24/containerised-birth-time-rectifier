/**
 * Mock geocoding API handler
 * Returns predefined coordinates and timezone data for testing
 */
export default function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Get query from request body
  const { query } = req.body;

  if (!query) {
    return res.status(400).json({ error: 'Missing location query' });
  }

  // Default mock data (fallback)
  let mockData = {
    results: [
      {
        id: 'loc_default',
        name: 'Test Location',
        country: 'Test Country',
        country_code: 'TC',
        state: 'Test State',
        latitude: 40.0,
        longitude: -74.0,
        timezone: 'America/New_York'
      }
    ]
  };

  // For specific test locations, return predefined data
  const queryLower = query.toLowerCase();

  if (queryLower.includes('pune') || queryLower.includes('maharashtra')) {
    mockData = {
      results: [
        {
          id: 'loc_pune',
          name: 'Pune',
          country: 'India',
          country_code: 'IN',
          state: 'Maharashtra',
          latitude: 18.5204,
          longitude: 73.8567,
          timezone: 'Asia/Kolkata'
        }
      ]
    };
  } else if (queryLower.includes('new york')) {
    mockData = {
      results: [
        {
          id: 'loc_nyc',
          name: 'New York City',
          country: 'United States',
          country_code: 'US',
          state: 'New York',
          latitude: 40.7128,
          longitude: -74.0060,
          timezone: 'America/New_York'
        }
      ]
    };
  } else if (queryLower.includes('london')) {
    mockData = {
      results: [
        {
          id: 'loc_london',
          name: 'London',
          country: 'United Kingdom',
          country_code: 'GB',
          state: 'England',
          latitude: 51.5074,
          longitude: -0.1278,
          timezone: 'Europe/London'
        }
      ]
    };
  } else if (queryLower.includes('tokyo')) {
    mockData = {
      results: [
        {
          id: 'loc_tokyo',
          name: 'Tokyo',
          country: 'Japan',
          country_code: 'JP',
          state: 'Tokyo',
          latitude: 35.6762,
          longitude: 139.6503,
          timezone: 'Asia/Tokyo'
        }
      ]
    };
  }

  // Add a small delay to simulate network latency
  setTimeout(() => {
    res.status(200).json(mockData);
  }, 500);
}
