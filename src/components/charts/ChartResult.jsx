import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

// Components
import LoadingIndicator from '../ui/LoadingIndicator';
import ErrorMessage from '../ui/ErrorMessage';
import RetryButton from '../ui/RetryButton';
import CelestialCanvas from '../three-scene/CelestialCanvas';

/**
 * Chart result page with robust error handling and loading states
 * Shows the birth time rectification results and chart visualization
 */
const ChartResult = ({ chartId }) => {
  // State
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  // Router for navigation
  const router = useRouter();

  // Subscribe to API progress events for visual feedback
  useEffect(() => {
    // Set up event listener for API progress
    const handleApiProgress = (event) => {
      if (event.detail && event.detail.percent) {
        setLoadingProgress(event.detail.percent);
      }
    };

    window.addEventListener('apiProgress', handleApiProgress);

    return () => {
      window.removeEventListener('apiProgress', handleApiProgress);
    };
  }, []);

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
    setIsRetrying(false);

    // Function to fetch chart data
    const fetchChartData = async () => {
      try {
        // Artificial progress indicator (since the actual API might not provide progress)
        const progressInterval = setInterval(() => {
          if (isMounted) {
            setLoadingProgress(prev => {
              // Cap at 95% until actual data arrives
              return Math.min(prev + (100 - prev) * 0.1, 95);
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

          // Store successful result in localStorage for recovery
          localStorage.setItem(`chart_data_${chartId}`, JSON.stringify(response.data));
        }
      } catch (err) {
        console.error('Error fetching chart data:', err);

        // Try to recover from localStorage if available
        const cachedData = localStorage.getItem(`chart_data_${chartId}`);
        if (cachedData) {
          try {
            const parsedData = JSON.parse(cachedData);
            if (isMounted) {
              setChartData(parsedData);
              setLoadingProgress(100);
              setLoading(false);
              setError({
                message: 'Using cached data. Some information may be outdated.',
                type: 'warning'
              });
            }
            clearInterval(progressInterval);
            return;
          } catch (cacheError) {
            console.error('Error parsing cached data:', cacheError);
            // Continue with normal error handling
          }
        }

        // Clear the progress interval
        clearInterval(progressInterval);

        // Set error message
        if (isMounted) {
          if (err.code === 'ECONNABORTED') {
            setError({
              message: 'Request timed out. The server may be busy, please try again.',
              type: 'error'
            });
          } else {
            setError({
              message: err.response?.data?.message ||
                      err.message ||
                      'Failed to load chart data. Please try again.',
              type: 'error'
            });
          }
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
  }, [chartId, isRetrying]);

  // Handle retry
  const handleRetry = () => {
    setIsRetrying(true);
  };

  // Format time for display
  const formatTime = (timeString) => {
    if (!timeString) return 'Unknown';
    try {
      const [hours, minutes] = timeString.split(':');
      const hour = parseInt(hours, 10);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const hour12 = hour % 12 || 12;
      return `${hour12}:${minutes} ${ampm}`;
    } catch (e) {
      return timeString;
    }
  };

  // Render loading state
  if (loading) {
    return (
      <div className="chart-result-container loading">
        <div className="cosmic-background">
          <CelestialCanvas />
        </div>
        <div className="loading-overlay">
          <LoadingIndicator size="large" message="Generating astrological chart..." />
          <div className="progress-container">
            <div className="progress-bar">
              <div
                className="progress-bar-inner"
                style={{ width: `${loadingProgress}%` }}
              ></div>
            </div>
            <p className="progress-text">{Math.round(loadingProgress)}% complete</p>
          </div>
        </div>
      </div>
    );
  }

  // Render error state
  if (error && !chartData) {
    return (
      <div className="chart-result-container error">
        <div className="cosmic-background">
          <CelestialCanvas />
        </div>
        <div className="error-overlay">
          <ErrorMessage message={error.message} type={error.type || 'error'} />
          <div className="error-actions">
            <RetryButton onClick={handleRetry} text="Try Again" />
            <button
              className="btn-secondary"
              onClick={() => router.push('/')}
            >
              Return to Form
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render chart data
  return (
    <div className="chart-result-container">
      <div className="cosmic-background">
        <CelestialCanvas />
      </div>

      {error && (
        <div className="warning-banner">
          <ErrorMessage
            message={error.message}
            type={error.type || 'warning'}
            autoHideAfter={10000}
          />
        </div>
      )}

      <div className="chart-content">
        <h1>Your Astrological Chart</h1>

        {chartData && (
          <>
            <div className="chart-visualization-container">
              {/* Chart visualization could be rendered here if we had a ChartVisualization component */}
              <div className="placeholder-visualization">
                <div className="chart-image-container">
                  {chartData.chart_image_url ? (
                    <img
                      src={chartData.chart_image_url}
                      alt="Astrological Chart"
                      className="chart-image"
                    />
                  ) : (
                    <div className="chart-placeholder">
                      <span>Chart Image Not Available</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="rectification-details">
              <h2>Birth Time Rectification Results</h2>

              <div className="result-cards">
                <div className="result-card">
                  <h3>Original Birth Time</h3>
                  <div className="time-display">{formatTime(chartData.birth_details?.time || chartData.original_time)}</div>
                  <p className="time-note">As provided by you</p>
                </div>

                <div className="result-card highlight">
                  <h3>Rectified Birth Time</h3>
                  <div className="time-display">{formatTime(chartData.rectified_time)}</div>
                  <div className="confidence-score">
                    <span>Confidence: </span>
                    <div className="score-bar">
                      <div
                        className="score-fill"
                        style={{width: `${chartData.confidence_score || 0}%`}}
                      ></div>
                    </div>
                    <span>{chartData.confidence_score || 0}%</span>
                  </div>
                </div>
              </div>

              <div className="explanation-section">
                <h3>Analysis Explanation</h3>
                <div className="explanation-content">
                  <p>{chartData.explanation || 'No explanation provided.'}</p>
                </div>
              </div>
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

      <style jsx>{`
        .chart-result-container {
          position: relative;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }

        .cosmic-background {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: -1;
        }

        .loading-overlay, .error-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          background: rgba(0, 0, 0, 0.7);
          z-index: 10;
          padding: 20px;
        }

        .progress-container {
          margin-top: 30px;
          width: 80%;
          max-width: 400px;
        }

        .progress-bar {
          height: 6px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
          overflow: hidden;
          margin-bottom: 10px;
        }

        .progress-bar-inner {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          border-radius: 3px;
          transition: width 0.3s ease;
        }

        .progress-text {
          text-align: center;
          color: rgba(255, 255, 255, 0.8);
          font-size: 14px;
        }

        .error-actions {
          display: flex;
          gap: 15px;
          margin-top: 30px;
        }

        .chart-content {
          padding: 40px 20px;
          max-width: 1000px;
          margin: 0 auto;
          width: 100%;
          color: white;
          position: relative;
          z-index: 1;
        }

        h1 {
          font-size: 2.5rem;
          text-align: center;
          margin-bottom: 40px;
          background: linear-gradient(90deg, #60a5fa, #a78bfa, #60a5fa);
          background-size: 200% auto;
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        }

        h2 {
          font-size: 1.8rem;
          color: #bfdbfe;
          margin-bottom: 30px;
          text-align: center;
        }

        h3 {
          font-size: 1.2rem;
          color: #93c5fd;
          margin-bottom: 15px;
        }

        .chart-visualization-container {
          background: rgba(15, 23, 42, 0.7);
          backdrop-filter: blur(10px);
          border-radius: 15px;
          padding: 30px;
          margin-bottom: 40px;
          border: 1px solid rgba(96, 165, 250, 0.2);
        }

        .placeholder-visualization {
          width: 100%;
          aspect-ratio: 4/3;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
        }

        .chart-image-container {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .chart-image {
          max-width: 100%;
          max-height: 100%;
          object-fit: contain;
        }

        .chart-placeholder {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(15, 23, 42, 0.5);
          color: #93c5fd;
          border: 1px dashed rgba(96, 165, 250, 0.4);
          border-radius: 10px;
        }

        .rectification-details {
          background: rgba(15, 23, 42, 0.7);
          backdrop-filter: blur(10px);
          border-radius: 15px;
          padding: 30px;
          margin-bottom: 40px;
          border: 1px solid rgba(96, 165, 250, 0.2);
        }

        .result-cards {
          display: flex;
          gap: 30px;
          margin-bottom: 30px;
          flex-wrap: wrap;
        }

        .result-card {
          flex: 1;
          min-width: 250px;
          background: rgba(30, 41, 59, 0.5);
          padding: 20px;
          border-radius: 10px;
          text-align: center;
          display: flex;
          flex-direction: column;
          border: 1px solid rgba(96, 165, 250, 0.1);
        }

        .result-card.highlight {
          background: rgba(37, 48, 78, 0.7);
          border: 1px solid rgba(96, 165, 250, 0.3);
          box-shadow: 0 0 20px rgba(96, 165, 250, 0.1);
        }

        .time-display {
          font-size: 2.5rem;
          font-weight: bold;
          color: white;
          margin: 15px 0;
        }

        .time-note {
          font-size: 0.9rem;
          color: #94a3b8;
          margin-top: auto;
        }

        .confidence-score {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 15px;
          flex-wrap: wrap;
          justify-content: center;
        }

        .score-bar {
          flex: 1;
          height: 8px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 4px;
          overflow: hidden;
          position: relative;
          min-width: 100px;
          max-width: 200px;
        }

        .score-fill {
          position: absolute;
          height: 100%;
          left: 0;
          top: 0;
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          border-radius: 4px;
        }

        .explanation-section {
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid rgba(96, 165, 250, 0.2);
        }

        .explanation-content {
          background: rgba(30, 41, 59, 0.5);
          padding: 20px;
          border-radius: 10px;
          color: #e2e8f0;
          line-height: 1.6;
        }

        .chart-actions {
          display: flex;
          gap: 20px;
          margin-top: 40px;
          justify-content: center;
        }

        .btn-primary, .btn-secondary {
          padding: 12px 24px;
          border-radius: 30px;
          font-size: 1rem;
          font-weight: bold;
          border: none;
          cursor: pointer;
          transition: all 0.3s ease;
          min-width: 180px;
        }

        .btn-primary {
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          color: white;
          box-shadow: 0 4px 15px rgba(59, 130, 246, 0.5);
        }

        .btn-primary:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 25px rgba(59, 130, 246, 0.6);
        }

        .btn-secondary {
          background: rgba(15, 23, 42, 0.6);
          color: #a5b4fc;
          border: 1px solid rgba(96, 165, 250, 0.3);
          backdrop-filter: blur(10px);
        }

        .btn-secondary:hover {
          background: rgba(30, 41, 59, 0.8);
          transform: translateY(-3px);
          box-shadow: 0 4px 15px rgba(96, 165, 250, 0.3);
          color: #bfdbfe;
        }

        .warning-banner {
          position: fixed;
          top: 20px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 100;
          width: 90%;
          max-width: 600px;
        }

        /* Responsive design */
        @media (max-width: 768px) {
          h1 {
            font-size: 2rem;
          }

          h2 {
            font-size: 1.5rem;
          }

          .result-cards {
            flex-direction: column;
            gap: 20px;
          }

          .chart-actions {
            flex-direction: column;
            align-items: center;
          }

          .btn-primary, .btn-secondary {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
};

export default ChartResult;
