import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';

const ChartResult = () => {
  const router = useRouter();
  const { chartId } = router.query;
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Skip if chartId is not available yet
    if (!chartId) return;

    try {
      // Attempt to retrieve the chart data from sessionStorage
      const storedData = sessionStorage.getItem('chartData');

      if (storedData) {
        const data = JSON.parse(storedData);
        setChartData(data);
      } else {
        // In a real implementation, this would fetch from the API using the chartId
        // Mock data for now
        setChartData({
          chart_id: chartId,
          birth_details: {
            name: 'Test User',
            date: '1990-06-15',
            time: '14:30',
            location: 'New York, USA'
          },
          rectified_time: '14:23',
          confidence_score: 87,
          explanation: 'Based on planetary positions and life events, we determined the rectified birth time.'
        });
      }
    } catch (err) {
      console.error('Error retrieving chart data:', err);
      setError('Failed to load chart data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [chartId]);

  if (loading) {
    return (
      <div className="cosmic-scene">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading your astrological chart...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cosmic-scene">
        <div className="error-container">
          <h2>Error Loading Chart</h2>
          <p>{error}</p>
          <button
            onClick={() => router.push('/birth-time-analysis')}
            className="retry-button">
            Return to Form
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="cosmic-scene">
      <Head>
        <title>Chart Results | Birth Time Rectifier</title>
        <meta name="description" content="Your astrological chart with birth time rectification results" />
      </Head>

      {/* Navigation Header */}
      <header className="cosmic-header">
        <div className="logo">
          <Link href="/">
            <span className="logo-text">Birth Time Rectifier</span>
          </Link>
        </div>
        <nav>
          <Link href="/">
            <span className="nav-link">Home</span>
          </Link>
          <Link href="/birth-time-analysis">
            <span className="nav-link">New Analysis</span>
          </Link>
        </nav>
      </header>

      <div className="chart-container">
        <h1>Your Astrological Chart</h1>

        <div className="chart-details">
          <div className="chart-visualization" data-testid="chart-visualization">
            <div className="chart-svg" data-testid="chart-svg">
              {/* Placeholder for actual chart visualization */}
              <div className="mock-chart">
                <div className="mock-planets">
                  <div className="planet" data-testid="planet-sun"></div>
                  <div className="planet" data-testid="planet-moon"></div>
                  <div className="planet" data-testid="planet-mercury"></div>
                  <div className="planet" data-testid="planet-venus"></div>
                  <div className="planet" data-testid="planet-mars"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="chart-info">
            <div className="birth-details">
              <h2>Birth Details</h2>
              <p><strong>Name:</strong> {chartData?.birth_details?.name}</p>
              <p><strong>Date:</strong> {chartData?.birth_details?.date}</p>
              <p><strong>Original Birth Time:</strong> {chartData?.birth_details?.time}</p>
              <p><strong>Location:</strong> {chartData?.birth_details?.location}</p>
            </div>

            <div className="rectification-details">
              <h2>Rectification Results</h2>
              <p><strong>Rectified Birth Time:</strong> {chartData?.rectified_time}</p>
              <div className="confidence-score">
                <span>Confidence Score: </span>
                <span data-testid="confidence-score">{chartData?.confidence_score}%</span>
              </div>
              <div className="explanation">
                <h3>Explanation</h3>
                <p>{chartData?.explanation}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="chart-actions">
          <button className="btn-primary" data-testid="export-pdf">
            Export Chart
          </button>
          <Link href="/birth-time-analysis">
            <button className="btn-secondary">New Analysis</button>
          </Link>
        </div>
      </div>

      <style jsx>{`
        .cosmic-scene {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          background-color: #000000;
          background-image: radial-gradient(circle at 10% 20%, #0f172a 0%, #020617 100%);
          color: white;
        }

        .cosmic-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(10px);
          position: relative;
          z-index: 10;
        }

        .logo-text {
          font-size: 1.5rem;
          font-weight: bold;
          background: linear-gradient(90deg, #60a5fa, #a78bfa);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          cursor: pointer;
        }

        nav {
          display: flex;
          gap: 20px;
        }

        .nav-link {
          color: #a5b4fc;
          transition: color 0.3s ease;
          cursor: pointer;
        }

        .nav-link:hover {
          color: #60a5fa;
        }

        .loading-container, .error-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 80vh;
          text-align: center;
          padding: 20px;
        }

        .loading-spinner {
          border: 4px solid rgba(255, 255, 255, 0.1);
          border-left-color: #60a5fa;
          border-radius: 50%;
          width: 50px;
          height: 50px;
          animation: spin 1s linear infinite;
          margin-bottom: 20px;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .error-container h2 {
          color: #ef4444;
          margin-bottom: 10px;
        }

        .retry-button {
          margin-top: 20px;
          padding: 10px 20px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 5px;
          cursor: pointer;
          transition: background 0.3s;
        }

        .retry-button:hover {
          background: #2563eb;
        }

        .chart-container {
          max-width: 1200px;
          margin: 40px auto;
          padding: 30px;
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }

        h1 {
          font-size: 2.5rem;
          text-align: center;
          margin-bottom: 30px;
          background: linear-gradient(90deg, #60a5fa, #a78bfa);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        }

        .chart-details {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 30px;
        }

        .chart-visualization {
          background: rgba(15, 23, 42, 0.5);
          border-radius: 12px;
          padding: 20px;
          aspect-ratio: 1;
          display: flex;
          justify-content: center;
          align-items: center;
          border: 1px solid rgba(96, 165, 250, 0.2);
        }

        .mock-chart {
          width: 100%;
          height: 100%;
          position: relative;
          border-radius: 50%;
          background: radial-gradient(circle, #0a143b 0%, #050a20 100%);
          display: flex;
          justify-content: center;
          align-items: center;
          box-shadow: 0 0 30px rgba(96, 165, 250, 0.2);
          overflow: hidden;
        }

        .mock-planets {
          position: relative;
          width: 80%;
          height: 80%;
          border: 1px dashed rgba(165, 180, 252, 0.3);
          border-radius: 50%;
        }

        .planet {
          position: absolute;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: white;
          box-shadow: 0 0 10px white;
        }

        [data-testid="planet-sun"] {
          background: orange;
          box-shadow: 0 0 15px orange;
          top: 20%;
          left: 80%;
        }

        [data-testid="planet-moon"] {
          background: silver;
          box-shadow: 0 0 10px silver;
          top: 70%;
          left: 20%;
        }

        [data-testid="planet-mercury"] {
          background: #b5b5b5;
          box-shadow: 0 0 8px #b5b5b5;
          top: 40%;
          left: 30%;
        }

        [data-testid="planet-venus"] {
          background: #e6c8a0;
          box-shadow: 0 0 12px #e6c8a0;
          top: 30%;
          left: 60%;
        }

        [data-testid="planet-mars"] {
          background: #e8684a;
          box-shadow: 0 0 10px #e8684a;
          top: 60%;
          left: 70%;
        }

        .chart-info {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .birth-details, .rectification-details {
          background: rgba(15, 23, 42, 0.5);
          border-radius: 12px;
          padding: 20px;
          border: 1px solid rgba(96, 165, 250, 0.2);
        }

        h2 {
          font-size: 1.8rem;
          margin-bottom: 15px;
          color: #a5b4fc;
        }

        h3 {
          font-size: 1.4rem;
          margin: 15px 0 10px;
          color: #a5b4fc;
        }

        p {
          margin-bottom: 10px;
          line-height: 1.6;
        }

        .confidence-score {
          display: flex;
          align-items: center;
          margin: 15px 0;
          font-size: 1.2rem;
        }

        .confidence-score span:last-child {
          color: #34d399;
          font-weight: bold;
          margin-left: 5px;
        }

        .chart-actions {
          display: flex;
          justify-content: center;
          gap: 20px;
          margin-top: 40px;
        }

        .btn-primary, .btn-secondary {
          padding: 12px 24px;
          border-radius: 6px;
          font-weight: bold;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn-primary {
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          color: white;
          border: none;
          box-shadow: 0 4px 6px rgba(59, 130, 246, 0.5);
        }

        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 8px rgba(59, 130, 246, 0.6);
        }

        .btn-secondary {
          background: transparent;
          color: #a5b4fc;
          border: 1px solid #a5b4fc;
        }

        .btn-secondary:hover {
          background: rgba(165, 180, 252, 0.1);
          transform: translateY(-2px);
        }

        .entity-details {
          position: absolute;
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid #60a5fa;
          color: white;
          padding: 10px;
          border-radius: 6px;
          z-index: 20;
          pointer-events: none;
          transition: opacity 0.3s;
        }

        .export-success {
          position: fixed;
          bottom: 20px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(52, 211, 153, 0.9);
          color: white;
          padding: 10px 20px;
          border-radius: 4px;
          animation: fadeIn 0.3s ease-out, fadeOut 0.3s ease-in 2.7s forwards;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateX(-50%) translateY(20px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }

        @keyframes fadeOut {
          from { opacity: 1; transform: translateX(-50%) translateY(0); }
          to { opacity: 0; transform: translateX(-50%) translateY(20px); }
        }

        /* Responsive styles */
        @media (max-width: 1024px) {
          .chart-container {
            padding: 20px;
            margin: 20px;
          }
        }

        @media (max-width: 768px) {
          .chart-details {
            grid-template-columns: 1fr;
          }

          h1 {
            font-size: 2rem;
          }

          .chart-actions {
            flex-direction: column;
            align-items: center;
          }

          .btn-primary, .btn-secondary {
            width: 100%;
            max-width: 300px;
          }
        }
      `}</style>
    </div>
  );
};

export default ChartResult;
