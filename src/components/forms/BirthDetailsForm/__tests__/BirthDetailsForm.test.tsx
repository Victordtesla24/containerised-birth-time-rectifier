import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import BirthDetailsForm from '../index';
import { geocodeBirthPlace } from '../../../../services/geocoding';

// Mock the geocoding service
jest.mock('../../../../services/geocoding', () => ({
  geocodeBirthPlace: jest.fn().mockResolvedValue({
    latitude: 51.5074,
    longitude: -0.1278,
    timezone: 'Europe/London'
  })
}));

describe('BirthDetailsForm', () => {
  const defaultProps = {
    onSubmit: jest.fn(),
    onValidation: jest.fn(),
    initialData: {},
    isLoading: false
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders form elements correctly', () => {
    render(<BirthDetailsForm {...defaultProps} />);
    
    // Check for the presence of form elements
    expect(screen.getByLabelText(/Birth Date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Birth Time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Birth Place/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();
  });

  test('shows validation errors when submitting empty form', async () => {
    render(<BirthDetailsForm {...defaultProps} />);
    
    // Get all input fields
    const dateInput = screen.getByLabelText(/Birth Date/i);
    const timeInput = screen.getByLabelText(/Birth Time/i);
    const placeInput = screen.getByLabelText(/Birth Place/i);
    
    // Focus and blur each field to trigger touched state
    await act(async () => {
      fireEvent.focus(dateInput);
      fireEvent.blur(dateInput);
      
      fireEvent.focus(timeInput);
      fireEvent.blur(timeInput);
      
      fireEvent.focus(placeInput);
      fireEvent.blur(placeInput);
    });
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /Next/i });
    
    await act(async () => {
      fireEvent.click(submitButton);
    });
    
    // Now check for error messages that should appear based on the form's error handling logic
    await waitFor(() => {
      expect(screen.getByText(/Birth date is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Birth time is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Birth place is required/i)).toBeInTheDocument();
    });
  });

  test('submit button is disabled when loading', () => {
    render(<BirthDetailsForm {...defaultProps} isLoading={true} />);
    
    const submitButton = screen.getByRole('button', { name: /Processing/i });
    expect(submitButton).toBeDisabled();
    expect(submitButton).toHaveClass('bg-gray-400');
  });

  test('calls onSubmit when form is valid and submitted', async () => {
    // Setup geocoding mock to be resolved after a delay
    (geocodeBirthPlace as jest.Mock).mockImplementation(
      (place) => new Promise(resolve => 
        setTimeout(() => resolve({
          latitude: 51.5074,
          longitude: -0.1278,
          timezone: 'Europe/London'
        }), 50)
      )
    );
    
    render(<BirthDetailsForm {...defaultProps} />);
    
    // Fill out the form
    const dateInput = screen.getByLabelText(/Birth Date/i);
    const timeInput = screen.getByLabelText(/Birth Time/i);
    const placeInput = screen.getByLabelText(/Birth Place/i);
    
    await act(async () => {
      fireEvent.change(dateInput, { target: { value: '2000-01-01' } });
      fireEvent.change(timeInput, { target: { value: '12:00' } });
      fireEvent.change(placeInput, { target: { value: 'London, UK' } });
      // Need to trigger blur to start geocoding
      fireEvent.blur(placeInput);
    });
    
    // Wait for geocoding to be called
    await waitFor(() => {
      expect(geocodeBirthPlace).toHaveBeenCalledWith('London, UK');
    });
    
    // Wait for geocoding to complete
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /Next/i });
    
    await act(async () => {
      fireEvent.click(submitButton);
    });
    
    // Check if onSubmit was called with the right data
    await waitFor(() => {
      expect(defaultProps.onSubmit).toHaveBeenCalledWith(expect.objectContaining({
        date: '2000-01-01',
        time: '12:00',
        place: 'London, UK',
        coordinates: expect.objectContaining({
          latitude: 51.5074,
          longitude: -0.1278
        }),
        timezone: 'Europe/London'
      }));
    });
  });
});
