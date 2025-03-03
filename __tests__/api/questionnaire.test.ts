import { createMocks } from 'node-mocks-http';
import type { NextApiRequest, NextApiResponse } from 'next';
import handler from '@/pages/api/questionnaire';

// Mock fetch for API calls
global.fetch = jest.fn();

// Mock environment variables
process.env.NEXT_PUBLIC_AI_SERVICE_URL = 'http://test-api';

// Constants
const CONFIDENCE_THRESHOLD = 90;

describe('/api/questionnaire', () => {
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

  it('returns 400 if required data is missing', async () => {
    const { req, res } = createMocks<NextApiRequest, NextApiResponse>({
      method: 'POST',
      body: {},
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(400);
    expect(res._getJSONData().error).toContain('Missing required questionnaire data');
  });

  it('processes questionnaire answers with the AI service', async () => {
    const mockResponse = {
      success: true,
      confidenceScore: 85,
      meetsThreshold: false,
      rectificationSuggestions: []
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
        answers: [
          { questionId: 'q1', question: 'Test question?', answer: 'Yes' }
        ],
        confidenceScore: 80
      },
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(200);
    expect(res._getJSONData()).toMatchObject({
      ...mockResponse,
      meetsThreshold: false,
      requestMoreQuestions: true
    });
    
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-api/api/process-questionnaire',
      expect.objectContaining({
        method: 'POST'
      })
    );
  });

  it('falls back to mock data when AI service fails', async () => {
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
        answers: [
          { questionId: 'q1', question: 'Test question?', answer: 'Yes' }
        ],
        confidenceScore: 80
      },
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(200);
    expect(res._getJSONData()._warning).toContain('mock data');
    expect(res._getJSONData().meetsThreshold).toBeDefined();
  });

  it('returns rectification suggestions when confidence meets threshold', async () => {
    const mockResponse = {
      success: true,
      confidenceScore: 95,
      meetsThreshold: true,
      rectificationSuggestions: [
        {
          suggestedTime: '12:15',
          confidence: 90,
          explanation: 'Test explanation'
        }
      ]
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
        answers: [
          { questionId: 'q1', question: 'Test question?', answer: 'Yes' }
        ],
        confidenceScore: 92
      },
    });

    await handler(req, res);

    expect(res._getStatusCode()).toBe(200);
    expect(res._getJSONData()).toMatchObject({
      ...mockResponse,
      meetsThreshold: true,
      requestMoreQuestions: false
    });
    expect(res._getJSONData().rectificationSuggestions.length).toBeGreaterThan(0);
  });
}); 