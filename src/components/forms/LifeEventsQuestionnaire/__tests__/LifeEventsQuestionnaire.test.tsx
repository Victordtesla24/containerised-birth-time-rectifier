import React from 'react';
import { render, screen } from '@testing-library/react';
import LifeEventsQuestionnaire from '../index';
import { BirthDetails } from '@/types';

// Disable network requests
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({})
  })
) as jest.Mock;

// Sample birth details for testing
const mockBirthDetails: BirthDetails = {
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

describe('LifeEventsQuestionnaire', () => {
  // Test isLoading state which doesn't require complex mocking
  it('displays processing message when isLoading is true', () => {
    render(
      <LifeEventsQuestionnaire
        birthDetails={mockBirthDetails}
        onSubmit={jest.fn()}
        isLoading={true}
      />
    );

    // Check for the precise loading message in the component
    expect(
      screen.getByText("Processing your answers and rectifying birth time...")
    ).toBeInTheDocument();
  });
});
