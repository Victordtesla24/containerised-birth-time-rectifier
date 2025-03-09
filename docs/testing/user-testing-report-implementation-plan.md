# Birth Time Rectifier - Implementation Plan (Continued)

This document continues the implementation plan from `test-results/implementation-plan.md`.

## Completing the CelestialCanvas Component Enhancement

```jsx
// Continued from previous implementation plan
// Calculate optimal performance settings
const optimizedSettings = useMemo(() => {
  return {
    dpr: pixelRatio,
    shadows: qualityLevel !== 'low',
    flat: qualityLevel === 'low',
    linear: true,
    gl: {
      antialias,
      alpha: false,
      stencil: false,
      depth: true,
      powerPreference: 'high-performance',
    }
  };
}, [pixelRatio, qualityLevel, antialiasing]);

return (
  <div style={{
    width: '100%',
    height: '100vh',
    position: fullscreen ? 'absolute' : 'fixed',
    top: 0,
    left: 0,
    overflow: 'hidden',
    zIndex: fullscreen ? 0 : -1,
    background: '#000'
  }} ref={canvasRef}>
    {canvasError ? (
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        color: 'white',
        textAlign: 'center',
        maxWidth: '80%',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        padding: '20px',
        borderRadius: '8px',
      }}>
        <h3>Graphics Processing Error</h3>
        <p>We encountered an issue with the 3D rendering.</p>
        <button onClick={() => setCanvasError(null)} style={{
          padding: '10px 20px',
          border: 'none',
          borderRadius: '4px',
          backgroundColor: '#4a90e2',
          color: 'white',
          fontSize: '14px',
          cursor: 'pointer'
        }}>
          Try Again with Simplified Graphics
        </button>
      </div>
    ) : (
      <ErrorBoundary
        fallback={<div>Could not load 3D scene</div>}
        onError={handleCanvasError}
      >
        <Canvas
          {...optimizedSettings}
          style={{
            background: 'radial-gradient(circle at center, #050a20 0%, #000000 100%)'
          }}
          onCreated={({ gl }) => {
            // Apply optimizations when canvas is created
            if (qualityLevel !== 'low') {
              gl.shadowMap.enabled = true;
              gl.shadowMap.type = THREE.PCFSoftShadowMap;
            }
            gl.outputColorSpace = THREE.SRGBColorSpace;

            // Expose renderer for texture loader
            textureManager.textureLoader.manager.renderer = gl;
          }}
        >
          {/* WebGL capability detection */}
          <WebGLCapabilityDetector onCapabilitiesDetected={handleCapabilitiesDetected} />

          {/* Performance monitoring */}
          <PerformanceMonitor />

          {/* Graceful WebGL context management */}
          <WebGLContextHandler />

          {/* Camera controls */}
          <PerspectiveCamera makeDefault position={[0, 0, 15]} fov={55} />

          {/* Main celestial objects with quality-based rendering */}
          <Suspense fallback={<LoadingScreen />}>
            <AdaptivePlanetSystem mousePosition={mousePosition} />
          </Suspense>
        </Canvas>
      </ErrorBoundary>
    )}
  </div>
);
}

export default CelestialCanvas;
```

### 3. Fix Navigation Flow Issues

#### 3.1 Improved Form Submission and Loading State

