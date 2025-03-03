import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import ChartVisualization from '@/components/charts/ChartVisualization';
import { RectificationResult, ChartData } from '@/types';

type DivisionalChart = 'D1' | 'D2' | 'D3' | 'D4' | 'D5' | 'D7' | 'D9' | 'D10' | 'D12' | 'D16' | 'D20' | 'D24' | 'D27' | 'D30' | 'D40' | 'D45' | 'D60';

interface ChartInfo {
  id: DivisionalChart;
  name: string;
  description: string;
  available: boolean;
  requiresPremium: boolean;
}

// Mock chart data for demonstration
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

interface MockChartData {
  ascendant: {
    sign: string;
    degree: number;
    description?: string;
  };
  planets: MockPlanetPosition[];
  houses: MockHouseDetails[];
  aspects: any[];
}

export default function CustomChartsPage() {
  const router = useRouter();
  const [rectificationResult, setRectificationResult] = useState<RectificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userSubscriptionTier, setUserSubscriptionTier] = useState<'free' | 'standard' | 'premium'>('standard');
  const [selectedChart, setSelectedChart] = useState<DivisionalChart>('D1');
  const [mockChartData, setMockChartData] = useState<MockChartData | null>(null);
  const [formattedChartData, setFormattedChartData] = useState<ChartData | null>(null);

  // Chart definitions with availability based on subscription tier
  const chartDefinitions: ChartInfo[] = [
    {
      id: 'D1',
      name: 'Rashi Chart (Birth Chart)',
      description: 'The main birth chart showing planetary positions at the time of birth.',
      available: true,
      requiresPremium: false
    },
    {
      id: 'D2',
      name: 'Hora Chart',
      description: 'Shows wealth potential and material resources.',
      available: userSubscriptionTier !== 'free',
      requiresPremium: false
    },
    {
      id: 'D3',
      name: 'Drekkana Chart',
      description: 'Indicates siblings and courage.',
      available: userSubscriptionTier !== 'free',
      requiresPremium: false
    },
    {
      id: 'D4',
      name: 'Chaturthamsa Chart',
      description: 'Shows property and fixed assets.',
      available: userSubscriptionTier !== 'free',
      requiresPremium: false
    },
    {
      id: 'D7',
      name: 'Saptamsa Chart',
      description: 'Indicates children and creative abilities.',
      available: userSubscriptionTier !== 'free',
      requiresPremium: false
    },
    {
      id: 'D9',
      name: 'Navamsa Chart',
      description: 'Shows marriage, relationships, and dharma.',
      available: true,
      requiresPremium: false
    },
    {
      id: 'D10',
      name: 'Dasamsa Chart',
      description: 'Indicates career and professional life.',
      available: userSubscriptionTier !== 'free',
      requiresPremium: false
    },
    {
      id: 'D12',
      name: 'Dwadasamsa Chart',
      description: 'Shows parents and ancestry.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D16',
      name: 'Shodasamsa Chart',
      description: 'Indicates vehicles and comforts of life.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D20',
      name: 'Vimsamsa Chart',
      description: 'Shows spiritual practices and religious inclinations.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D24',
      name: 'Chaturvimsamsa Chart',
      description: 'Indicates educational achievements and learning.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D27',
      name: 'Saptavimsamsa Chart',
      description: 'Shows strengths and weaknesses.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D30',
      name: 'Trimsamsa Chart',
      description: 'Indicates misfortunes and challenges.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D40',
      name: 'Khavedamsa Chart',
      description: 'Shows auspicious and inauspicious effects.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D45',
      name: 'Akshavedamsa Chart',
      description: 'Indicates general well-being and fortune.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    },
    {
      id: 'D60',
      name: 'Shashtiamsa Chart',
      description: 'Shows the most detailed and specific karmic influences.',
      available: userSubscriptionTier === 'premium',
      requiresPremium: true
    }
  ];

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

      // Generate mock chart data for the selected chart
      generateMockChartData(selectedChart);
    } catch (e) {
      console.error('Error parsing stored rectification result:', e);
      setError('Failed to load chart data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [router, selectedChart]);

  // Format the mock chart data to match the ChartData interface
  useEffect(() => {
    if (mockChartData) {
      const formattedData: ChartData = {
        ascendant: {
          sign: mockChartData.ascendant.sign,
          degree: mockChartData.ascendant.degree,
          description: mockChartData.ascendant.description
        },
        planets: mockChartData.planets.map(planet => ({
          planet: planet.name,
          sign: planet.sign,
          degree: planet.degree.toString(),
          house: planet.house,
          retrograde: planet.retrograde,
          description: planet.description
        })),
        houses: mockChartData.houses.map(house => ({
          number: house.number,
          sign: house.sign,
          startDegree: house.degree,
          endDegree: house.degree + 30,
          planets: house.planets.map(planetName => ({
            planet: planetName,
            sign: mockChartData.planets.find(p => p.name === planetName)?.sign || '',
            degree: mockChartData.planets.find(p => p.name === planetName)?.degree.toString() || '0',
            house: house.number
          }))
        })),
        aspects: mockChartData.aspects.map(aspect => ({
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
  }, [mockChartData]);

  const handleChartSelection = (chartId: DivisionalChart) => {
    const chartInfo = chartDefinitions.find(chart => chart.id === chartId);

    if (!chartInfo) {
      setError(`Chart ${chartId} not found.`);
      return;
    }

    if (!chartInfo.available) {
      if (chartInfo.requiresPremium) {
        alert(`The ${chartInfo.name} requires a premium subscription. Upgrade to access this chart.`);
      } else {
        alert(`The ${chartInfo.name} is not available in your current subscription tier.`);
      }
      return;
    }

    setSelectedChart(chartId);
    generateMockChartData(chartId);
  };

  const generateMockChartData = (chartType: DivisionalChart) => {
    // Generate different mock data based on chart type
    const baseChart: MockChartData = {
      ascendant: {
        sign: 'Aries',
        degree: 15,
        description: `The ascendant in the ${chartType} chart represents your outward personality and physical appearance.`
      },
      planets: [
        {
          name: 'Sun',
          sign: 'Taurus',
          degree: 10,
          house: 2,
          retrograde: false,
          description: `The Sun in the ${chartType} chart represents your core identity and life purpose.`
        },
        {
          name: 'Moon',
          sign: 'Cancer',
          degree: 5,
          house: 4,
          retrograde: false,
          description: `The Moon in the ${chartType} chart represents your emotions and subconscious mind.`
        },
        {
          name: 'Mercury',
          sign: 'Taurus',
          degree: 15,
          house: 2,
          retrograde: false,
          description: `Mercury in the ${chartType} chart represents your communication style and intellectual approach.`
        },
        {
          name: 'Venus',
          sign: 'Gemini',
          degree: 20,
          house: 3,
          retrograde: false,
          description: `Venus in the ${chartType} chart represents your approach to love, beauty, and values.`
        },
        {
          name: 'Mars',
          sign: 'Aries',
          degree: 25,
          house: 1,
          retrograde: false,
          description: `Mars in the ${chartType} chart represents your drive, energy, and assertiveness.`
        }
      ],
      houses: [
        {
          number: 1,
          sign: 'Aries',
          degree: 15,
          planets: ['Mars'],
          description: `The 1st house in the ${chartType} chart represents self, appearance, and beginnings.`
        },
        {
          number: 2,
          sign: 'Taurus',
          degree: 15,
          planets: ['Sun', 'Mercury'],
          description: `The 2nd house in the ${chartType} chart represents wealth, values, and possessions.`
        },
        {
          number: 3,
          sign: 'Gemini',
          degree: 15,
          planets: ['Venus'],
          description: `The 3rd house in the ${chartType} chart represents communication, siblings, and short journeys.`
        },
        {
          number: 4,
          sign: 'Cancer',
          degree: 15,
          planets: ['Moon'],
          description: `The 4th house in the ${chartType} chart represents home, family, and roots.`
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

    // Modify the chart based on the chart type
    let modifiedChart = { ...baseChart };

    if (chartType === 'D9') {
      modifiedChart.ascendant.sign = 'Taurus';
      modifiedChart.planets[0].sign = 'Gemini';
      modifiedChart.planets[0].house = 2;
      modifiedChart.planets[1].sign = 'Leo';
      modifiedChart.planets[1].house = 4;
      modifiedChart.houses[0].sign = 'Taurus';
      modifiedChart.houses[1].sign = 'Gemini';
      modifiedChart.houses[3].sign = 'Leo';
    } else if (chartType === 'D10') {
      modifiedChart.ascendant.sign = 'Capricorn';
      modifiedChart.planets[0].sign = 'Pisces';
      modifiedChart.planets[0].house = 3;
      modifiedChart.planets[1].sign = 'Sagittarius';
      modifiedChart.planets[1].house = 12;
      modifiedChart.houses[0].sign = 'Capricorn';
      modifiedChart.houses[2].sign = 'Pisces';
      modifiedChart.houses[11].sign = 'Sagittarius';
    }

    setMockChartData(modifiedChart);
  };

  const handleUpgradeClick = () => {
    alert('This would redirect to the subscription upgrade page in a production environment.');
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
        <title>Divisional Charts | Birth Time Rectifier</title>
        <meta name="description" content="Explore different divisional charts based on your rectified birth time" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-white mb-4 md:mb-0">Divisional Charts</h1>
          <div className="flex space-x-3">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
            >
              Back to Analysis
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chart Selection Sidebar */}
          <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Chart Types</h2>
            <div className="space-y-2">
              {chartDefinitions.map((chart) => (
                <button
                  key={chart.id}
                  onClick={() => handleChartSelection(chart.id)}
                  className={`w-full text-left px-3 py-2 rounded-md transition ${
                    selectedChart === chart.id
                      ? 'bg-blue-100 text-blue-800'
                      : chart.available
                      ? 'hover:bg-gray-100'
                      : 'text-gray-400 cursor-not-allowed'
                  }`}
                  disabled={!chart.available}
                >
                  <div className="flex items-center justify-between">
                    <span>{chart.id} - {chart.name}</span>
                    {chart.requiresPremium && (
                      <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                        Premium
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
            {userSubscriptionTier !== 'premium' && (
              <div className="mt-6 p-4 bg-indigo-50 rounded-md">
                <p className="text-sm text-indigo-800 mb-2">
                  Upgrade to Premium to access all divisional charts and detailed interpretations.
                </p>
                <button
                  onClick={handleUpgradeClick}
                  className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
                >
                  Upgrade Now
                </button>
              </div>
            )}
          </div>

          {/* Chart Display Area */}
          <div className="lg:col-span-3 bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">
                {chartDefinitions.find(c => c.id === selectedChart)?.name || selectedChart}
              </h2>
              <div className="text-sm text-gray-500">
                Based on rectified birth time
              </div>
            </div>

            {formattedChartData ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <ChartVisualization
                    chartData={formattedChartData}
                    width={400}
                    height={400}
                  />
                </div>
                <div>
                  <h3 className="font-medium text-lg mb-3">Chart Information</h3>
                  <p className="mb-4 text-gray-700">
                    {chartDefinitions.find(c => c.id === selectedChart)?.description}
                  </p>

                  <h4 className="font-medium mt-4 mb-2">Ascendant</h4>
                  <p className="text-gray-700">
                    {mockChartData?.ascendant.sign} - {mockChartData?.ascendant.degree.toFixed(2)}°
                  </p>

                  <h4 className="font-medium mt-4 mb-2">Key Planets</h4>
                  <div className="space-y-1">
                    {mockChartData?.planets.slice(0, 3).map(planet => (
                      <div key={planet.name} className="flex justify-between">
                        <span>{planet.name}</span>
                        <span>{planet.sign} {planet.degree.toFixed(2)}° (House {planet.house})</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-500">
                      For a detailed interpretation of your {selectedChart} chart, please consult with an astrologer.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-64">
                <p className="text-gray-500">Chart data is loading or not available.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
