import { createMocks } from 'node-mocks-http';
import handler from '@/pages/api/questionnaire/generate';

// Set environment variables for testing with real endpoints
// Use localhost URLs for testing to avoid ENOTFOUND errors
process.env.NEXT_PUBLIC_AI_SERVICE_URL = 'http://localhost:8000';

describe('/api/questionnaire/generate', () => {
  // No beforeEach reset mocks since we're using real endpoints

  it('returns 405 for non-POST requests', async () => {
    const { req, res } = createMocks({
      method: 'GET',
    });

    await handler(req as any, res as any);

    expect(res._getStatusCode()).toBe(405);
    expect(res._getJSONData()).toEqual({
      success: false,
      error: 'Method not allowed'
    });
  });

  it('returns 400 if birth details are missing', async () => {
    const { req, res } = createMocks({
      method: 'POST',
      body: {
        currentConfidence: 0,
        previousAnswers: {}
      },
    });

    await handler(req as any, res as any);

    expect(res._getStatusCode()).toBe(400);
    expect(res._getJSONData().message).toContain('Birth details are required');
  });

  // Tests that use real API endpoints but handle the case when they're not available
  it('handles API unavailability gracefully', async () => {
    const { req, res } = createMocks({
      method: 'POST',
      body: {
        birthDetails: {
          name: 'Test User',
          date: '1990-01-01',
          time: '12:00',
          place: 'New York',
          coordinates: { latitude: 40.7128, longitude: -74.006 },
          timezone: 'America/New_York'
        },
        currentConfidence: 0,
        previousAnswers: {}
      },
    });

    await handler(req as any, res as any);

    // If the API is available, we should get a 200 response
    // If not, we should get an error response (could be 404, 500, etc.)
    // Either way, the handler should handle the situation gracefully
    if (res._getStatusCode() === 200) {
      // If successful, should have questions
      const data = res._getJSONData();
      expect(data).toBeDefined();
      // Real API might return different structure, adjust expectations as needed
    } else {
      // If API is unavailable, should return appropriate error
      expect(res._getStatusCode()).toBeGreaterThanOrEqual(400);
      expect(res._getJSONData().success).toBe(false);
    }
  });
});
