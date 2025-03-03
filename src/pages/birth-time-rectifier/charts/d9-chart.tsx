import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import ChartVisualization from '@/components/charts/ChartVisualization';
import { ChartData } from '@/types';
import { RectificationResult } from '@/types';

// Mock chart data interface for our component
interface MockPlanetPosition {
  name: string;
  sign: string;
  degree: number;
  house: number;
  retrograde?: boolean;
  description?: string;
}

interface MockHouseDetails {
  number: number;
  sign: string;
  degree: number;
  planets: string[];
  description?: string;
}

interface MockAspect {
  planet1: string;
  planet2: string;
  aspectType: string;
  orb: number;
  influence: 'positive' | 'negative' | 'neutral';
  description?: string;
}

interface MockChartData {
  ascendant: {
    sign: string;
    degree: number;
    description?: string;
  };
  planets: MockPlanetPosition[];
  houses: MockHouseDetails[];
  aspects: MockAspect[];
}

// Allow for flexible rectification result structure
type FlexibleRectificationResult = RectificationResult & {
  birthDetails: {
    name?: string;
    date?: string;
    place?: string;
    [key: string]: any;
  }
};

export default function D9ChartPage() {
  const router = useRouter();
  const [chartData, setChartData] = useState<MockChartData | null>(null);
  const [formattedChartData, setFormattedChartData] = useState<ChartData | null>(null);
  const [rectificationResult, setRectificationResult] = useState<FlexibleRectificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlanet, setSelectedPlanet] = useState<string | null>(null);

  useEffect(() => {
    // Retrieve rectification result from session storage
    const storedResult = sessionStorage.getItem('rectificationResult');
    if (!storedResult) {
      // Redirect back to analysis if no data found
      router.push('/birth-time-rectifier/analysis');
      return;
    }
    try {
      const parsedResult = JSON.parse(storedResult);
      setRectificationResult(parsedResult);

      if (parsedResult.charts?.d9Chart) {
        setChartData(parsedResult.charts.d9Chart);

        // Select the first planet by default
        if (parsedResult.charts.d9Chart.planets.length > 0) {
          setSelectedPlanet(parsedResult.charts.d9Chart.planets[0].name);
        }
      } else {
        // If no chart data, create mock data
        const mockChart = generateMockChart();
        setChartData(mockChart);

        if (mockChart.planets.length > 0) {
          setSelectedPlanet(mockChart.planets[0].name);
        }
      }
    } catch (e) {
      console.error('Error parsing stored rectification result:', e);
      setError('Failed to load chart data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  // Format the mock chart data to match the ChartData interface
  useEffect(() => {
    if (chartData) {
      const formattedData: ChartData = {
        ascendant: {
          sign: chartData.ascendant.sign,
          degree: chartData.ascendant.degree,
          description: chartData.ascendant.description
        },
        planets: chartData.planets.map(planet => ({
          planet: planet.name,
          sign: planet.sign,
          degree: planet.degree.toString(),
          house: planet.house,
          retrograde: planet.retrograde,
          description: planet.description
        })),
        houses: chartData.houses.map(house => ({
          number: house.number,
          sign: house.sign,
          startDegree: house.degree,
          endDegree: house.degree + 30,
          planets: house.planets.map(planetName => ({
            planet: planetName,
            sign: chartData.planets.find(p => p.name === planetName)?.sign || '',
            degree: chartData.planets.find(p => p.name === planetName)?.degree.toString() || '0',
            house: house.number
          }))
        })),
        aspects: chartData.aspects.map(aspect => ({
          planet1: aspect.planet1,
          planet2: aspect.planet2,
          aspectType: aspect.aspectType,
          orb: aspect.orb,
          influence: aspect.influence,
          description: aspect.description
        })),
        divisionalCharts: {}
      };
      setFormattedChartData(formattedData);
    }
  }, [chartData]);

  const handlePlanetClick = (planetName: string) => {
    setSelectedPlanet(planetName);
  };

  const generateMockChart = (): MockChartData => {
    return {
      ascendant: {
        sign: 'Taurus',
        degree: 15,
        description: 'In the Navamsa chart, the ascendant shows deeper aspects of your personality and marriage.'
      },
      planets: [
        {
          name: 'Sun',
          sign: 'Gemini',
          degree: 10,
          house: 2,
          retrograde: false,
          description: 'The Sun in the Navamsa shows your deeper soul purpose and spiritual path.'
        },
        {
          name: 'Moon',
          sign: 'Leo',
          degree: 25,
          house: 4,
          retrograde: false,
          description: 'The Moon in the Navamsa reveals your emotional patterns in relationships.'
        }
      ],
      houses: [
        {
          number: 1,
          sign: 'Taurus',
          degree: 0,
          planets: [],
          description: 'The 1st house in D9 shows your approach to marriage and partnerships.'
        },
        {
          number: 2,
          sign: 'Gemini',
          degree: 30,
          planets: ['Sun'],
          description: 'The 2nd house in D9 relates to family values and resources in marriage.'
        },
        {
          number: 4,
          sign: 'Leo',
          degree: 90,
          planets: ['Moon'],
          description: 'The 4th house in D9 shows emotional security in relationships.'
        }
      ],
      aspects: [
        {
          planet1: 'Sun',
          planet2: 'Moon',
          aspectType: 'Trine',
          orb: 0.5,
          influence: 'positive',
          description: 'This aspect indicates harmony between your spiritual purpose and emotional needs.'
        }
      ]
    };
  };

  const handleExport = () => {
    // In a real implementation, this would generate a PDF or image of the chart
    alert('Export functionality would be implemented here in production.');
  };

  // Helper function to format birth time for display
  const formatBirthTime = (timeString: string) => {
    try {
      const date = new Date(timeString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return timeString;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <CelestialBackground />
        <div className="container mx-auto px-4 py-8 relative z-10">
          <div className="max-w-2xl mx-auto bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
            <h1 className="text-xl font-semibold mb-4 text-red-600">Error</h1>
            <p className="mb-4">{error}</p>
            <button
              onClick={() => router.push('/birth-time-rectifier/analysis')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Return to Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Navamsa Chart (D9) - Detailed View</title>
        <meta name="description" content="Detailed view of your Navamsa chart (D9)" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-white mb-4 md:mb-0">Navamsa Chart (D9)</h1>
          <div className="flex space-x-3">
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
            >
              Export Chart
            </button>
            <button
              onClick={() => router.back()}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
            >
              Back to Analysis
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Birth Details Summary */}
          <div className="bg-white bg-opacity-90 backdrop-blur-sm p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Birth Details</h2>
            {rectificationResult ? (
              <div className="space-y-3">
                {rectificationResult.birthDetails.name && (
                  <p><span className="font-medium">Name:</span> {rectificationResult.birthDetails.name}</p>
                )}
                {rectificationResult.birthDetails.date && (
                  <p><span className="font-medium">Date:</span> {rectificationResult.birthDetails.date}</p>
                )}
                <p>
                  <span className="font-medium">Original Time:</span> {formatBirthTime(rectificationResult.originalTime)}
                </p>
                <p>
                  <span className="font-medium">Rectified Time:</span> {formatBirthTime(rectificationResult.suggestedTime)}
                </p>
                {rectificationResult.birthDetails.place && (
                  <p><span className="font-medium">Place:</span> {rectificationResult.birthDetails.place}</p>
                )}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p><span className="font-medium">Confidence:</span> {rectificationResult.confidence * 100}%</p>
                  <p><span className="font-medium">Reliability:</span> {rectificationResult.reliability}</p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">Birth details not available.</p>
            )}
            <div className="mt-6 pt-4 border-t border-gray-200">
              <h3 className="font-medium mb-2">About D9 Chart</h3>
              <p className="text-sm text-gray-500 mt-4">
                The D9 chart (Navamsa) represents the 9th harmonic division of the zodiac. It shows deeper karmic
                patterns, especially related to marriage, relationships, and spirituality.
              </p>
            </div>
          </div>

          {/* Chart Visualization */}
          <div className="lg:col-span-2 bg-white bg-opacity-90 backdrop-blur-sm p-6 rounded-lg shadow flex flex-col">
            <h2 className="text-xl font-semibold mb-4">D9 Chart Visualization</h2>
            <div className="flex-grow flex items-center justify-center">
              {formattedChartData ? (
                <ChartVisualization
                  chartData={formattedChartData}
                  width={500}
                  height={500}
                  onPlanetClick={handlePlanetClick}
                />
              ) : (
                <div className="text-center py-10">
                  <p className="text-gray-500">D9 chart data not available.</p>
                  <p className="text-sm text-gray-400 mt-2">This may be due to limited information or subscription level.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Planet Details and Interpretations */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Planet Details */}
          <div className="bg-white bg-opacity-90 backdrop-blur-sm p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Planet Positions</h2>
            {chartData ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Planet</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sign</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Degree</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">House</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {chartData.planets.map((planet) => (
                      <tr
                        key={planet.name}
                        className={`cursor-pointer hover:bg-gray-50 ${selectedPlanet === planet.name ? 'bg-blue-50' : ''}`}
                        onClick={() => handlePlanetClick(planet.name)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{planet.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{planet.sign}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{planet.degree.toFixed(2)}°</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{planet.house}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500">Planet data not available.</p>
            )}
          </div>

          {/* Selected Planet Interpretation */}
          <div className="bg-white bg-opacity-90 backdrop-blur-sm p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Planet Interpretation</h2>
            {selectedPlanet && chartData ? (
              <div>
                {chartData.planets
                  .filter(planet => planet.name === selectedPlanet)
                  .map(planet => (
                    <div key={planet.name}>
                      <h3 className="text-lg font-medium text-indigo-700 mb-2">{planet.name} in {planet.sign}</h3>
                      <div className="mb-4 p-3 bg-indigo-50 rounded-md">
                        <p className="text-sm"><span className="font-medium">Position:</span> {planet.degree.toFixed(2)}° {planet.sign}</p>
                        <p className="text-sm"><span className="font-medium">House:</span> {planet.house}</p>
                        {planet.retrograde && (
                          <p className="text-sm text-orange-600"><span className="font-medium">Motion:</span> Retrograde</p>
                        )}
                      </div>
                      <div className="mt-4">
                        <h4 className="font-medium mb-2">Interpretation in D9 Chart:</h4>
                        <p className="text-gray-700">{planet.description || `The ${planet.name} in ${planet.sign} in the D9 chart indicates specific patterns in your relationships and spiritual growth.`}</p>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-gray-500">Select a planet from the chart or table to view its interpretation.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