```jsx
import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

// Components
import CelestialCanvas from '../components/three-scene/CelestialCanvas';
import LoadingIndicator from '../components/ui/LoadingIndicator';
import ErrorMessage from '../components/ui/ErrorMessage';

const BirthDetailsForm = () => {
  // Form state
  const [formData, setFormData] = useState({
    fullName: '',
    birthDate: '',
    birthTime: '',
    birthLocation: '',
    additionalInfo: ''
  });

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});

  // Router for navigation
  const router = useRouter();

  // Handle input changes
  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Clear validation error when field is edited
    if (validationErrors[name]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  }, [validationErrors]);

  // Validate form data
  const validateForm = useCallback(() => {
    const errors = {};

    if (!formData.fullName.trim()) {
      errors.fullName = 'Name is required';
    }

    if (!formData.birthDate) {
      errors.birthDate = 'Birth date is required';
    } else {
      // Simple date validation
      const dateRegex = /^\d{2}\/\d{2}\/\d{4}$|^\d{4}-\d{2}-\d{2}$/;
      if (!dateRegex.test(formData.birthDate)) {
        errors.birthDate = 'Invalid date format. Use DD/MM/YYYY or YYYY-MM-DD';
      }
    }

    if (!formData.birthTime) {
      errors.birthTime = 'Approximate birth time is required';
    }

    if (!formData.birthLocation.trim()) {
      errors.birthLocation = 'Birth location is required';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData]);

  // Handle form submission with enhanced error handling
  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();

    // Validate form data
    if (!validateForm()) {
      return;
    }

    // Update UI state
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // First, validate birth location with geocoding service
      const geocodeResponse = await axios.post('/api/geocode', {
        query: formData.birthLocation
      }, {
        timeout: 10000 // 10 second timeout
      });

      if (!geocodeResponse.data || !geocodeResponse.data.results || geocodeResponse.data.results.length === 0) {
        throw new Error('Location not found. Please enter a valid city and country.');
      }

      // Get coordinates from geocoding result
      const location = geocodeResponse.data.results[0];

      // Submit complete form data with coordinates
      const response = await axios.post('/api/chart/generate', {
        ...formData,
        latitude: location.latitude,
        longitude: location.longitude,
        timezone: location.timezone
      }, {
        timeout: 30000 // 30 second timeout for chart generation
      });

      // Handle successful submission
      if (response.data && response.data.chart_id) {
        // Store chart ID in localStorage for potential recovery
        localStorage.setItem('lastChartId', response.data.chart_id);

        // Navigate to results page
        router.push(`/chart/${response.data.chart_id}`);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Form submission error:', error);

      // Set appropriate error message based on error type
      setSubmitError(
        error.response?.data?.message ||
        error.message ||
        'An unexpected error occurred. Please try again.'
      );

      // Reset submission state
      setIsSubmitting(false);
    }
  }, [formData, validateForm, router]);

  return (
    <div className="birth-form-container">
      <div className="cosmic-background">
        <CelestialCanvas />
      </div>

      <div className="form-content">
        <h2>Birth Time Analysis</h2>
        <p>Enter your birth details to begin the cosmic analysis</p>

        {submitError && (
          <ErrorMessage
            message={submitError}
            onDismiss={() => setSubmitError(null)}
          />
        )}

        <form onSubmit={handleSubmit}>
          {/* Form fields with validation */}
          <div className="form-group">
            <label htmlFor="fullName">Full Name</label>
            <input
              type="text"
              id="fullName"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              className={validationErrors.fullName ? 'error' : ''}
              disabled={isSubmitting}
              placeholder="Your full name"
            />
            {validationErrors.fullName && (
              <span className="error-text">{validationErrors.fullName}</span>
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="birthDate">Birth Date</label>
              <input
                type="date"
                id="birthDate"
                name="birthDate"
                value={formData.birthDate}
                onChange={handleChange}
                className={validationErrors.birthDate ? 'error' : ''}
                disabled={isSubmitting}
              />
              {validationErrors.birthDate && (
                <span className="error-text">{validationErrors.birthDate}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="birthTime">Approximate Birth Time</label>
              <input
                type="time"
                id="birthTime"
                name="birthTime"
                value={formData.birthTime}
                onChange={handleChange}
                className={validationErrors.birthTime ? 'error' : ''}
                disabled={isSubmitting}
              />
              {validationErrors.birthTime && (
                <span className="error-text">{validationErrors.birthTime}</span>
              )}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="birthLocation">Birth Location</label>
            <input
              type="text"
              id="birthLocation"
              name="birthLocation"
              value={formData.birthLocation}
              onChange={handleChange}
              className={validationErrors.birthLocation ? 'error' : ''}
              disabled={isSubmitting}
              placeholder="City, Country"
            />
            {validationErrors.birthLocation && (
              <span className="error-text">{validationErrors.birthLocation}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="additionalInfo">Additional Information</label>
            <textarea
              id="additionalInfo"
              name="additionalInfo"
              value={formData.additionalInfo}
              onChange={handleChange}
              disabled={isSubmitting}
              placeholder="Any additional details that may help with birth time rectification"
              rows={4}
            />
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? <LoadingIndicator /> : 'Begin Analysis'}
            </button>

            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setFormData({
                  fullName: '',
                  birthDate: '',
                  birthTime: '',
                  birthLocation: '',
                  additionalInfo: ''
                });
                setValidationErrors({});
              }}
              disabled={isSubmitting}
            >
              Reset Form
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BirthDetailsForm;
```

