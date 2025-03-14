import React from 'react';

/**
 * Loading indicator component
 * @param {Object} props - Component props
 * @param {string} props.size - Size of the indicator (small, medium, large)
 * @param {string} props.message - Optional message to display with the loading indicator
 * @param {string} props.color - Color of the loading indicator
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Loading indicator component
 */
const LoadingIndicator = ({
  size = 'medium',
  message = 'Loading...',
  color = 'currentColor',
  className = ''
}) => {
  // Determine the size of the spinner
  const sizeMap = {
    small: {
      width: '16px',
      height: '16px',
      borderWidth: '2px',
    },
    medium: {
      width: '32px',
      height: '32px',
      borderWidth: '3px',
    },
    large: {
      width: '48px',
      height: '48px',
      borderWidth: '4px',
    },
  };

  const spinnerStyle = sizeMap[size] || sizeMap.medium;

  return (
    <div
      className={`loading-indicator ${className}`}
      data-testid="loading-indicator"
      aria-label="Loading"
      role="status"
      id="loading-indicator"
    >
      <div
        className="spinner"
        data-testid="loading-spinner"
        style={{
          ...spinnerStyle,
          borderColor: `${color} transparent transparent transparent`,
        }}
      />
      {message && (
        <p
          className="loading-message"
          data-testid="loading-message"
        >
          {message}
        </p>
      )}

      <style jsx>{`
        .loading-indicator {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 1rem;
          z-index: 1000;
        }

        .spinner {
          border-radius: 50%;
          border-style: solid;
          border-color: currentColor transparent transparent transparent;
          animation: spin 1s linear infinite;
        }

        .loading-message {
          margin-top: 0.5rem;
          font-size: 0.875rem;
          color: ${color};
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
