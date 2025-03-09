import React from 'react';

/**
 * Enhanced loading indicator with multiple styles and customization options
 * Designed for consistent loading state feedback throughout the application
 */
const LoadingIndicator = ({
  size = 'medium',
  type = 'spinner',
  color = '#FFFFFF',
  message = '',
  progress = null,
  inline = false
}) => {
  // Size presets (in pixels)
  const sizeMap = {
    small: { container: 16, indicator: 16, fontSize: 12 },
    medium: { container: 24, indicator: 24, fontSize: 14 },
    large: { container: 40, indicator: 40, fontSize: 16 },
    xlarge: { container: 60, indicator: 60, fontSize: 18 }
  };

  // Use provided size or fallback to medium
  const sizeObj = sizeMap[size] || sizeMap.medium;

  // Handle custom numeric sizes
  const dimensions = typeof size === 'number'
    ? { container: size, indicator: size, fontSize: Math.max(12, size / 2) }
    : sizeObj;

  // Generate styles based on configurations
  const containerStyle = {
    display: 'flex',
    flexDirection: inline ? 'row' : 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: inline ? '12px' : '8px'
  };

  // Create loading indicator based on type
  const renderIndicator = () => {
    switch (type) {
      case 'dots':
        return (
          <div className="loading-dots" style={{ height: dimensions.indicator }}>
            <div className="dot" style={{ backgroundColor: color }}></div>
            <div className="dot" style={{ backgroundColor: color }}></div>
            <div className="dot" style={{ backgroundColor: color }}></div>
            <style jsx>{`
              .loading-dots {
                display: flex;
                align-items: center;
                gap: 4px;
              }
              .dot {
                width: ${dimensions.indicator / 4}px;
                height: ${dimensions.indicator / 4}px;
                border-radius: 50%;
                animation: dotPulse 1.5s infinite ease-in-out;
              }
              .dot:nth-child(1) {
                animation-delay: 0s;
              }
              .dot:nth-child(2) {
                animation-delay: 0.2s;
              }
              .dot:nth-child(3) {
                animation-delay: 0.4s;
              }
              @keyframes dotPulse {
                0%, 100% { transform: scale(0.5); opacity: 0.5; }
                50% { transform: scale(1); opacity: 1; }
              }
            `}</style>
          </div>
        );

      case 'bar':
        return (
          <div
            className="loading-bar"
            style={{
              width: dimensions.container * 3,
              height: dimensions.indicator / 3
            }}
          >
            <div className="bar-progress" style={{ backgroundColor: color }}></div>
            <style jsx>{`
              .loading-bar {
                position: relative;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: ${dimensions.indicator / 6}px;
                overflow: hidden;
              }

              .bar-progress {
                position: absolute;
                top: 0;
                left: 0;
                height: 100%;
                width: 30%;
                border-radius: ${dimensions.indicator / 6}px;
                animation: barMove 1.5s infinite ease-in-out;
              }

              @keyframes barMove {
                0% { left: -30%; }
                100% { left: 100%; }
              }
            `}</style>
          </div>
        );

      case 'progress':
        // Ensure progress is a number between 0 and 100
        const progressValue = Math.min(100, Math.max(0, progress || 0));

        return (
          <div
            className="progress-bar"
            style={{
              width: dimensions.container * 3,
              height: dimensions.indicator / 3
            }}
          >
            <div
              className="progress-fill"
              style={{
                width: `${progressValue}%`,
                backgroundColor: color
              }}
            ></div>
            <style jsx>{`
              .progress-bar {
                position: relative;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: ${dimensions.indicator / 6}px;
                overflow: hidden;
              }

              .progress-fill {
                position: absolute;
                top: 0;
                left: 0;
                height: 100%;
                transition: width 0.3s ease-in-out;
                border-radius: ${dimensions.indicator / 6}px;
              }
            `}</style>
          </div>
        );

      case 'pulse':
        return (
          <div
            className="loading-pulse"
            style={{
              width: dimensions.indicator,
              height: dimensions.indicator
            }}
          >
            <div className="pulse-ring" style={{ borderColor: color }}></div>
            <style jsx>{`
              .loading-pulse {
                position: relative;
              }

              .pulse-ring {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: ${dimensions.indicator * 0.8}px;
                height: ${dimensions.indicator * 0.8}px;
                border: 2px solid;
                border-radius: 50%;
                opacity: 0;
                animation: pulse 1.5s linear infinite;
              }

              @keyframes pulse {
                0% {
                  transform: translate(-50%, -50%) scale(0.5);
                  opacity: 0;
                }
                50% {
                  opacity: 1;
                }
                100% {
                  transform: translate(-50%, -50%) scale(1.2);
                  opacity: 0;
                }
              }
            `}</style>
          </div>
        );

      case 'spinner':
      default:
        return (
          <div
            className="spinner"
            style={{
              width: dimensions.indicator,
              height: dimensions.indicator,
              borderColor: `${color} transparent transparent transparent`
            }}
          >
            <style jsx>{`
              .spinner {
                border-radius: 50%;
                border-width: ${Math.max(2, dimensions.indicator / 10)}px;
                border-style: solid;
                animation: spin 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
              }

              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        );
    }
  };

  // Render loading message if provided
  const renderMessage = () => {
    if (!message) return null;

    return (
      <div
        className="loading-message"
        style={{
          fontSize: `${dimensions.fontSize}px`,
          color: color,
          textAlign: 'center',
          marginTop: inline ? 0 : '8px'
        }}
      >
        {message}
        {type === 'progress' && progress !== null && (
          <span className="progress-percentage">
            &nbsp;({Math.round(progress)}%)
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="loading-indicator" style={containerStyle}>
      {renderIndicator()}
      {renderMessage()}
    </div>
  );
};

export default LoadingIndicator;
