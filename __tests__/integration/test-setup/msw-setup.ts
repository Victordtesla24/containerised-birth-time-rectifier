import { handlers } from '../../../src/mocks/handlers';

// Mock fetch API for integration tests
export const setupMockAPI = () => {
  beforeAll(() => {
    // Backup the original fetch implementation
    const originalFetch = global.fetch;
    
    // Mock API calls in our tests
    global.fetch = jest.fn().mockImplementation((url: string | URL | Request, options?: RequestInit) => {
      // Convert URL to string if it's an object
      const urlString = typeof url === 'string' ? url : url.toString();
      
      // Return health check success for service checks
      if (urlString.includes('/api/health')) {
        return Promise.resolve({ 
          ok: true,
          json: () => Promise.resolve({ status: 'healthy' })
        });
      }
      
      // Mock geocoding API
      if (urlString.includes('/geocode') || urlString.includes('geocoding')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            latitude: 40.7128,
            longitude: -74.0060,
            timezone: 'America/New_York'
          })
        });
      }
      
      // Mock initial chart API
      if (urlString.includes('/api/initial-chart') || urlString.includes('/api/charts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            chartData: {
              ascendant: 0,
              planets: [
                { id: 'sun', position: 30, house: 1 },
                { id: 'moon', position: 60, house: 2 }
              ],
              houses: Array.from({ length: 12 }, (_, i) => ({
                number: i + 1,
                start: i * 30,
                end: (i + 1) * 30
              }))
            }
          })
        });
      }
      
      // Mock questionnaire API - enhanced to better handle different request patterns
      if (urlString.includes('/api/questionnaire')) {
        // Check if this is for question generation endpoint
        if (urlString.includes('/generate') || (options && options.method === 'POST')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              questions: [
                {
                  id: 'q1',
                  text: 'Do you have any major career changes?',
                  type: 'boolean',
                  options: ['Yes', 'No']
                },
                {
                  id: 'q2',
                  text: 'When did you get married?',
                  type: 'date'
                }
              ],
              confidence: 0.95,
              isComplete: true,
              hasReachedThreshold: true
            })
          });
        } else {
          // For general questionnaire endpoints
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([
              {
                id: 'q1',
                text: 'Do you have any major career changes?',
                type: 'boolean',
                options: ['Yes', 'No']
              },
              {
                id: 'q2',
                text: 'When did you get married?',
                type: 'date'
              }
            ])
          });
        }
      }
      
      // Mock rectification API
      if (urlString.includes('/api/rectify')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            suggestedTime: '12:30:00',
            confidence: 0.85,
            details: {
              ascendantChange: true,
              houseShifts: [1, 3, 5]
            }
          })
        });
      }
      
      // Default response for unhandled requests
      console.log(`Unhandled mock request for: ${urlString}`);
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });
};

// Export a function that creates a custom request handler
export const mockApiCall = (path: string, responseData: any) => {
  // Update the fetch mock for just this specific call
  (global.fetch as jest.Mock).mockImplementationOnce((url: string | URL | Request) => {
    const urlString = typeof url === 'string' ? url : url.toString();
    
    if (urlString.includes(path)) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(responseData)
      });
    }
    
    // Fall back to the default mock with a safe check
    const mockImpl = (global.fetch as jest.Mock).getMockImplementation();
    if (mockImpl) {
      return mockImpl(url);
    }
    
    // Default fallback if no mock implementation is found
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({})
    });
  });
}; 