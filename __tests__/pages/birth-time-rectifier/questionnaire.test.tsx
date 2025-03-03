import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionnairePage from '@/pages/birth-time-rectifier/questionnaire';

// Mock the router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    query: {}
  }),
}));

// Mock the components
jest.mock('@/components/visualization/CelestialBackground', () => ({
  CelestialBackground: () => <div data-testid="celestial-background" />
}));

jest.mock('@/components/forms/LifeEventsQuestionnaire', () => {
  return {
    __esModule: true,
    default: ({ birthDetails, onSubmit, isLoading }: any) => (
      <div data-testid="questionnaire-component">
        <button 
          data-testid="submit-button"
          onClick={() => onSubmit({ 
            confidenceScore: 92,
            answers: [{ questionId: 'test', question: 'test?', answer: 'Yes' }]
          })}
        >
          Submit Questionnaire
        </button>
        <div data-testid="loading-state">{isLoading ? 'Loading' : 'Not Loading'}</div>
      </div>
    )
  };
});

// Mock sessionStorage
const mockSessionStorage: Record<string, string> = {};

Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: jest.fn((key: string) => mockSessionStorage[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      mockSessionStorage[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete mockSessionStorage[key];
    }),
    clear: jest.fn(() => {
      Object.keys(mockSessionStorage).forEach(key => {
        delete mockSessionStorage[key];
      });
    }),
  },
  writable: true
});

// Mock fetch
global.fetch = jest.fn();

describe('QuestionnairePage', () => {
  const mockRouter = { push: jest.fn() };
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset session storage mock
    Object.keys(mockSessionStorage).forEach(key => {
      delete mockSessionStorage[key];
    });
    
    // Set mock birth details in session storage
    const mockBirthDetails = {
      name: 'Test User',
      date: '1990-01-01',
      time: '12:00',
      place: 'New York',
      coordinates: { latitude: 40.7128, longitude: -74.006 },
      timezone: 'America/New_York'
    };
    
    mockSessionStorage['birthDetails'] = JSON.stringify(mockBirthDetails);
    
    // Mock router
    jest.spyOn(require('next/router'), 'useRouter').mockReturnValue(mockRouter);
  });

  it('redirects if birth details are not found', async () => {
    // Clear session storage
    Object.keys(mockSessionStorage).forEach(key => {
      delete mockSessionStorage[key];
    });
    
    render(<QuestionnairePage />);
    
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('/birth-time-rectifier');
    });
  });

  it('renders the questionnaire component when birth details are available', async () => {
    render(<QuestionnairePage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('questionnaire-component')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Life Events Questionnaire')).toBeInTheDocument();
  });

  it('processes questionnaire submission with sufficient confidence', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ 
        confidenceScore: 95,
        meetsThreshold: true
      }),
    });

    render(<QuestionnairePage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('questionnaire-component')).toBeInTheDocument();
    });
    
    // Click the submit button in the mocked questionnaire component
    fireEvent.click(screen.getByTestId('submit-button'));
    
    // Should show processing state
    await waitFor(() => {
      expect(screen.getByText('Finalizing Your Birth Time Analysis')).toBeInTheDocument();
    });
    
    // Should call the API
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/questionnaire'),
      expect.any(Object)
    );
    
    // Should redirect to analysis page after successful submission
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('/birth-time-rectifier/analysis');
      expect(mockSessionStorage['rectificationResult']).toBeDefined();
    });
  });

  it('shows error when confidence is not sufficient', async () => {
    render(<QuestionnairePage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('questionnaire-component')).toBeInTheDocument();
    });
    
    // Override the mock to return low confidence
    const lowConfidenceData = { 
      confidenceScore: 60,
      answers: [{ questionId: 'test', question: 'test?', answer: 'Yes' }]
    };
    
    // Submit with low confidence
    const onSubmit = (require('@/components/forms/LifeEventsQuestionnaire').default as any).mock.calls[0][0].onSubmit;
    onSubmit(lowConfidenceData);
    
    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/confidence score .* is below the required threshold/i)).toBeInTheDocument();
    });
    
    // Should not redirect
    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    // Mock failed API response
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API error'));

    render(<QuestionnairePage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('questionnaire-component')).toBeInTheDocument();
    });
    
    // Click the submit button in the mocked questionnaire component
    fireEvent.click(screen.getByTestId('submit-button'));
    
    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  it('uses fallback mock data when API fails but confidence is high', async () => {
    // Mock failed API response
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API error'));

    render(<QuestionnairePage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('questionnaire-component')).toBeInTheDocument();
    });
    
    // Click the submit button in the mocked questionnaire component
    fireEvent.click(screen.getByTestId('submit-button'));
    
    // Should redirect to analysis page with mock data
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('/birth-time-rectifier/analysis');
      expect(mockSessionStorage['rectificationResult']).toBeDefined();
    });
    
    // Parse the mock result to verify it has the right structure
    const mockResult = JSON.parse(mockSessionStorage['rectificationResult']);
    expect(mockResult.suggestedTime).toBeDefined();
    expect(mockResult.confidence).toBeGreaterThanOrEqual(90);
  });
}); 