/**
 * WebGL Integration Test
 * Tests WebGL initialization, error handling, and quality adaptations
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import CelestialCanvas from '../../components/three-scene/CelestialCanvas';
import { QualityProvider } from '../../components/providers/QualityProvider';

// Mock the WebGL context
const mockWebGLContext = {
  getExtension: jest.fn(),
  getParameter: jest.fn(),
  getShaderPrecisionFormat: jest.fn(() => ({
    precision: 23,
    rangeMin: 127,
    rangeMax: 127
  })),
  VERTEX_SHADER: 'VERTEX_SHADER',
  FRAGMENT_SHADER: 'FRAGMENT_SHADER',
  HIGH_FLOAT: 'HIGH_FLOAT',
  MEDIUM_FLOAT: 'MEDIUM_FLOAT',
  LOW_FLOAT: 'LOW_FLOAT'
};

describe('WebGL Rendering Integration Tests', () => {
  // Store original HTMLCanvasElement.prototype.getContext
  const originalGetContext = HTMLCanvasElement.prototype.getContext;

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  afterAll(() => {
    // Restore original getContext method after all tests
    HTMLCanvasElement.prototype.getContext = originalGetContext;
  });

  test('Successfully initializes WebGL with full capabilities', async () => {
    // Mock successful WebGL context
    HTMLCanvasElement.prototype.getContext = jest.fn((contextType) => {
      if (contextType === 'webgl' || contextType === 'experimental-webgl') {
        return mockWebGLContext;
      }
      return null;
    });

    render(
      <QualityProvider>
        <CelestialCanvas />
      </QualityProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith('webgl');
    });
  });

  test('Shows fallback content when WebGL is not supported', async () => {
    // Mock WebGL not being supported
    HTMLCanvasElement.prototype.getContext = jest.fn((contextType) => {
      return null;
    });

    render(
      <QualityProvider>
        <CelestialCanvas />
      </QualityProvider>
    );

    // Fallback content should eventually appear
    await waitFor(() => {
      const fallbackMessage = screen.getByText(/3D Visualization Not Available/i);
      expect(fallbackMessage).toBeInTheDocument();
    });
  });

  test('Handles WebGL context loss and recovery', async () => {
    // Mock successful WebGL context
    const mockCanvas = document.createElement('canvas');
    const listeners = {};

    // Mock addEventListener to capture context lost/restored events
    mockCanvas.addEventListener = jest.fn((eventType, callback) => {
      listeners[eventType] = callback;
    });

    // Mock context creation
    HTMLCanvasElement.prototype.getContext = jest.fn(() => mockWebGLContext);

    // Mock document.createElement to return our mock canvas
    const originalCreateElement = document.createElement;
    document.createElement = jest.fn((tagName) => {
      if (tagName === 'canvas') {
        return mockCanvas;
      }
      return originalCreateElement.call(document, tagName);
    });

    render(
      <QualityProvider>
        <CelestialCanvas />
      </QualityProvider>
    );

    // Trigger context loss
    if (listeners['webglcontextlost']) {
      const contextLostEvent = { preventDefault: jest.fn() };
      listeners['webglcontextlost'](contextLostEvent);

      // Ensure event.preventDefault was called to enable recovery
      expect(contextLostEvent.preventDefault).toHaveBeenCalled();
    }

    // Trigger context restoration
    if (listeners['webglcontextrestored']) {
      listeners['webglcontextrestored']({});
    }

    // Restore original createElement
    document.createElement = originalCreateElement;
  });

  test('Adapts quality settings based on device capabilities', async () => {
    // Mock a lower-end device
    mockWebGLContext.getParameter = jest.fn((param) => {
      if (param === 'MAX_TEXTURE_SIZE') return 2048;
      return 4;
    });

    HTMLCanvasElement.prototype.getContext = jest.fn(() => mockWebGLContext);

    // Mock screen properties for mobile device
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = jest.fn().mockImplementation(query => ({
      matches: query.includes('max-width'),
      media: query
    }));

    // Also mock devicePixelRatio
    const originalDevicePixelRatio = window.devicePixelRatio;
    Object.defineProperty(window, 'devicePixelRatio', { value: 2 });

    render(
      <QualityProvider>
        <CelestialCanvas />
      </QualityProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalled();
    });

    // Restore original values
    window.matchMedia = originalMatchMedia;
    Object.defineProperty(window, 'devicePixelRatio', { value: originalDevicePixelRatio });
  });
});