#### 3.2 Improved Loading Indicators and State Management

```jsx
// LoadingIndicator component with better visibility
import React from 'react';

// Simple loading spinner with animation
const LoadingIndicator = ({ size = 'medium', message = '' }) => {
  // Size classes
  const sizeClass = {
    small: 'loading-indicator--small',
    medium: 'loading-indicator--medium',
    large: 'loading-indicator--large',
  }[size] || 'loading-indicator--medium';

  return (
    <div className={`loading-indicator ${sizeClass}`}>
      <div className="loading-spinner">
        <div className="spinner-inner"></div>
      </div>
      {message && <p className="loading-message">{message}</p>}

      <style jsx>{`
        .loading-indicator {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }

        .loading-indicator--small .loading-spinner {
          width: 20px;
          height: 20px;
        }

        .loading-indicator--medium .loading-spinner {
          width: 30px;
          height: 30px;
        }

        .loading-indicator--large .loading-spinner {
          width: 50px;
          height: 50px;
        }

        .loading-spinner {
          border-radius: 50%;
          position: relative;
          border: 2px solid rgba(255, 255, 255, 0.2);
        }

        .spinner-inner {
          position: absolute;
          left: -2px;
          top: -2px;
          right: -2px;
          bottom: -2px;
          border-radius: 50%;
          border: 2px solid transparent;
          border-top-color: #fff;
          animation: spin 1s linear infinite;
        }

        .loading-message {
          margin-top: 8px;
          font-size: 14px;
          color: #fff;
          text-align: center;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default LoadingIndicator;
```

#### 3.3 Create a Robust Chart Result Page

```jsx
// ChartResult.jsx - Displays the chart with enhanced error handling
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

// Components
import LoadingIndicator from '../components/ui/LoadingIndicator';
import ErrorMessage from '../components/ui/ErrorMessage';
import ChartVisualization from '../components/charts/ChartVisualization';
import RectificationDetails from '../components/charts/RectificationDetails';
import RetryButton from '../components/ui/RetryButton';

// Chart result page with robust error handling and loading states
const ChartResult = () => {
  // State
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);

  // Router to get chart ID from URL
  const router = useRouter();
  const { chartId } = router.query;

  // Fetch chart data when component mounts
  useEffect(() => {
    // Skip if chart ID is not available yet
    if (!chartId) return;

    let isMounted = true;
    let source = axios.CancelToken.source();

    // Reset state
    setLoading(true);
    setError(null);
    setLoadingProgress(0);

    // Function to fetch chart data
    const fetchChartData = async () => {
      try {
        // Artificial progress indicator (since the actual API doesn't provide progress)
        const progressInterval = setInterval(() => {
          if (isMounted) {
            setLoadingProgress(prev => {
              const newProgress = prev + (100 - prev) * 0.1;
              return Math.min(newProgress, 95); // Cap at 95% until actual data arrives
            });
          }
        }, 500);

        // Fetch chart data
        const response = await axios.get(`/api/chart/${chartId}`, {
          cancelToken: source.token,
          timeout: 30000 // 30 second timeout
        });

        // Clear the progress interval
        clearInterval(progressInterval);

        // Update state with received data
        if (isMounted) {
          setChartData(response.data);
          setLoadingProgress(100);
          setLoading(false);
        }
      } catch (err) {
        console.error('Error fetching chart data:', err);

        // Clear the progress interval
        clearInterval(progressInterval);

        // Set error message
        if (isMounted) {
          setError(
            err.response?.data?.message ||
            err.message ||
            'Failed to load chart data. Please try again.'
          );
          setLoading(false);
        }
      }
    };

    // Start fetching data
    fetchChartData();

    // Cleanup function
    return () => {
      isMounted = false;
      source.cancel('Component unmounted');
    };
  }, [chartId]);

  // Handle retry
  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setLoadingProgress(0);

    // Re-fetch data by forcing a re-render (using the same chart ID)
    router.replace(router.asPath);
  };

  // Render loading state
  if (loading) {
    return (
      <div className="chart-result-container loading">
        <LoadingIndicator size="large" message="Generating astrological chart..." />
        <div className="progress-bar">
          <div
            className="progress-bar-inner"
            style={{ width: `${loadingProgress}%` }}
          ></div>
        </div>
        <p className="progress-text">{Math.round(loadingProgress)}% complete</p>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="chart-result-container error">
        <ErrorMessage message={error} />
        <RetryButton onClick={handleRetry} />
        <button
          className="btn-secondary"
          onClick={() => router.push('/')}
        >
          Return to Form
        </button>
      </div>
    );
  }

  // Render chart data
  return (
    <div className="chart-result-container">
      <h1>Your Astrological Chart</h1>

      {chartData && (
        <>
          <div className="chart-visualization-container">
            <ChartVisualization chartData={chartData} />
          </div>

          <div className="rectification-details">
            <RectificationDetails
              originalTime={chartData.birth_details.time}
              rectifiedTime={chartData.rectified_time}
              confidenceScore={chartData.confidence_score}
              explanation={chartData.explanation}
            />
          </div>

          <div className="chart-actions">
            <button
              className="btn-primary"
              onClick={() => router.push(`/export/${chartData.chart_id}`)}
            >
              Export Chart
            </button>

            <button
              className="btn-secondary"
              onClick={() => router.push('/')}
            >
              New Analysis
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ChartResult;
```

#### 3.4 Add Network Request Progress with Interceptors

```jsx
// api/apiClient.js - Enhanced Axios client with better error handling and retry logic
import axios from 'axios';
import { toast } from 'react-toastify';

// Create custom Axios instance with default config
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    // Extract information from error
    const originalRequest = error.config;
    const status = error.response?.status;

    // Only retry once
    if (originalRequest._retry) {
      return Promise.reject(error);
    }

    // Handle specific error types
    switch (status) {
      case 401: // Unauthorized
        // Redirect to login page or refresh token
        // window.location.href = '/login';
        toast.error('Session expired. Please refresh the page to continue.');
        break;

      case 408: // Request Timeout
      case 429: // Too Many Requests
      case 500: // Server Error
      case 502: // Bad Gateway
      case 503: // Service Unavailable
      case 504: // Gateway Timeout
        // Retry these errors automatically after delay
        originalRequest._retry = true;

        // Show retry notification
        toast.info('Connection issue. Retrying...');

        // Wait 2 seconds before retrying
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Retry request
        return apiClient(originalRequest);

      default:
        break;
    }

    // Reject with the error for further handling
    return Promise.reject(error);
  }
);

// Add progress reporting to requests (for uploads/downloads)
apiClient.defaults.onDownloadProgress = (progressEvent) => {
  // Dispatch download progress event that components can listen for
  const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);

  // Create and dispatch custom event
  const progressPayload = {
    url: progressEvent.target.responseURL,
    loaded: progressEvent.loaded,
    total: progressEvent.total,
    percent: percentCompleted,
    type: 'download'
  };

  const event = new CustomEvent('apiProgress', { detail: progressPayload });
  window.dispatchEvent(event);
};

