import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ChartVisualization from '../../components/charts/ChartVisualization';
import NorthIndianChart from '../../components/charts/NorthIndianChart';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import PlanetSystem from '../../components/three-scene/PlanetSystem';
import CelestialCanvas from '../../components/three-scene/CelestialCanvas';

/**
 * Chart result page for displaying birth time rectification results
 * This component is optimized for test reliability with clear test attributes
 * Enhanced with advanced visualizations for production environment
 */
const ChartPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [renderMode, setRenderMode] = useState('standard');
  const [showEffects, setShowEffects] = useState(false);
  const [isComparisonMode, setIsComparisonMode] = useState(false);
  const [activeView, setActiveView] = useState('2d'); // '2d', '3d', or 'table'
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch chart data from API
  useEffect(() => {
    if (!id) return;

    const fetchChartData = async () => {
      try {
        setIsLoading(true);
        // Make API call to fetch chart data
        const response = await fetch(`/api/chart/${id}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch chart data: ${response.statusText}`);
        }

        const data = await response.json();
        setChartData(data);
        setIsLoading(false);
      } catch (err) {
        console.error('Error fetching chart data:', err);
        setError(err.message);
        setIsLoading(false);

        // For testing/demo purposes, use mock data if API fails
        setChartData(getMockChartData(id));
      }
    };

    fetchChartData();
  }, [id]);

  // Mock chart data with planetary data for visualization
  const getMockChartData = (chartId) => {
    return {
      chart_id: chartId || 'test-123',
      birth_details: {
        date: '1985-10-24',
        time: '14:30',
        location: 'Pune, Maharashtra',
        latitude: 18.5204,
        longitude: 73.8567,
        timezone: 'Asia/Kolkata'
      },
      rectified_time: '14:33',
      confidence_score: 85,
      explanation: 'Birth time rectification based on planetary positions and life events analysis.',
      planets: [
        { id: 'sun', name: 'Sun', sign: 'Libra', degree: 28.25, house: 2, longitude: 208.25 },
        { id: 'moon', name: 'Moon', sign: 'Taurus', degree: 15.48, house: 9, longitude: 45.48 },
        { id: 'mercury', name: 'Mercury', sign: 'Scorpio', degree: 5.22, house: 3, longitude: 215.22 },
        { id: 'venus', name: 'Venus', sign: 'Virgo', degree: 22.15, house: 1, longitude: 172.15 },
        { id: 'mars', name: 'Mars', sign: 'Capricorn', degree: 10.08, house: 5, longitude: 280.08 },
        { id: 'jupiter', name: 'Jupiter', sign: 'Aquarius', degree: 8.34, house: 6, longitude: 308.34 },
        { id: 'saturn', name: 'Saturn', sign: 'Scorpio', degree: 18.52, house: 3, longitude: 228.52 },
        { id: 'rahu', name: 'Rahu', sign: 'Virgo', degree: 28.15, house: 1, longitude: 178.15 },
        { id: 'ketu', name: 'Ketu', sign: 'Pisces', degree: 2.15, house: 7, longitude: 332.15 }
      ],
      ascendant: {
        sign: 'Virgo',
        degree: 18.75,
        longitude: 168.75
      },
      houses: Array.from({ length: 12 }, (_, i) => ({
        number: i + 1,
        sign: ['Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius',
               'Pisces', 'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo'][i],
        degree: (i * 30 + 15) % 30,
        cusp: i * 30
      }))
    };
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mx-auto"></div>
          <p className="mt-4 text-white">Loading chart data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-900">
        <div className="text-center text-red-500 p-4 border border-red-700 rounded-lg">
          <h2 className="text-xl font-bold">Error</h2>
          <p>{error}</p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Return Home
          </button>
        </div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-900">
        <div className="text-center text-white">
          <p>No chart data available</p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Return Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 py-8 px-4">
      <div className="container mx-auto">
        {/* Header with birth details and rectification info */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white mb-4" data-testid="chart-title">
            Birth Chart
          </h1>
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h2 className="text-xl text-indigo-400 mb-2">Birth Details</h2>
                <p className="text-white"><span className="text-gray-400">Date:</span> {chartData.birth_details.date}</p>
                <p className="text-white"><span className="text-gray-400">Original Time:</span> {chartData.birth_details.time}</p>
                <p className="text-white"><span className="text-gray-400">Location:</span> {chartData.birth_details.location}</p>
              </div>
              {chartData.rectified_time && (
                <div>
                  <h2 className="text-xl text-indigo-400 mb-2">Rectification</h2>
                  <p className="text-white"><span className="text-gray-400">Rectified Time:</span> {chartData.rectified_time}</p>
                  <p className="text-white"><span className="text-gray-400">Confidence:</span> {chartData.confidence_score}%</p>
                  <div className="mt-1 bg-gray-700 rounded-full h-2.5">
                    <div
                      className="bg-indigo-600 h-2.5 rounded-full"
                      style={{ width: `${chartData.confidence_score}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Visualization mode selector */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              type="button"
              onClick={() => setActiveView('2d')}
              className={`px-4 py-2 text-sm font-medium rounded-l-lg ${
                activeView === '2d'
                ? 'bg-indigo-700 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
              data-testid="2d-view-button"
            >
              Vedic Chart (2D)
            </button>
            <button
              type="button"
              onClick={() => setActiveView('3d')}
              className={`px-4 py-2 text-sm font-medium ${
                activeView === '3d'
                ? 'bg-indigo-700 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
              data-testid="3d-view-button"
            >
              Planetary 3D View
            </button>
            <button
              type="button"
              onClick={() => setActiveView('table')}
              className={`px-4 py-2 text-sm font-medium rounded-r-lg ${
                activeView === 'table'
                ? 'bg-indigo-700 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
              data-testid="table-view-button"
            >
              Planetary Positions
            </button>
          </div>
        </div>

        {/* Chart visualization based on selected view */}
        <div className="bg-gray-800 rounded-lg p-4">
          {activeView === '2d' && (
            <div data-testid="north-indian-chart" className="p-4">
              <NorthIndianChart chartData={chartData} className="mx-auto" />
            </div>
          )}

          {activeView === '3d' && (
            <div data-testid="3d-visualization" className="h-96">
              <CelestialCanvas
                enableRotation={true}
                backgroundColor={0x000011}
                particleCount={500}
                fallbackContent={
                  <div className="flex justify-center items-center h-full">
                    <p className="text-white text-center">3D visualization not available in this browser.<br />Please try another browser or switch to the 2D view.</p>
                  </div>
                }
              >
                <PlanetSystem
                  planets={chartData.planets.map(p => ({
                    name: p.name,
                    sign: p.sign,
                    position: [Math.cos(p.longitude * Math.PI/180) * 5, 0, Math.sin(p.longitude * Math.PI/180) * 5],
                    rotation: [0, p.longitude * Math.PI/180, 0],
                    size: p.name === 'Sun' ? 1 : p.name === 'Moon' ? 0.7 : 0.5
                  }))}
                  showEffects={showEffects}
                  quality={renderMode === 'high' ? 'high' : 'medium'}
                />
              </CelestialCanvas>
            </div>
          )}

          {activeView === 'table' && (
            <div data-testid="planetary-table" className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Planet</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Sign</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Degree</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">House</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-gray-800 divide-y divide-gray-700">
                  {chartData.planets.map((planet) => (
                    <tr key={planet.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white">{planet.name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white">{planet.sign}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white">{`${Math.floor(planet.degree)}° ${Math.round((planet.degree % 1) * 60)}'`}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white">{planet.house}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                        {planet.isRetrograde ? 'Retrograde' : 'Direct'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Explanation section */}
        {chartData.explanation && (
          <div className="mt-8 bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl text-indigo-400 mb-4">Rectification Explanation</h2>
            <p className="text-white">{chartData.explanation}</p>
          </div>
        )}

        {/* Actions section */}
        <div className="mt-8 flex justify-center space-x-4">
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
            data-testid="back-button"
          >
            Back Home
          </button>
          <button
            onClick={() => window.print()}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            data-testid="export-button"
          >
            Export Chart
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChartPage;
