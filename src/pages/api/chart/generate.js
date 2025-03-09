/**
 * Mock API handler for chart generation
 * For testing purposes, this returns predefined response data
 */
export default function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Extract the data from the request body
  const {
    fullName,
    birthDate,
    birthTime,
    latitude,
    longitude,
    timezone
  } = req.body;

  // Simulating API processing delay
  setTimeout(() => {
    // Generate a unique chart ID
    const chart_id = `chart_${Date.now().toString(36)}`;

    // Return a successful response
    res.status(200).json({
      chart_id,
      success: true,
      data: {
        name: fullName,
        date: birthDate,
        time: birthTime,
        coordinates: {
          latitude,
          longitude
        },
        timezone
      },
      message: 'Chart generated successfully'
    });
  }, 1500); // 1.5 second delay to simulate processing
}
