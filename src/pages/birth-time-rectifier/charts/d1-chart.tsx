import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import ChartVisualization from '@/components/charts/ChartVisualization';
import { ChartData } from '@/types';

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

export default function D1ChartPage() {
  const router = useRouter();
  const [chartData, setChartData] = useState<MockChartData | null>(null);
  const [formattedChartData, setFormattedChartData] = useState<ChartData | null>(null);
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
      if (parsedResult.charts?.d1Chart) {
        setChartData(parsedResult.charts.d1Chart);

        // Select the first planet by default
        if (parsedResult.charts.d1Chart.planets.length > 0) {
          setSelectedPlanet(parsedResult.charts.d1Chart.planets[0].name);
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
        sign: 'Aries',
        degree: 0,
        description: 'The rising sign represents your outward personality and physical appearance.'
      },
      planets: [
        {
          name: 'Sun',
          sign: 'Aries',
          degree: 15,
          house: 1,
          retrograde: false,
          description: 'The Sun represents your core identity and life purpose.'
        },
        {
          name: 'Moon',
          sign: 'Cancer',
          degree: 5,
          house: 4,
          retrograde: false,
          description: 'The Moon represents your emotions and subconscious mind.'
        }
      ],
      houses: [
        {
          number: 1,
          sign: 'Aries',
          degree: 0,
          planets: ['Sun'],
          description: 'The 1st house represents self, appearance, and beginnings.'
        },
        {
          number: 4,
          sign: 'Cancer',
          degree: 90,
          planets: ['Moon'],
          description: 'The 4th house represents home, family, and roots.'
        }
      ],
      aspects: [
        {
          planet1: 'Sun',
          planet2: 'Moon',
          aspectType: 'Square',
          orb: 1.5,
          influence: 'neutral',
          description: 'This aspect indicates some tension between your conscious will and emotional needs.'
        }
      ]
    };
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

  if (!chartData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <CelestialBackground />
        <div className="container mx-auto px-4 py-8 relative z-10">
          <div className="max-w-2xl mx-auto bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
            <h1 className="text-xl font-semibold mb-4">No Chart Data Found</h1>
            <p className="mb-4">Unable to load chart data. Please complete the rectification process first.</p>
            <button
              onClick={() => router.push('/birth-time-rectifier')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Return to Birth Details Form
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Birth Chart (D1) - Detailed View</title>
        <meta name="description" content="Detailed view of your birth chart (D1)" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-white">Birth Chart (D1)</h1>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
          >
            Back to Analysis
          </button>
        </div>

        <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart Visualization - takes 2/3 width on large screens */}
          <div className="lg:col-span-2 bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Chart Visualization</h2>
            {formattedChartData ? (
              <ChartVisualization
                chartData={formattedChartData}
                width={500}
                height={500}
                onPlanetClick={handlePlanetClick}
              />
            ) : (
              <div className="aspect-square max-w-lg mx-auto flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg">
                <p className="text-gray-500">Loading chart data...</p>
              </div>
            )}
          </div>

          {/* Chart Details - takes 1/3 width on large screens */}
          <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Chart Details</h2>

            <div className="mb-6">
              <h3 className="font-medium border-b pb-2 mb-2">Ascendant</h3>
              <p><span className="font-medium">Sign:</span> {chartData.ascendant.sign}</p>
              <p><span className="font-medium">Position:</span> {chartData.ascendant.degree.toFixed(2)}°</p>
              {chartData.ascendant.description && (
                <p className="mt-2 text-gray-600 italic">{chartData.ascendant.description}</p>
              )}
            </div>

            {selectedPlanet ? (
              <div className="mb-6">
                <h3 className="font-medium border-b pb-2 mb-2">Selected Planet</h3>
                {chartData.planets
                  .filter(planet => planet.name === selectedPlanet)
                  .map(planet => (
                    <div key={planet.name} className="space-y-2">
                      <p><span className="font-medium">Name:</span> {planet.name}</p>
                      <p><span className="font-medium">Sign:</span> {planet.sign}</p>
                      <p><span className="font-medium">House:</span> {planet.house}</p>
                      <p><span className="font-medium">Position:</span> {planet.degree.toFixed(2)}°</p>
                      {planet.retrograde && (
                        <p><span className="font-medium">Motion:</span> Retrograde</p>
                      )}
                      {planet.description && (
                        <p className="mt-3 text-gray-700 italic">{planet.description}</p>
                      )}
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">Select a planet to view details</p>
            )}

            <div className="mt-6">
              <h3 className="font-medium border-b pb-2 mb-2">All Planets</h3>
              <ul className="space-y-1">
                {chartData.planets.map(planet => (
                  <li
                    key={planet.name}
                    className={`cursor-pointer p-2 rounded hover:bg-gray-100 ${
                      selectedPlanet === planet.name ? 'bg-blue-50 border-l-4 border-blue-500 pl-2' : ''
                    }`}
                    onClick={() => handlePlanetClick(planet.name)}
                  >
                    {planet.name} - {planet.sign} ({planet.house}H)
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
