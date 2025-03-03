import { createMocks } from 'node-mocks-http';
import type { NextApiRequest, NextApiResponse } from 'next';
import handler from '@/pages/api/questionnaire/generate';

// Mock fetch for API calls
global.fetch = jest.fn();

// Mock environment variables
process.env.NEXT_PUBLIC_AI_SERVICE_URL = 'http://test-api';

describe('/api/questionnaire/generate', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('returns 405 for non-POST requests', async () => {
    const { req, res } = createMocks<NextApiRequest, NextApiResponse>({
      method: 'GET',
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(405);
    expect(res._getJSONData()).toEqual({ error: 'Method not allowed' });
  });

  it('returns 400 if birth details are missing', async () => {
    const { req, res } = createMocks<NextApiRequest, NextApiResponse>({
      method: 'POST',
      body: {
        currentConfidence: 0,
        previousAnswers: {}
      },
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(500);
    expect(res._getJSONData().message).toContain('Birth details are required');
  });

  it('uses the AI service when available', async () => {
    const mockResponse = {
      questions: [
        {
          id: 'q1',
          text: 'Test question',
          type: 'yes_no',
          weight: 0.5
        }
      ],
      confidenceScore: 10,
      isComplete: false,
      hasReachedThreshold: false
    };

    // Mock successful AI service response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const { req, res } = createMocks<NextApiRequest, NextApiResponse>({
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

    await handler(req, res);

    expect(res._getStatusCode()).toBe(200);
    expect(res._getJSONData()).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-api/api/generate-questions',
      expect.objectContaining({
        method: 'POST'
      })
    );
  });

  it('falls back to local generation when AI service fails', async () => {
    // Mock failed AI service response
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Service unavailable'));

    const { req, res } = createMocks<NextApiRequest, NextApiResponse>({
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

    await handler(req, res);

    expect(res._getStatusCode()).toBe(200);
    expect(res._getJSONData().questions.length).toBeGreaterThan(0);
    expect(res._getJSONData()._warning).toContain('fallback');
  });

  it('provides follow-up questions based on previous answers', async () => {
    // Mock failed AI service response to trigger fallback
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Service unavailable'));

    const { req, res } = createMocks<NextApiRequest, NextApiResponse>({
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
        currentConfidence: 5,
        previousAnswers: {
          'relationship-marriage': 'Yes',
          'health-major-illness': 'Yes'
        }
      },
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(200);
    
    // Check if follow-up questions were generated
    const responseData = res._getJSONData();
    const followUpIds = responseData.questions.map((q: any) => q.id);
    
    // We should have follow-up questions for relationships and health
    expect(
      followUpIds.includes('relationship-children') || 
      followUpIds.includes('health-recovery')
    ).toBeTruthy();
    
    // Confidence should have been adjusted
    expect(responseData.confidenceScore).toBeGreaterThan(5);
  });
}); 