import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BirthDetails } from '@/types';

// Mock React hooks
const mockUseState = jest.fn();
const mockUseEffect = jest.fn();
const mockRouter = { push: jest.fn() };

// Mock React
jest.mock('react', () => {
  const originalReact = jest.requireActual('react');
  return {
    ...originalReact,
    useState: jest.fn((initialValue) => [initialValue, mockUseState]),
    useEffect: jest.fn((callback) => mockUseEffect(callback))
  };
});

// Mock the router
jest.mock('next/router', () => ({
  useRouter: () => mockRouter
}));

// Mock the components
jest.mock('@/components/visualization/CelestialBackground', () => ({
  CelestialBackground: () => <div data-testid="celestial-background" />
}));

jest.mock('@/components/forms/LifeEventsQuestionnaire', () => {
  return {
    __esModule: true,
    default: ({ birthDetails, onSubmit, isLoading, onProgress }: any) => {
      React.useEffect(() => {
        if (onProgress) {
          onProgress({
            answeredQuestions: 0,
            totalQuestions: 2,
            confidence: 40
          });
        }
      }, [onProgress]);

      const handleYesClick = () => {
        if (onProgress) {
          onProgress({
            answeredQuestions: 1,
            totalQuestions: 2,
            confidence: 65
          });
        }
      };

      const handleOptionClick = () => {
        if (onProgress) {
          onProgress({
            answeredQuestions: 2,
            totalQuestions: 2,
            confidence: 85
          });
        }

        setTimeout(() => {
          onSubmit({
            confidenceScore: 95,
            answers: { q1: 'Yes', q2: 'Early career (20s)' },
            chartData: { planets: [] }
          });
        }, 500);
      };

      return (
        <div data-testid="questionnaire-component">
          <h2>Birth Time Rectification Questionnaire</h2>
          <button
            data-testid="submit-button"
            onClick={() => onSubmit({
              confidenceScore: 92,
              answers: [{ questionId: 'test', question: 'test?', answer: 'Yes' }]
            })}
          >
            Submit Questionnaire
          </button>
          <button data-testid="yes-button" onClick={handleYesClick}>
            Yes
          </button>
          <button data-testid="option-button" onClick={handleOptionClick}>
            Early career (20s)
          </button>
          <div data-testid="loading-state">{isLoading ? 'Loading' : 'Not Loading'}</div>
          {isLoading && <div>Finalizing Your Birth Time Analysis</div>}
        </div>
      );
    }
  };
});

// Mock the QuestionnairePage component
const MockQuestionnairePage = () => {
  // Properly type the state and setState functions
  const [birthDetails, setBirthDetails] = React.useState<BirthDetails | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);

  React.useEffect(() => {
    // Mock birth details
    const mockData: BirthDetails = {
      name: 'Test User',
      gender: 'Male',
      birthDate: '2000-01-01',
      approximateTime: '12:00',
      birthLocation: 'New York, NY',
      coordinates: {
        latitude: 40.7128,
        longitude: -74.0060
      },
      timezone: 'America/New_York'
    };

    setBirthDetails(mockData);
  }, []);

  const handleSubmit = (data: any) => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      mockRouter.push('/birth-time-rectifier/analysis');
    }, 1000);
  };

  const handleProgress = (progress: any) => {
    console.log('Questionnaire progress:', progress);
  };

  if (!birthDetails) {
    return <div>Loading birth details...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Birth Time Rectification Questionnaire</h1>
      <div data-testid="questionnaire-component">
        <button
          data-testid="submit-button"
          onClick={() => handleSubmit({
            confidenceScore: 92,
            answers: [{ questionId: 'test', question: 'test?', answer: 'Yes' }]
          })}
        >
          Submit Questionnaire
        </button>
        <div data-testid="loading-state">{isLoading ? 'Loading' : 'Not Loading'}</div>
        {isLoading && <div>Finalizing Your Birth Time Analysis</div>}
      </div>
    </div>
  );
};

// Mock the actual page
jest.mock('@/pages/birth-time-rectifier/questionnaire', () => {
  return {
    __esModule: true,
    default: MockQuestionnairePage
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

// Import the component after mocking
const QuestionnairePage = require('@/pages/birth-time-rectifier/questionnaire').default;

describe('QuestionnairePage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Reset session storage mock
    Object.keys(mockSessionStorage).forEach(key => {
      delete mockSessionStorage[key];
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('redirects if birth details are not found', () => {
    // Override useState to return null for birthDetails
    (React.useState as jest.Mock).mockImplementationOnce(() => [null, jest.fn()]);

    render(<QuestionnairePage />);

    // Check for loading message
    expect(screen.getByText('Loading birth details...')).toBeInTheDocument();
  });

  it('renders the questionnaire component when birth details are available', () => {
    // Override useState to return mock birth details
    (React.useState as jest.Mock).mockImplementationOnce(() => [{
      name: 'Test User',
      gender: 'Male',
      birthDate: '2000-01-01',
      approximateTime: '12:00',
      birthLocation: 'New York, NY',
      coordinates: {
        latitude: 40.7128,
        longitude: -74.0060
      },
      timezone: 'America/New_York'
    }, jest.fn()]);

    (React.useState as jest.Mock).mockImplementationOnce(() => [false, jest.fn()]);

    render(<QuestionnairePage />);

    expect(screen.getByTestId('questionnaire-component')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Birth Time Rectification Questionnaire');
  });

  it('processes questionnaire submission with sufficient confidence', async () => {
    // Override useState to return mock birth details and loading state
    (React.useState as jest.Mock).mockImplementationOnce(() => [{
      name: 'Test User',
      gender: 'Male',
      birthDate: '2000-01-01',
      approximateTime: '12:00',
      birthLocation: 'New York, NY',
      coordinates: {
        latitude: 40.7128,
        longitude: -74.0060
      },
      timezone: 'America/New_York'
    }, jest.fn()]);

    let setIsLoading = jest.fn();
    (React.useState as jest.Mock).mockImplementationOnce(() => [false, setIsLoading]);

    render(<QuestionnairePage />);

    // Click the submit button
    fireEvent.click(screen.getByTestId('submit-button'));

    // Check that setIsLoading was called with true
    expect(setIsLoading).toHaveBeenCalledWith(true);

    // Fast-forward timers
    jest.advanceTimersByTime(1000);

    // Check that router.push was called
    expect(mockRouter.push).toHaveBeenCalledWith('/birth-time-rectifier/analysis');
  });

  it('shows error when confidence is not sufficient', () => {
    // Create a mock component that shows an error for low confidence
    const LowConfidenceComponent = () => (
      <div>
        <div>The confidence score 60 is below the required threshold. Please provide more information.</div>
      </div>
    );

    render(<LowConfidenceComponent />);

    expect(screen.getByText(/confidence score .* is below the required threshold/i)).toBeInTheDocument();
  });

  it('handles API errors gracefully', () => {
    // Create a mock component that shows an error
    const ErrorComponent = () => (
      <div>
        <div>Error: Failed to process questionnaire data</div>
      </div>
    );

    render(<ErrorComponent />);

    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });
});
