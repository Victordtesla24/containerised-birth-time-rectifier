import { createMocks } from 'node-mocks-http';
import handler from '@/pages/api/questionnaire';

// Constants for validation using real environment values
const CONFIDENCE_THRESHOLD = 90;
const API_SERVICE_URL = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

describe('/api/questionnaire', () => {
  beforeEach(() => {
    // No mocking - use real API endpoints
    process.env.NODE_ENV = 'test';
  });

  it('returns 405 for non-POST requests', async () => {
    const { req, res } = createMocks({
      method: 'GET',
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(405);
    expect(res._getJSONData()).toEqual({
      success: false,
      error: 'Method not allowed'
    });
  });

  it('returns 400 if required data is missing', async () => {
    const { req, res } = createMocks({
      method: 'POST',
      body: {},
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(400);
    expect(res._getJSONData().error).toContain('Missing required questionnaire data');
  });

  it('processes valid questionnaire data with real API service', async () => {
    // This test hits the real AI service
    // It will fail if the service is unavailable, which is expected per requirements

    // Construct proper data according to API requirements
    const birthDetails = {
      name: 'Test User',
      birthDate: '1990-01-01',
      approximateTime: '12:00',
      birthLocation: 'New York, NY, USA',
      coordinates: {
        latitude: 40.7128,
        longitude: -74.0060
      },
      timezone: 'America/New_York'
    };

    const answers = [
      {
        questionId: '1',
        question: 'Have you experienced a major career change around age 30?',
        answer: 'Yes'
      }
    ];

    const confidenceScore = 20; // Starting confidence

    const { req, res } = createMocks({
      method: 'POST',
      body: {
        birthDetails,
        answers,
        confidenceScore
      },
    });

    // Call the API handler
    await handler(req, res);

    // If the real API is down, this test will fail
    // This is expected behavior per the requirements
    if (res._getStatusCode() === 200) {
      const data = res._getJSONData();
      expect(data.success).toBe(true);
      if (data.questions) {
        expect(Array.isArray(data.questions)).toBe(true);
      }
      if (data.confidenceScore !== undefined) {
        expect(typeof data.confidenceScore).toBe('number');
      }
    } else {
      // Log the error but don't mask it - still fail the test as requested
      console.error('Real API returned error:', res._getStatusCode(), res._getJSONData());
      throw new Error(`API returned status ${res._getStatusCode()}: ${JSON.stringify(res._getJSONData())}`);
    }
  });
});
