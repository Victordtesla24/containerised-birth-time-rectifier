import React from 'react';

// Mock QualityProvider for testing
export const QualityProvider = ({ children }) => {
  return <div data-testid="mock-quality-provider">{children}</div>;
};

// Mock CelestialCanvas for testing
export const CelestialCanvas = (props) => {
  React.useEffect(() => {
    // Access the canvas and trigger getContext to ensure our mock is called
    const canvas = document.createElement('canvas');
    canvas.getContext('webgl');
  }, []);

  return (
    <div data-testid="mock-celestial-canvas">
      <canvas className="celestial-canvas" />
      <div className="fallback-content">
        <div className="fallback-message">
          <h3>3D Visualization Not Available</h3>
          <p>Your device does not support WebGL, which is required for the 3D celestial visualization.</p>
        </div>
      </div>
    </div>
  );
};
