import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LifeEventsQuestionnaire from '@/components/forms/LifeEventsQuestionnaire';
import { BirthDetails } from '@/types';

// Mock fetch for API calls
global.fetch = jest.fn();

// Sample birth details for testing
const mockBirthDetails: BirthDetails = {
  name: 'Test User',
  date: '1990-01-01',
  time: '12:00',
  place: 'New York',
  coordinates: { latitude: 40.7128, longitude: -74.006 },
  timezone: 'America/New_York'
};

// Sample questions for testing
const mockQuestions = [
  {
    id: 'q1',
    text: 'Did you experience a major career change between ages 28-32?',
    type: 'yes_no' as const,
    weight: 0.15
  },
  {
    id: 'q2',
    text: 'Which period of your career has been most satisfying?',
    type: 'multiple_choice' as const,
    options: ['Early career (20s)', 'Mid-career (30s-40s)', 'Later career (50+)', 'None'],
    weight: 0.12
  }
];

describe('LifeEventsQuestionnaire Component', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    
    // Mock initial chart fetch
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ chartData: { /* mock chart data */ } }),
    });
    
    // Mock question fetch
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        questions: mockQuestions,
        confidenceScore: 0,
        isComplete: false,
        hasReachedThreshold: false
      }),
    });
  });

  it('renders loading state initially', async () => {
    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={jest.fn()} 
        isLoading={false} 
      />
    );

    expect(screen.getByText(/preparing your personalized questionnaire/i)).toBeInTheDocument();
  });

  it('shows the first question when loaded', async () => {
    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={jest.fn()} 
        isLoading={false} 
      />
    );

    await waitFor(() => {
      expect(screen.getByText(mockQuestions[0].text)).toBeInTheDocument();
    });

    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });

  it('handles yes/no questions correctly', async () => {
    // Mock answer processing
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        confidenceScore: 15,
        meetsThreshold: false,
        requestMoreQuestions: true
      }),
    });

    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={jest.fn()} 
        isLoading={false} 
      />
    );

    await waitFor(() => {
      expect(screen.getByText(mockQuestions[0].text)).toBeInTheDocument();
    });

    // Click the Yes button
    fireEvent.click(screen.getByText('Yes'));

    // Should process the answer and move to next question
    await waitFor(() => {
      expect(screen.getByText(mockQuestions[1].text)).toBeInTheDocument();
    });

    // The answer should have been sent to the API
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/questionnaire'),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('Yes')
      })
    );
  });

  it('handles multiple choice questions correctly', async () => {
    // Mock answer processing
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        confidenceScore: 30,
        meetsThreshold: false,
        requestMoreQuestions: true
      }),
    });

    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={jest.fn()} 
        isLoading={false} 
      />
    );

    // Wait for the first question and answer it
    await waitFor(() => {
      expect(screen.getByText(mockQuestions[0].text)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Yes'));

    // Wait for the second question (multiple choice)
    await waitFor(() => {
      expect(screen.getByText(mockQuestions[1].text)).toBeInTheDocument();
    });

    // Click one of the multiple choice options
    fireEvent.click(screen.getByText('Early career (20s)'));

    // The answer should have been sent to the API
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/questionnaire'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('Early career (20s)')
        })
      );
    });
  });

  it('updates the progress bar as confidence increases', async () => {
    // Set up fetch mock to return increasing confidence scores
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({ // Initial chart
        ok: true,
        json: async () => ({ chartData: { /* mock chart data */ } }),
      })
      .mockResolvedValueOnce({ // Initial questions
        ok: true,
        json: async () => ({
          questions: mockQuestions,
          confidenceScore: 0,
          isComplete: false,
          hasReachedThreshold: false
        }),
      })
      .mockResolvedValueOnce({ // First answer
        ok: true,
        json: async () => ({
          confidenceScore: 40,
          meetsThreshold: false,
          requestMoreQuestions: true
        }),
      })
      .mockResolvedValueOnce({ // Second answer
        ok: true,
        json: async () => ({
          confidenceScore: 85,
          meetsThreshold: false,
          requestMoreQuestions: true
        }),
      });

    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={jest.fn()} 
        isLoading={false} 
      />
    );

    // Wait for questions to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestions[0].text)).toBeInTheDocument();
    });

    // Answer the first question
    fireEvent.click(screen.getByText('Yes'));

    // Check that the progress has updated
    await waitFor(() => {
      expect(screen.getByText('40%')).toBeInTheDocument();
    });

    // Move to the second question and answer
    await waitFor(() => {
      expect(screen.getByText(mockQuestions[1].text)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Early career (20s)'));

    // Check that the progress has updated again
    await waitFor(() => {
      expect(screen.getByText('85%')).toBeInTheDocument();
    });
  });

  it('calls onSubmit when confidence threshold is reached', async () => {
    const mockOnSubmit = jest.fn();
    const CONFIDENCE_THRESHOLD = 90;

    // Set up fetch mock to reach threshold
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({ // Initial chart
        ok: true,
        json: async () => ({ chartData: { /* mock chart data */ } }),
      })
      .mockResolvedValueOnce({ // Initial questions
        ok: true,
        json: async () => ({
          questions: mockQuestions,
          confidenceScore: 85,
          isComplete: false,
          hasReachedThreshold: false
        }),
      })
      .mockResolvedValueOnce({ // First answer reaches threshold
        ok: true,
        json: async () => ({
          confidenceScore: CONFIDENCE_THRESHOLD,
          meetsThreshold: true,
          requestMoreQuestions: false
        }),
      });

    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={mockOnSubmit} 
        isLoading={false} 
      />
    );

    // Wait for questions to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestions[0].text)).toBeInTheDocument();
    });

    // Answer the first question which should reach threshold
    fireEvent.click(screen.getByText('Yes'));

    // Check that onSubmit was called
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
    
    // Check the argument contains the right confidence score
    expect(mockOnSubmit.mock.calls[0][0].confidenceScore).toBeGreaterThanOrEqual(CONFIDENCE_THRESHOLD);
  });

  it('shows error state when API fails', async () => {
    // Mock failed API calls
    (global.fetch as jest.Mock)
      .mockRejectedValueOnce(new Error('Failed to fetch initial chart'))
      .mockRejectedValueOnce(new Error('Failed to fetch questions'));

    render(
      <LifeEventsQuestionnaire 
        birthDetails={mockBirthDetails} 
        onSubmit={jest.fn()} 
        isLoading={false} 
      />
    );

    // Wait for error to appear (need to wait longer as it appears after multiple retries)
    await waitFor(() => {
      expect(screen.getByText(/error loading questions/i)).toBeInTheDocument();
    }, { timeout: 3000 });

    // Check for retry button
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });
}); 