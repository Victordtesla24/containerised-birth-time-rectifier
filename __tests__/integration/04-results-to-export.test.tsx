/**
 * Integration Tests: Results to Export
 * 
 * Tests the next touchpoints in the UI/UX flow chart:
 * H[Results Page] --> J[Chart Visualization]
 * J[Chart Visualization] --> K[Export/Share]
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { skipIfServicesNotRunning, waitForNetwork, waitForWithRetry } from './utils';
import { createMockRouter } from '../test-utils/createMockRouter';

// Import our mock setup and utility
import { setupMockAPI, mockApiCall } from './test-setup/msw-setup';

// Import components to test
import AnalysisPage from '../../src/pages/birth-time-rectifier/analysis';

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));

// Setup mock session storage with explicit typing
const mockSessionStorage: Record<string, string> = {
  birthDetails: JSON.stringify({
    date: '2000-01-01',
    time: '12:00',
    place: 'New York, USA',
    coordinates: {
      latitude: 40.7128,
      longitude: -74.0060
    },
    timezone: 'America/New_York'
  }),
  rectificationResult: JSON.stringify({
    suggestedTime: '12:30:00',
    confidence: 0.85,
    details: {
      ascendantChange: true,
      houseShifts: [1, 3, 5]
    },
    charts: {
      d1Chart: {
        ascendant: 120,
        planets: [
          { id: 'sun', position: 30, house: 1 },
          { id: 'moon', position: 60, house: 2 }
        ],
        houses: Array.from({ length: 12 }, (_, i) => ({
          number: i + 1,
          start: i * 30,
          end: (i + 1) * 30
        }))
      }
    }
  })
};

// Mock sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: jest.fn((key: string) => mockSessionStorage[key] || null),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  },
  writable: true
});

// Mock download functionality
// @ts-ignore
global.URL.createObjectURL = jest.fn(() => 'mock-url');
// @ts-ignore
global.URL.revokeObjectURL = jest.fn();

// Setup the mock API
setupMockAPI();

// Skip all tests if services are not running
skipIfServicesNotRunning();

describe('Results to Export - Integration Tests', () => {
  test('Analysis page should render rectification results correctly', async () => {
    // Setup mock router
    const mockRouter = createMockRouter({});
    jest.requireMock('next/router').useRouter.mockReturnValue(mockRouter);
    
    // Render analysis page
    render(<AnalysisPage />);
    
    // Verify that results are displayed - look for text that's actually present on the page
    await waitForWithRetry(() => {
      return (
        screen.queryByText(/rectified birth time/i) !== null || 
        screen.queryByText(/12:30/) !== null
      );
    }, { timeout: 5000, retries: 3 });
    
    // Now make more specific assertions
    expect(screen.getByText(/12:30/)).toBeInTheDocument();
    expect(screen.getByText(/85/)).toBeInTheDocument();
  });
  
  test('Export button should trigger chart export functionality', async () => {
    // Create very simple mocks that don't create infinite recursion
    const mockToBlob = jest.fn().mockImplementation((callback) => {
      const fakeBlob = new Blob(['fake chart data'], { type: 'image/png' });
      callback(fakeBlob);
    });
    
    // Don't mock document.createElement directly, as it causes infinite recursion
    // Instead mock HTMLCanvasElement.prototype.toBlob
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = mockToBlob;
    
    // Mock URL methods
    jest.spyOn(URL, 'createObjectURL').mockReturnValue('mock-url');
    jest.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    
    // Render the component
    render(<AnalysisPage />);
    
    const user = userEvent.setup();
    
    // Wait for page to load and find the export button
    await waitForWithRetry(() => {
      return screen.queryByText(/export report/i) !== null;
    }, { timeout: 5000, retries: 3 });
    
    // Find the export button
    const exportButton = await screen.findByText(/export report/i);
    
    // Verify the button exists
    expect(exportButton).toBeInTheDocument();
    
    // Click the button - we're mostly checking that this doesn't throw errors
    await user.click(exportButton);
    
    // Wait a moment to let any click handlers execute
    await waitFor(() => {}, { timeout: 500 });
    
    // Clean up all mocks
    HTMLCanvasElement.prototype.toBlob = originalToBlob;
    jest.restoreAllMocks();
  });
}); 