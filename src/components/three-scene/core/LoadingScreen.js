/**
 * LoadingScreen Component
 * Displays a loading screen with progress bar and error handling for WebGL scenes
 */
import React from 'react';
import PropTypes from 'prop-types';

const LoadingScreen = ({
  isLoading = true,
  progress = 0,
  error = null,
  onRetry = null,
  message = 'Loading...'
}) => {
  const formattedProgress = Math.min(100, Math.max(0, Math.round(progress * 100)));

  return (
    <div className={`loading-screen ${!isLoading ? 'hidden' : ''}`}>
      {error ? (
        <div className="error-container">
          <div className="error-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <h3>Loading Error</h3>
          <p className="error-message">{error.message || 'Failed to load 3D visualization'}</p>
          {onRetry && (
            <button onClick={onRetry} className="retry-button">
              Try Again
            </button>
          )}
        </div>
      ) : (
        <div className="loading-container">
          <div className="loading-spinner">
            <div className="spinner"></div>
          </div>
          <h3>{message}</h3>
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${formattedProgress}%` }}></div>
            <div className="progress-text">{formattedProgress}%</div>
          </div>
        </div>
      )}

      <style jsx>{`
        .loading-screen {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
          color: white;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        .loading-screen.hidden {
          opacity: 0;
          visibility: hidden;
          transition: opacity 0.5s ease, visibility 0.5s ease;
        }

        .loading-container,
        .error-container {
          background-color: rgba(30, 41, 59, 0.7);
          border-radius: 12px;
          padding: 32px;
          width: 80%;
          max-width: 350px;
          text-align: center;
          backdrop-filter: blur(10px);
          box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
          border: 1px solid rgba(96, 165, 250, 0.2);
        }

        .loading-spinner {
          margin-bottom: 20px;
        }

        .spinner {
          width: 48px;
          height: 48px;
          border: 4px solid rgba(255, 255, 255, 0.1);
          border-radius: 50%;
          border-top-color: #60a5fa;
          margin: 0 auto;
          animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        h3 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 20px 0;
          color: white;
        }

        .progress-container {
          background-color: rgba(15, 23, 42, 0.5);
          border-radius: 20px;
          height: 16px;
          overflow: hidden;
          position: relative;
          margin-top: 12px;
        }

        .progress-bar {
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          height: 100%;
          width: 0;
          border-radius: 20px;
          transition: width 0.3s ease;
        }

        .progress-text {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          font-size: 0.75rem;
          font-weight: 600;
          color: white;
          mix-blend-mode: difference;
        }

        .error-icon {
          color: #f87171;
          margin-bottom: 20px;
        }

        .error-message {
          margin-bottom: 20px;
          color: #cbd5e1;
          font-size: 0.875rem;
          line-height: 1.5;
        }

        .retry-button {
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          border: none;
          color: white;
          padding: 8px 20px;
          border-radius: 20px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.875rem;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .retry-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);
        }
      `}</style>
    </div>
  );
};

LoadingScreen.propTypes = {
  isLoading: PropTypes.bool,
  progress: PropTypes.number,
  error: PropTypes.object,
  onRetry: PropTypes.func,
  message: PropTypes.string
};

export default LoadingScreen;
