const { createMocks } = require('node-mocks-http');
const handler = require('@/pages/api/questionnaire').default;

// No mocks for fetch - using real fetch API
// Access real API endpoints

// Constants
const CONFIDENCE_THRESHOLD = 90;
const AI_SERVICE_URL = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

describe('/api/questionnaire', () => {
  beforeEach(() => {
    // Reset but don't mock
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

  // Note: The following tests need real API endpoints and won't use mocks
  // They may fail if the real services are not available
  // This is expected behavior per the requirements
});