apiClient.defaults.onUploadProgress = (progressEvent) => {
  // Dispatch upload progress event that components can listen for
  const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);

  // Create and dispatch custom event
  const progressPayload = {
    url: progressEvent.target.responseURL,
    loaded: progressEvent.loaded,
    total: progressEvent.total,
    percent: percentCompleted,
    type: 'upload'
  };

  const event = new CustomEvent('apiProgress', { detail: progressPayload });
  window.dispatchEvent(event);
};

export default apiClient;
```

## 4. Testing Strategy

### 4.1 Manual Testing Checklist

The following checklist should be used to verify the fixes have resolved the identified issues:

1. **WebGL Rendering**
   - [ ] Test on low-end devices to verify automatic quality reduction
   - [ ] Test error recovery after context loss
   - [ ] Verify texture loading fallbacks work when images fail to load

2. **Performance**
   - [ ] Measure frame rates to verify they stay above 30 FPS
   - [ ] Test adaptive quality scaling under high load
   - [ ] Verify memory usage stays within reasonable bounds

3. **Navigation Flow**
   - [ ] Test form submission with valid and invalid inputs
   - [ ] Verify proper loading indicators appear during long operations
   - [ ] Confirm successful navigation between form and results
   - [ ] Test network error handling and retry functionality

### 4.2 Automated Testing Approach

```jsx
// tests/components/WebGLErrorHandling.test.js
import React from 'react';
import { render, act } from '@testing-library/react';
import { WebGLContextHandler } from '../../src/components/three-scene/core/WebGLContextHandler';

