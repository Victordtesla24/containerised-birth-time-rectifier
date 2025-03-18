import React from 'react';
import { render, screen } from '@testing-library/react';
import LifeEventsQuestionnaire from '../index';
import { BirthDetails } from '@/types';
import { RouterContext } from 'next/dist/shared/lib/router-context.shared-runtime';

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

// Create a mock router
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

describe('LifeEventsQuestionnaire', () => {
  // Test isLoading state which doesn't require complex mocking
  it('displays processing message when isLoading is true', () => {
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
});
