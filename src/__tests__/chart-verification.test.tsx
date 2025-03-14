import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChartVerification from '../components/charts/ChartVerification';

describe('ChartVerification Component', () => {
  test('renders verified status correctly', () => {
    const verification = {
      status: 'verified',
      confidence: 95,
      corrections_applied: false,
      corrections: [],
      message: 'Chart verified successfully against Vedic standards.'
    };

    render(<ChartVerification verification={verification} />);

    expect(screen.getByText('Chart Verification')).toBeInTheDocument();
    expect(screen.getByText('Verified')).toBeInTheDocument();
    expect(screen.getByText(/95/)).toBeInTheDocument();
    expect(screen.getByText('Chart verified successfully against Vedic standards.')).toBeInTheDocument();
  });

  test('renders errors_found status correctly', () => {
    const verification = {
      status: 'errors_found',
      confidence: 75,
      corrections_applied: true,
      corrections: [
        {
          field: 'Mars position',
          original: 'Aries 15.5°',
          corrected: 'Aries 16.2°',
          explanation: 'Calculation error in Mars position'
        }
      ],
      message: 'Minor corrections applied to chart calculations.'
    };

    render(<ChartVerification verification={verification} />);

    expect(screen.getByText('Chart Verification')).toBeInTheDocument();
    expect(screen.getByText('Errors Found')).toBeInTheDocument();
    expect(screen.getByText(/75/)).toBeInTheDocument();
    expect(screen.getByText('Minor corrections applied to chart calculations.')).toBeInTheDocument();
    expect(screen.getByText('Calculation error in Mars position')).toBeInTheDocument();
    expect(screen.getByText('Aries 15.5°')).toBeInTheDocument();
    expect(screen.getByText('Aries 16.2°')).toBeInTheDocument();
  });

  test('renders verification_error status correctly', () => {
    const verification = {
      status: 'verification_error',
      confidence: 0,
      corrections_applied: false,
      corrections: [],
      message: 'Unable to verify chart due to API error.'
    };

    render(<ChartVerification verification={verification} />);

    expect(screen.getByText('Chart Verification')).toBeInTheDocument();
    expect(screen.getByText('Verification Error')).toBeInTheDocument();
    expect(screen.getByText(/0/)).toBeInTheDocument();
    expect(screen.getByText('Unable to verify chart due to API error.')).toBeInTheDocument();
  });

  test('renders not_verified status correctly', () => {
    const verification = {
      status: 'not_verified',
      confidence: 0,
      corrections_applied: false,
      corrections: [],
      message: 'Chart was not verified with OpenAI.'
    };

    render(<ChartVerification verification={verification} />);

    expect(screen.getByText('Chart Verification')).toBeInTheDocument();
    expect(screen.getByText('Not Verified')).toBeInTheDocument();
    expect(screen.getByText(/0/)).toBeInTheDocument();
    expect(screen.getByText('Chart was not verified with OpenAI.')).toBeInTheDocument();
  });

  test('handles missing verification data gracefully', () => {
    const verification = {
      status: 'verified',
      confidence: 0,
      corrections_applied: false,
      corrections: [],
      message: ''
    };

    render(<ChartVerification verification={verification} />);

    expect(screen.getByText('Chart Verification')).toBeInTheDocument();
    expect(screen.getByText('Verified')).toBeInTheDocument();
    expect(screen.getByText(/0/)).toBeInTheDocument();
  });
});
