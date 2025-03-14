import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

// Components
import LoadingIndicator from '../ui/LoadingIndicator';
import ErrorMessage from '../ui/ErrorMessage';
import RetryButton from '../ui/RetryButton';
import CelestialCanvas from '../three-scene/CelestialCanvas';
import ChartVerification from './ChartVerification';

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
  const [showVerification, setShowVerification] = useState(false);

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

    const fetchChartData = async () => {
      try {
        // Simulate progress for better UX
        const progressInterval = setInterval(() => {
          setLoadingProgress(prev => Math.min(prev + 5, 90));
        }, 300);

        // Fetch chart data from API
        const response = await axios.get(`/api/chart/${chartId}`, {
          cancelToken: source.token,
          timeout: 30000, // 30 second timeout
        });

        clearInterval(progressInterval);

        // Update state if component is still mounted
        if (isMounted) {
          setChartData(response.data);
          setLoading(false);
          setLoadingProgress(100);

          // Show verification panel if verification data exists
          if (response.data?.verification) {
            setShowVerification(true);
          }
        }
      } catch (err) {
        clearInterval(progressInterval);

        // Only update state if component is still mounted
        if (isMounted) {
          console.error('Error fetching chart data:', err);
          setError(err.response?.data?.message || 'Failed to load chart data');
          setLoading(false);
        }
      }
    };

    fetchChartData();

    // Cleanup function
    return () => {
      isMounted = false;
      source.cancel('Component unmounted');
    };
  }, [chartId, isRetrying]);

  // Handle retry button click
  const handleRetry = () => {
    setIsRetrying(prev => !prev);
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

  // Show loading state
  if (loading) {
    return (
      <div className="chart-result-container p-6 flex flex-col items-center justify-center min-h-[400px]">
        <LoadingIndicator progress={loadingProgress} />
        <p className="mt-4 text-gray-600">Loading chart data...</p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="chart-result-container p-6">
        <ErrorMessage message={error} />
        <RetryButton onClick={handleRetry} />
      </div>
    );
  }

  // Show empty state
  if (!chartData) {
    return (
      <div className="chart-result-container p-6">
        <p className="text-gray-600">No chart data available.</p>
      </div>
    );
  }

  // Extract data for display
  const {
    birth_details = {},
    chart_data = {},
    verification = null
  } = chartData;

  return (
    <div className="chart-result-container p-4 md:p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Birth Chart</h2>
        <div className="text-gray-600">
          <p>
            <span className="font-medium">Name:</span> {birth_details.full_name || 'Not provided'}
          </p>
          <p>
            <span className="font-medium">Date:</span> {birth_details.birth_date || 'Unknown'}
          </p>
          <p>
            <span className="font-medium">Time:</span> {formatTime(birth_details.birth_time)}
          </p>
          <p>
            <span className="font-medium">Location:</span> {birth_details.location || 'Unknown'}
          </p>
        </div>
      </div>

      {/* Chart Visualization */}
      <div className="mb-8">
        <div className="chart-visualization-container bg-gray-50 rounded-lg p-4 mb-4">
          {chart_data.planets && (
            <CelestialCanvas
              chartData={chart_data}
              width={800}
              height={600}
              renderMode="enhanced"
              showEffects={true}
            />
          )}
        </div>
      </div>

      {/* Verification Results */}
      {showVerification && verification && (
        <div className="mb-8">
          <ChartVerification verification={verification} className="bg-white" />
        </div>
      )}

      {/* Planetary Positions */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4">Planetary Positions</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200 rounded-lg">
            <thead>
              <tr className="bg-gray-100">
                <th className="px-4 py-2 text-left">Planet</th>
                <th className="px-4 py-2 text-left">Sign</th>
                <th className="px-4 py-2 text-left">Degree</th>
                <th className="px-4 py-2 text-left">House</th>
                <th className="px-4 py-2 text-left">Retrograde</th>
              </tr>
            </thead>
            <tbody>
              {chart_data.planets && chart_data.planets.map((planet, index) => (
                <tr key={planet.name || index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-4 py-2 font-medium">{planet.name}</td>
                  <td className="px-4 py-2">{planet.sign}</td>
                  <td className="px-4 py-2">{planet.degree.toFixed(2)}°</td>
                  <td className="px-4 py-2">{planet.house}</td>
                  <td className="px-4 py-2">{planet.is_retrograde ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* House Cusps */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4">House Cusps</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200 rounded-lg">
            <thead>
              <tr className="bg-gray-100">
                <th className="px-4 py-2 text-left">House</th>
                <th className="px-4 py-2 text-left">Sign</th>
                <th className="px-4 py-2 text-left">Degree</th>
              </tr>
            </thead>
            <tbody>
              {chart_data.houses && chart_data.houses.map((house, index) => (
                <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-4 py-2 font-medium">{index + 1}</td>
                  <td className="px-4 py-2">{house.sign}</td>
                  <td className="px-4 py-2">{house.degree.toFixed(2)}°</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-4 mt-8">
        <button
          onClick={() => router.push('/birth-time-rectifier/questionnaire')}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Continue to Questionnaire
        </button>

        <button
          onClick={() => window.print()}
          className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
        >
          Print Chart
        </button>
      </div>
    </div>
  );
};

export default ChartResult;
