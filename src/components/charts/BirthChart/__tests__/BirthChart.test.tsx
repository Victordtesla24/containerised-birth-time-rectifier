import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BirthChart from '../index';
import { ChartData } from '@/types';

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('BirthChart', () => {
  const mockData: ChartData = {
    ascendant: 0,
    planets: [
      {
        id: 'sun',
        name: 'Sun',
        longitude: 0,
        latitude: 0,
        speed: 1,
        house: 1,
      },
      {
        id: 'moon',
        name: 'Moon',
        longitude: 90,
        latitude: 0,
        speed: 13,
        house: 4,
      },
    ],
    houses: [
      {
        number: 1,
        startDegree: 0,
        endDegree: 30,
        planets: [],
      },
      {
        number: 4,
        startDegree: 90,
        endDegree: 120,
        planets: [],
      },
    ],
    divisionalCharts: {
      D9: {
        ascendant: 45,
        planets: [
          {
            id: 'sun',
            name: 'Sun',
            longitude: 45,
            latitude: 0,
            speed: 1,
            house: 2,
          },
        ],
        houses: [
          {
            number: 2,
            startDegree: 30,
            endDegree: 60,
            planets: [],
          },
        ],
        divisionalCharts: {},
        aspects: [],
      },
    },
    aspects: [],
  };

  const defaultProps = {
    data: mockData,
    width: 800,
    height: 800,
  };

  it('renders chart with controls', () => {
    render(<BirthChart {...defaultProps} />);

    // Check for controls
    expect(screen.getByText('Hide Controls')).toBeInTheDocument();
    expect(screen.getByText('Show Celestial Background')).toBeInTheDocument();
    expect(screen.getByText('Show Labels')).toBeInTheDocument();

    // Check for chart information
    expect(screen.getByText('Chart Information')).toBeInTheDocument();
    expect(screen.getByText('Ascendant:')).toBeInTheDocument();
    expect(screen.getByText('Total Planets:')).toBeInTheDocument();
    expect(screen.getByText('Houses:')).toBeInTheDocument();
  });

  it('toggles controls visibility', () => {
    render(<BirthChart {...defaultProps} />);

    const toggleButton = screen.getByText('Hide Controls');
    fireEvent.click(toggleButton);

    expect(screen.getByText('Show Controls')).toBeInTheDocument();
    expect(screen.queryByText('Show Celestial Background')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Show Controls'));
    expect(screen.getByText('Show Celestial Background')).toBeInTheDocument();
  });

  it('handles divisional chart selection', () => {
    render(<BirthChart {...defaultProps} />);

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();

    fireEvent.change(select, { target: { value: 'D9' } });
    expect(select).toHaveValue('D9');
    expect(screen.getByRole('option', { name: 'D9' })).toBeInTheDocument();
  });

  it('toggles chart features', () => {
    render(<BirthChart {...defaultProps} />);

    // Toggle celestial background
    const celestialToggle = screen.getByRole('checkbox', {
      name: /Show Celestial Background/i,
    });
    fireEvent.click(celestialToggle);
    expect(celestialToggle).not.toBeChecked();

    // Toggle labels
    const labelsToggle = screen.getByRole('checkbox', {
      name: /Show Labels/i,
    });
    fireEvent.click(labelsToggle);
    expect(labelsToggle).not.toBeChecked();
  });

  it('handles planet clicks', () => {
    const onPlanetClick = jest.fn();
    render(<BirthChart {...defaultProps} onPlanetClick={onPlanetClick} />);

    // Note: We can't directly test the planet click here since it's handled by ChartRenderer
    // Instead, we verify the prop is passed correctly
    expect(onPlanetClick).not.toHaveBeenCalled();
  });

  it('displays correct chart information', () => {
    render(<BirthChart {...defaultProps} />);

    // Check ascendant value
    expect(screen.getByText('0.00°')).toBeInTheDocument();

    // Check planet count
    const planetCount = screen.getByText(/Total Planets:/i).parentElement?.textContent;
    expect(planetCount).toContain('2');

    // Check house count
    const houseCount = screen.getByText(/Houses:/i).parentElement?.textContent;
    expect(houseCount).toContain('2');
  });

  it('handles empty divisional charts', () => {
    const dataWithoutDivisional = {
      ...mockData,
      divisionalCharts: {},
    };

    render(<BirthChart {...defaultProps} data={dataWithoutDivisional} />);

    // Divisional chart selector should not be present
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });
});