// Mock three.js and React Three Fiber
jest.mock('@react-three/fiber', () => ({
  useThree: () => ({
    gl: {
      domElement: {
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      }
    },
    invalidate: jest.fn()
  })
}));

describe('WebGLContextHandler', () => {
  let originalConsoleWarn;
  let originalConsoleError;

  beforeEach(() => {
    // Mock console methods
    originalConsoleWarn = console.warn;
    originalConsoleError = console.error;
    console.warn = jest.fn();
    console.error = jest.fn();

    // Mock document methods
    document.createElement = jest.fn().mockReturnValue({
      style: {}
    });
    document.body.appendChild = jest.fn();
    document.body.removeChild = jest.fn();
  });

  afterEach(() => {
    // Restore console methods
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;

    // Clear mocks
    jest.clearAllMocks();
  });

  it('should handle WebGL context loss gracefully', () => {
    // Render component
    render(<WebGLContextHandler />);

    // Get addEventListener mock
    const { gl } = require('@react-three/fiber').useThree();
    const addEventListener = gl.domElement.addEventListener;

    // Extract context loss handler
    const contextLostHandler = addEventListener.mock.calls.find(
      call => call[0] === 'webglcontextlost'
    )[1];

    // Create mock event
    const mockEvent = {
      preventDefault: jest.fn()
    };

    // Simulate context loss
    act(() => {
      contextLostHandler(mockEvent);
    });

    // Assertions
    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('WebGL context lost')
    );
    expect(document.createElement).toHaveBeenCalled();
    expect(document.body.appendChild).toHaveBeenCalled();
  });

  it('should handle WebGL context restoration', () => {
    // Render component
    render(<WebGLContextHandler />);

    // Get addEventListener mock
    const { gl, invalidate } = require('@react-three/fiber').useThree();
    const addEventListener = gl.domElement.addEventListener;

    // Extract context restored handler
    const contextRestoredHandler = addEventListener.mock.calls.find(
      call => call[0] === 'webglcontextrestored'
    )[1];

    // Simulate context restoration
    act(() => {
      contextRestoredHandler();
    });

    // Assertions
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('WebGL context restored')
    );
    expect(invalidate).toHaveBeenCalled();
  });
});
```

### 4.3 E2E Test for Form Submission

```jsx
// tests/e2e/formSubmission.spec.js
import { test, expect } from '@playwright/test';

test('form submission should work with valid data', async ({ page }) => {
  // Navigate to home page
  await page.goto('/');

  // Fill in form fields
  await page.fill('#fullName', 'John Smith');
  await page.fill('#birthDate', '1990-01-15');
  await page.fill('#birthTime', '14:30');
  await page.fill('#birthLocation', 'New York, USA');
  await page.fill('#additionalInfo', 'Had a major career change at age 32');

  // Submit form
  await page.click('button.btn-primary');

  // Check loading indicator appears
  await expect(page.locator('.loading-indicator')).toBeVisible();

  // Wait for navigation to results page
  await page.waitForNavigation();

  // Verify we're on the results page
  const url = page.url();
  expect(url).toContain('/chart/');

  // Check results are displayed
  await expect(page.locator('.chart-result-container')).toBeVisible();
  await expect(page.locator('.chart-visualization-container')).toBeVisible();
});

test('form displays validation errors for invalid data', async ({ page }) => {
  // Navigate to home page
  await page.goto('/');

  // Submit form without filling it
  await page.click('button.btn-primary');

  // Check validation errors are displayed
  await expect(page.locator('.error-text')).toHaveCount(3); // Name, date, location required

  // Fill invalid date format
  await page.fill('#birthDate', 'invalid-date');

  // Check specific validation error
  await expect(page.locator('#birthDate + .error-text')).toContainText('Invalid date format');
});
```

## 5. Implementation Order

To ensure the smoothest implementation and testing process, follow this order:

1. **WebGL Performance and Error Handling**
   - Implement TextureManager with robust error handling
   - Create WebGL capability detection
   - Enhance WebGLContextHandler for better recovery

2. **Quality Optimization**
   - Implement QualityContext for adaptive rendering
   - Create simplified fallback components for low-end devices
   - Optimize CelestialCanvas rendering settings

3. **Navigation Flow**
   - Improve form validation and submission
   - Add loading indicators with progress
   - Enhance error handling for network requests

4. **Testing**
   - Run manual tests on different devices
   - Execute automated tests
   - Perform end-to-end testing
