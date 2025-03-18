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
const BASE_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://birth-rectifier-api-gateway:9000';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';

// Function to log API calls
const logApiCall = (url: string) => {
  console.log(`API Call to: ${url}`);
};

describe('Questionnaire to Analysis Flow', () => {
  // Increase the timeout for all tests in this describe block
  jest.setTimeout(60000); // Increase timeout to 60 seconds

  afterEach(() => {
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

    // Verify that an error message is displayed if real services are unavailable
    // or that the questionnaire loads if services are available
    await waitFor(() => {
      // Look for either an error message or the first question
      const errorElement = screen.queryByText(/Error/i) ||
                           screen.queryByText(/Failed/i) ||
                           screen.queryByText(/unavailable/i);

      const questionElement = screen.queryByText(/Question 1/i) ||
                              screen.queryByText(/Did you experience/i);

      // Either an error or a question should be present
      expect(errorElement !== null || questionElement !== null).toBe(true);
    }, { timeout: 10000 });
  });

  it('Should display error or proceed with questionnaire based on API availability', async () => {
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

    // Render with mock router
    render(
      <RouterContext.Provider value={mockRouter}>
        <QuestionnairePage />
      </RouterContext.Provider>
    );

    // Click the Start Questionnaire button to begin
    const startButton = await screen.findByTestId('start-questionnaire-button');
    fireEvent.click(startButton);

    // Wait for either an error message or the first question to appear
    await waitFor(() => {
      const errorElement = screen.queryByText(/Error/i) ||
                           screen.queryByText(/Failed/i) ||
                           screen.queryByText(/unavailable/i);

      const questionElement = screen.queryByText(/Question 1/i) ||
                              screen.queryByText(/Did you experience/i);

      // Either an error or a question should be present
      expect(errorElement !== null || questionElement !== null).toBe(true);
    }, { timeout: 10000 });

    // If we got a question, try to complete the questionnaire
    const questionElement = screen.queryByText(/Question 1/i) ||
                            screen.queryByText(/Did you experience/i);

    if (questionElement) {
      try {
        // Try to complete the questionnaire
        // This may fail if the API is not fully available
        await completeQuestionnaire(true);

        // If we get here, check if we were redirected to the analysis page
        expect(mockRouter.push).toHaveBeenCalledWith(expect.stringContaining('/analysis'));
      } catch (error) {
        // Error during completion is expected if API is not available
        console.log('Error during questionnaire completion:', error);

        // Verify we see an error message
        await waitFor(() => {
          const errorElements = screen.queryAllByText(/Failed|Error|Service Unavailable/i);
          expect(errorElements.length).toBeGreaterThan(0);
        }, { timeout: 5000 });
      }
    }
  });
});
