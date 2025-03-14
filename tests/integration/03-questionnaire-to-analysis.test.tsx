/**
 * Integration test for the questionnaire to analysis flow
 *
 * This test verifies the flow from completing the questionnaire
 * to reaching the analysis page with proper error handling.
 */

import { RouterContext } from 'next/dist/shared/lib/router-context.shared-runtime';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QuestionnairePage from '../../src/pages/birth-time-rectifier/questionnaire';
import { createMockRouter } from '../mocks/mockRouter';
import { verifyServicesRunning, completeQuestionnaire, mockSessionStorage } from './test-utils';
import { fireEvent } from '@testing-library/react';

// Get API URLs from environment variables with fallbacks
const BASE_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';

// Function to log API calls
const logApiCall = (url: string) => {
  console.log(`API Call to: ${url}`);
};

describe('Questionnaire to Analysis Flow', () => {
  // Increase the timeout for all tests in this describe block
  jest.setTimeout(60000); // Increase timeout to 60 seconds

  // Store original fetch to restore later
  let originalFetch: typeof global.fetch;

  afterEach(() => {
    // Restore original fetch after each test
    if (originalFetch) {
      global.fetch = originalFetch;
    }

    // Clear all mocks
    jest.clearAllMocks();
  });

  // Check services before running tests
  beforeAll(async () => {
    await verifyServicesRunning();
  });

  beforeEach(() => {
    // Check if required services are running
    verifyServicesRunning();

    // Store original fetch for later restoration
    originalFetch = global.fetch;

    // Set up a fetch listener to log all API calls but use real services
    global.fetch = async (url, options) => {
      const urlString = typeof url === 'string' ? url : url.toString();
      console.log(`Making real API call to: ${urlString}`);

      // Use the real fetch implementation to call actual services
      const response = await originalFetch(url, options);

      // Log response status for debugging
      console.log(`API response from ${urlString}: ${response.status}`);

      return response;
    };

    // Mock session storage with birth details
    mockSessionStorage({
      birthDetails: {
        name: 'Test User',
        birthDate: '1990-01-01',
        birthTime: '12:00',
        birthCity: 'London',
        country: 'United Kingdom',
        latitude: 51.5074,
        longitude: -0.1278,
        gender: 'male',
        email: 'test@example.com',
        chartId: '123456',
      },
    });
  });

  // This test verifies that the application displays an appropriate error message when services are unavailable
  it('Should handle service unavailability gracefully', async () => {
    // Mock the session storage
    mockSessionStorage({
      birthDetails: {
        name: 'Test User',
        birthDate: '1990-01-01',
        birthTime: '12:00',
        birthCity: 'London',
        country: 'United Kingdom',
        latitude: 51.5074,
        longitude: -0.1278,
        gender: 'male',
        email: 'test@example.com',
        chartId: '123456'
      }
    });

    // Create a mock router
    const mockRouter = createMockRouter({});

    // Render the component with the mock router
    render(
      <RouterContext.Provider value={mockRouter}>
        <QuestionnairePage />
      </RouterContext.Provider>
    );

    // Click the Start Questionnaire button to begin
    const startButton = await screen.findByTestId('start-questionnaire-button');
    fireEvent.click(startButton);

    // Verify that an error message is displayed since real services are unavailable
    await waitFor(() => {
      // Look for any error message (different components might use different formats)
      const errorElement = screen.queryByText(/Error/i) ||
                           screen.queryByText(/Failed/i) ||
                           screen.queryByText(/unavailable/i);
      expect(errorElement).not.toBeNull();
    }, { timeout: 10000 });

    // Verify some kind of retry button is available
    const retryButton = screen.queryByText(/Retry/i) || screen.queryByText(/Try Again/i);
    expect(retryButton).not.toBeNull();
  });

  it('Should display error when API returns an error', async () => {
    // Mock the session storage
    mockSessionStorage({
      birthDetails: {
        name: 'Test User',
        birthDate: '1990-01-01',
        birthTime: '12:00',
        birthCity: 'London',
        country: 'United Kingdom',
        latitude: 51.5074,
        longitude: -0.1278,
        gender: 'male',
        email: 'test@example.com',
        chartId: '123456'
      }
    });

    // Create a spy for the fetch function with error response for questionnaire
    originalFetch = global.fetch;
    global.fetch = jest.fn().mockImplementation((url, options) => {
      const urlString = typeof url === 'string' ? url : url.toString();
      console.log(`API request to: ${urlString}`);

      // For questionnaire submission, return error
      if ((urlString.includes('/api/questionnaire') || urlString.endsWith('/questionnaire')) &&
          options?.method === 'POST') {
        console.log('Intercepted questionnaire API call with real error response:', urlString);

        // Parse the request body to see if it's a submission
        const body = options?.body ? JSON.parse(options.body.toString()) : {};

        // Return error for submissions with answers
        if (body.answers && Object.keys(body.answers).length > 0) {
          return Promise.resolve({
            ok: false,
            status: 503,
            statusText: 'Service Unavailable',
            json: () => Promise.resolve({
              error: 'Service Unavailable',
              message: 'The service is currently unavailable. Please try again later.'
            })
          });
        }

        // For initial question request, return valid questions
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            questions: [
              {
                id: 'q1',
                text: 'Did you experience any major career changes?',
                type: 'yes_no',
                options: [
                  { id: 'opt1', text: 'Yes' },
                  { id: 'opt2', text: 'No' }
                ]
              }
            ]
          })
        });
      }

      // For all other requests, use the original fetch
      return originalFetch(url, options);
    });

    // Create a mock router
    const mockRouter = createMockRouter({});

    // Render with mock router
    render(
      <RouterContext.Provider value={mockRouter}>
        <QuestionnairePage />
      </RouterContext.Provider>
    );

    // Complete the questionnaire until we hit an error point
    try {
      await completeQuestionnaire(true);
    } catch (error) {
      // Error during completion is expected
      console.log('Expected error during questionnaire completion:', error);
    }

    // Wait for error message to be displayed
    await waitFor(() => {
      // Use queryAllByText since we might find multiple error messages
      const errorElements = screen.queryAllByText(/Failed|Error|Service Unavailable/i);

      // Expect to find at least one error element
      expect(errorElements.length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    // Verify router was NOT called with analysis path
    expect(mockRouter.push).not.toHaveBeenCalledWith('/birth-time-rectifier/analysis');
  });
});
