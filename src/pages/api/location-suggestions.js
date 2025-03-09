/**
 * Mock API handler for location suggestions
 * Returns a list of location suggestions based on the query
 */
export default function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Get query from request query parameters
  const { query } = req.query;

  if (!query || query.length < 3) {
    return res.status(400).json({
      error: 'Query must be at least 3 characters long',
      suggestions: []
    });
  }

  // Default suggestions (empty list)
  let suggestions = [];

  // Match query to predefined locations and generate suggestions
  const queryLower = query.toLowerCase();

  if (queryLower.includes('pune') || queryLower.includes('maha')) {
    suggestions = [
      { display_name: 'Pune, Maharashtra, India', lat: 18.5204, lon: 73.8567 },
      { display_name: 'Pimpri-Chinchwad, Maharashtra, India', lat: 18.6298, lon: 73.8131 },
      { display_name: 'Puna, Gujarat, India', lat: 21.6412, lon: 71.1636 }
    ];
  } else if (queryLower.includes('new') || queryLower.includes('york')) {
    suggestions = [
      { display_name: 'New York City, New York, United States', lat: 40.7128, lon: -74.0060 },
      { display_name: 'New York Mills, Minnesota, United States', lat: 46.5180, lon: -95.3763 },
      { display_name: 'New Yorke, South Australia, Australia', lat: -34.6373, lon: 137.5696 }
    ];
  } else if (queryLower.includes('lon')) {
    suggestions = [
      { display_name: 'London, England, United Kingdom', lat: 51.5074, lon: -0.1278 },
      { display_name: 'London, Ontario, Canada', lat: 42.9849, lon: -81.2453 },
      { display_name: 'Long Beach, California, United States', lat: 33.7701, lon: -118.1937 }
    ];
  } else if (queryLower.includes('tok')) {
    suggestions = [
      { display_name: 'Tokyo, Japan', lat: 35.6762, lon: 139.6503 },
      { display_name: 'Tokushima, Japan', lat: 34.0658, lon: 134.5593 },
      { display_name: 'Tokoname, Aichi, Japan', lat: 34.8865, lon: 136.8429 }
    ];
  }

  // Add a small delay to simulate network latency
  setTimeout(() => {
    res.status(200).json({ suggestions });
  }, 300);
}
