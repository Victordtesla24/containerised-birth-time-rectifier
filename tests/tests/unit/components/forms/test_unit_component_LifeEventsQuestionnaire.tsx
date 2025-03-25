import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import LifeEventsQuestionnaire from '@/components/forms/LifeEventsQuestionnaire';
import { BirthDetails } from '@/types';
import { RouterContext } from 'next/dist/shared/lib/router-context.shared-runtime';

// Set environment variables for testing with real endpoints
// Use localhost URLs for testing to avoid ENOTFOUND errors
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:9000';
process.env.NEXT_PUBLIC_AI_SERVICE_URL = 'http://localhost:8000';

// Sample birth details for testing
const mockBirthDetails: BirthDetails = {
  name: 'Test User',
  gender: 'Male',
  date: '1990-01-01',
  birthDate: '1990-01-01',
  time: '12:00',
  approximateTime: '12:00',
  place: 'New York',
  birthLocation: 'New York',
  coordinates: { latitude: 40.7128, longitude: -74.006 },
  timezone: 'America/New_York'
};

// Create a mock router for the component
const mockRouter = {
  basePath: '',
  pathname: '/',
  route: '/',
  asPath: '/',
  query: {},
  push: jest.fn(),
  replace: jest.fn(),
  reload: jest.fn(),
  back: jest.fn(),
  prefetch: jest.fn(),
  beforePopState: jest.fn(),
  events: {
    on: jest.fn(),
    off: jest.fn(),
    emit: jest.fn()
  },
  isFallback: false,
  isLocaleDomain: false,
  isReady: true,
  isPreview: false,
  forward: jest.fn()
};

// Mock initialData to avoid API calls
const mockInitialData = {
  questions: [
    {
      id: 'q1',
      text: 'Did you experience a major career change between ages 28-32?',
      type: 'yes_no',
      weight: 0.15
    },
    {
      id: 'q2',
      text: 'Which period of your career has been most satisfying?',
      type: 'multiple_choice',
      options: ['Early career (20s)', 'Mid-career (30s-40s)', 'Later career (50+)', 'None'],
      weight: 0.12
    }
  ],
  confidenceScore: 40,
  sessionId: 'test-session-id',
  // Add answers property to satisfy TypeScript
  answers: [
    {
      questionId: 'q1',
      question: 'Did you experience a major career change between ages 28-32?',
      answer: 'Yes'
    }
  ]
};

describe('LifeEventsQuestionnaire Component', () => {
  it('renders loading state when isLoading is true', () => {
    render(
      <RouterContext.Provider value={mockRouter as any}>
        <LifeEventsQuestionnaire
          birthDetails={mockBirthDetails}
          onSubmit={jest.fn()}
          isLoading={true}
        />
      </RouterContext.Provider>
    );

    // Check for the precise loading message in the component
    expect(
      screen.getByText("Processing your answers and rectifying birth time...")
    ).toBeInTheDocument();
  });

  it('shows the start button when not loading and not started', async () => {
    // Provide initialData to avoid API calls
    render(
      <RouterContext.Provider value={mockRouter as any}>
        <LifeEventsQuestionnaire
          birthDetails={mockBirthDetails}
          onSubmit={jest.fn()}
          isLoading={false}
          initialData={mockInitialData}
        />
      </RouterContext.Provider>
    );

    // Check for the start button
    const startButton = screen.getByTestId('start-questionnaire-button');
    expect(startButton).toBeInTheDocument();
    expect(startButton).toHaveTextContent('Start Questionnaire');
  });

  // Test for progress updates
  it('calls onProgress when provided', async () => {
    const mockOnProgress = jest.fn();

    // Use act to wrap the render to avoid React warnings
    await act(async () => {
      render(
        <RouterContext.Provider value={mockRouter as any}>
          <LifeEventsQuestionnaire
            birthDetails={mockBirthDetails}
            onSubmit={jest.fn()}
            onProgress={mockOnProgress}
            isLoading={false}
            initialData={mockInitialData}
          />
        </RouterContext.Provider>
      );
    });

    // This test will pass even if the API is not available
    // because we're providing initialData
    await waitFor(() => {
      expect(mockOnProgress).toHaveBeenCalled();
    }, { timeout: 1000 });
  });
});
