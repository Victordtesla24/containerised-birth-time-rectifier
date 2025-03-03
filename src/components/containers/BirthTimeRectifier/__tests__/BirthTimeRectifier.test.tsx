import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BirthTimeRectifier from '../index';

// Mock the required components
jest.mock('@/components/forms/BirthDetailsForm', () => {
  return {
    __esModule: true,
    default: function MockBirthDetailsForm(props: any) {
      const { onSubmit, isLoading, onValidation } = props;
      
      // Call onValidation to indicate form is valid
      React.useEffect(() => {
        if (onValidation) onValidation(true);
      }, [onValidation]);
      
      const testData = {
        date: '2000-01-01',
        time: '12:00',
        place: 'London, UK',
        coordinates: {
          latitude: 51.5074,
          longitude: -0.1278
        },
        timezone: 'Europe/London'
      };
      
      return (
        <div data-testid="birth-details-form">
          <button 
            data-testid="form-submit-button" 
            onClick={() => onSubmit(testData)}
            disabled={isLoading}
          >
            {isLoading ? 'Processing...' : 'Next'}
          </button>
        </div>
      );
    }
  };
});

jest.mock('@/components/charts/BirthChart', () => {
  return {
    __esModule: true,
    default: function MockBirthChart() {
      return (
        <div data-testid="birth-chart">
          <div data-testid="sun">Sun</div>
          <div data-testid="moon">Moon</div>
        </div>
      );
    }
  };
});

// Mock DockerAIService - simple mock that doesn't try to track calls
jest.mock('@/services/docker/DockerAIService', () => ({
  DockerAIService: {
    getInstance: () => ({
      calculateBirthTime: () => Promise.resolve({
        rectifiedTime: '14:30',
        confidence: 0.85,
        explanation: 'Test explanation'
      })
    })
  }
}));

describe('BirthTimeRectifier', () => {
  const defaultProps = {
    onSubmit: jest.fn().mockResolvedValue(undefined),
    onBirthTimeCalculated: jest.fn(),
    onError: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the form initially', () => {
    render(<BirthTimeRectifier {...defaultProps} />);
    
    expect(screen.getByTestId('birth-details-form')).toBeInTheDocument();
    expect(screen.getByTestId('form-submit-button')).toBeInTheDocument();
    expect(screen.queryByTestId('birth-chart')).not.toBeInTheDocument();
  });

  it('disables the form submit button when loading', () => {
    render(<BirthTimeRectifier {...defaultProps} isLoading={true} />);
    
    const submitButton = screen.getByTestId('form-submit-button');
    expect(submitButton).toBeDisabled();
    expect(submitButton).toHaveTextContent('Processing...');
  });
  
  it('calls parent onSubmit when form is submitted', () => {
    render(<BirthTimeRectifier {...defaultProps} />);
    
    // Submit the form
    fireEvent.click(screen.getByTestId('form-submit-button'));
    
    // Check that parent onSubmit was called
    expect(defaultProps.onSubmit).toHaveBeenCalled();
  });
}); 