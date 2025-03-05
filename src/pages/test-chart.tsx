import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import BirthChart from '@/components/charts/BirthChart';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import { ChartData } from '@/types';

// Zodiac signs in order
const SIGNS = [
  'Aries', 'Taurus', 'Gemini', 'Cancer',
  'Leo', 'Virgo', 'Libra', 'Scorpio',
  'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
];

export default function TestChartPage() {
  const [d1ChartData, setD1ChartData] = useState<ChartData | null>(null);
  const [d9ChartData, setD9ChartData] = useState<ChartData | null>(null);
  const [d3ChartData, setD3ChartData] = useState<ChartData | null>(null);
  const [d10ChartData, setD10ChartData] = useState<ChartData | null>(null);
  const [d12ChartData, setD12ChartData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'D1' | 'D3' | 'D9' | 'D10' | 'D12'>('D1');

  // Test birth data
  const testData = {
    birthDate: "1985-10-24T00:00:00",
    birthTime: "14:30",
    latitude: 18.5204,
    longitude: 73.8567,
    timezone: "Asia/Kolkata",
    chartType: "ALL"
  };

  useEffect(() => {
    // Fetch chart data from API
    const fetchChartData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        console.log("Fetching chart data with test data:", testData);

        const response = await fetch('http://localhost:8000/api/chart/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(testData),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          console.error('Error response:', errorData);
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Received chart data:", data);

        // Fix D1 chart data - add missing properties to make it compatible
        if (data.d1Chart) {
          const enhancedD1Chart: ChartData = {
            ...data.d1Chart,
            aspects: data.d1Chart.aspects || [],
            divisionalCharts: {},
            visualization: {
              celestialLayers: [
                {
                  depth: 0.1,
                  content: 'stars',
                  parallaxFactor: 0.1,
                  position: { x: 0, y: 0, z: -300 }
                },
                {
                  depth: 0.2,
                  content: 'nebulae',
                  parallaxFactor: 0.2,
                  position: { x: 0, y: 0, z: -200 }
                }
              ],
              cameraPosition: { x: 0, y: 0, z: 300 },
              lightingSetup: {
                ambient: { color: '#ffffff', intensity: 0.3 },
                directional: [
                  {
                    color: '#ffffff',
                    intensity: 0.7,
                    position: { x: 10, y: 10, z: 10 }
                  }
                ]
              }
            }
          };
          setD1ChartData(enhancedD1Chart);
        }

        // Fix D9 chart data
        if (data.d9Chart) {
          const enhancedD9Chart: ChartData = {
            ...data.d9Chart,
            aspects: data.d9Chart.aspects || [],
            divisionalCharts: {},
            visualization: {
              celestialLayers: [
                {
                  depth: 0.1,
                  content: 'stars',
                  parallaxFactor: 0.1,
                  position: { x: 0, y: 0, z: -300 }
                }
              ],
              cameraPosition: { x: 0, y: 0, z: 300 },
              lightingSetup: {
                ambient: { color: '#f8f0ff', intensity: 0.3 },
                directional: [
                  {
                    color: '#ffe0e0',
                    intensity: 0.7,
                    position: { x: 10, y: 10, z: 10 }
                  }
                ]
              }
            }
          };
          setD9ChartData(enhancedD9Chart);
        }

        // Generate mock data for other charts (D3, D10, D12)
        // This will help us test multi-chart display while waiting for API support
        const generateMockChartData = (baseChart: ChartData, divisionalNumber: number): ChartData => {
          // Use D1 chart data as a base, but shift planet positions based on divisional number
          return {
            ...baseChart,
            planets: baseChart.planets.map(planet => ({
              ...planet,
              // Shift degree based on divisional number to create variety and convert to string
              degree: (((typeof planet.degree === 'number' ? planet.degree :
                        typeof planet.degree === 'string' ? parseFloat(planet.degree) : 0) + 30 * divisionalNumber) % 360).toString(),
              // Vary the house placement
              house: ((planet.house || 1) + divisionalNumber - 1) % 12 + 1
            })),
            ascendant: typeof baseChart.ascendant === 'number' ?
              ((baseChart.ascendant + 30 * divisionalNumber) % 360) :
              {
                sign: SIGNS[(SIGNS.indexOf(baseChart.ascendant?.sign || 'Aries') + divisionalNumber) % 12],
                degree: ((baseChart.ascendant?.degree || 0) + 30 * divisionalNumber) % 360,
                description: baseChart.ascendant?.description
              },
          };
        };

        // If we have D1 data, generate mock data for other charts
        if (d1ChartData) {
          setD3ChartData(generateMockChartData(d1ChartData, 3));
          setD10ChartData(generateMockChartData(d1ChartData, 10));
          setD12ChartData(generateMockChartData(d1ChartData, 12));
        }
      } catch (err) {
        console.error('Error fetching chart data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load chart data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchChartData();
  }, []);

  const handlePlanetClick = (planetId: string) => {
    alert(`Clicked on planet: ${planetId}`);
  };

  return (
    <div className="min-h-screen bg-gray-900">
      <Head>
        <title>Birth Chart Visualization Test</title>
        <meta name="description" content="Testing chart visualization with test data" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <h1 className="text-3xl font-bold text-center mb-8 text-white">
          Birth Chart Visualization Test
        </h1>

        <div className="mb-6 p-4 bg-white/10 backdrop-blur-sm rounded-lg text-white">
          <h2 className="text-xl font-semibold mb-2">Test Data</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p><span className="font-medium">Birth Date:</span> 24/10/1985</p>
              <p><span className="font-medium">Birth Time:</span> 02:30 PM</p>
            </div>
            <div>
              <p><span className="font-medium">Birth Place:</span> Pune, India</p>
              <p><span className="font-medium">Latitude:</span> 18.5204°</p>
            </div>
            <div>
              <p><span className="font-medium">Longitude:</span> 73.8567°</p>
              <p><span className="font-medium">Timezone:</span> Asia/Kolkata</p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            <p className="font-medium">Error loading chart data:</p>
            <p>{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-white"></div>
          </div>
        ) : (
          <>
            {/* Chart Type Tabs */}
            <div className="flex mb-4 space-x-2">
              <button
                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                  activeTab === 'D1'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-700 text-white hover:bg-gray-600'
                }`}
                onClick={() => setActiveTab('D1')}
              >
                D1 Chart (Birth Chart)
              </button>
              <button
                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                  activeTab === 'D3'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-700 text-white hover:bg-gray-600'
                }`}
                onClick={() => setActiveTab('D3')}
              >
                D3 Chart (Drekkana)
              </button>
              <button
                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                  activeTab === 'D9'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-700 text-white hover:bg-gray-600'
                }`}
                onClick={() => setActiveTab('D9')}
              >
                D9 Chart (Navamsa)
              </button>
              <button
                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                  activeTab === 'D10'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-700 text-white hover:bg-gray-600'
                }`}
                onClick={() => setActiveTab('D10')}
              >
                D10 Chart (Dashamsha)
              </button>
              <button
                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                  activeTab === 'D12'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-700 text-white hover:bg-gray-600'
                }`}
                onClick={() => setActiveTab('D12')}
              >
                D12 Chart (Dwadashamsha)
              </button>
            </div>

            {/* Chart Visualization */}
            <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4">
              {activeTab === 'D1' && d1ChartData ? (
                <div>
                  <h2 className="text-xl font-semibold mb-4">D1 Chart (Birth Chart)</h2>
                  <div className="h-[600px] w-full">
                    <BirthChart
                      data={d1ChartData}
                      width={800}
                      height={800}
                      onPlanetClick={handlePlanetClick}
                    />
                  </div>
                </div>
              ) : activeTab === 'D3' && d3ChartData ? (
                <div>
                  <h2 className="text-xl font-semibold mb-4">D3 Chart (Drekkana)</h2>
                  <div className="h-[600px] w-full">
                    <BirthChart
                      data={d3ChartData}
                      width={800}
                      height={800}
                      onPlanetClick={handlePlanetClick}
                    />
                  </div>
                </div>
              ) : activeTab === 'D9' && d9ChartData ? (
                <div>
                  <h2 className="text-xl font-semibold mb-4">D9 Chart (Navamsa)</h2>
                  <div className="h-[600px] w-full">
                    <BirthChart
                      data={d9ChartData}
                      width={800}
                      height={800}
                      onPlanetClick={handlePlanetClick}
                    />
                  </div>
                </div>
              ) : activeTab === 'D10' && d10ChartData ? (
                <div>
                  <h2 className="text-xl font-semibold mb-4">D10 Chart (Dashamsha)</h2>
                  <div className="h-[600px] w-full">
                    <BirthChart
                      data={d10ChartData}
                      width={800}
                      height={800}
                      onPlanetClick={handlePlanetClick}
                    />
                  </div>
                </div>
              ) : activeTab === 'D12' && d12ChartData ? (
                <div>
                  <h2 className="text-xl font-semibold mb-4">D12 Chart (Dwadashamsha)</h2>
                  <div className="h-[600px] w-full">
                    <BirthChart
                      data={d12ChartData}
                      width={800}
                      height={800}
                      onPlanetClick={handlePlanetClick}
                    />
                  </div>
                </div>
              ) : (
                <div className="text-center p-8 text-gray-500">
                  <p>No chart data available for the selected chart type.</p>
                </div>
              )}
            </div>

            {/* Planetary Positions Table */}
            <div className="mt-8 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4">
              <h2 className="text-xl font-semibold mb-4">
                {activeTab === 'D1' ? 'D1 Chart' : activeTab === 'D3' ? 'D3 Chart' : activeTab === 'D9' ? 'D9 Chart' : activeTab === 'D10' ? 'D10 Chart' : 'D12 Chart'} - Planetary Positions
              </h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Planet</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sign</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Degree</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">House</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {(activeTab === 'D1' ? d1ChartData?.planets : activeTab === 'D3' ? d3ChartData?.planets : activeTab === 'D9' ? d9ChartData?.planets : activeTab === 'D10' ? d10ChartData?.planets : d12ChartData?.planets)?.map((planet) => (
                      <tr key={planet.name}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{planet.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{planet.sign}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{planet.degree}°</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">House {planet.house}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {planet.retrograde ? (
                            <span className="px-2 py-1 text-xs font-medium bg-amber-100 text-amber-800 rounded-full">
                              Retrograde
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                              Direct
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
