import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import ChartVisualization from '@/components/charts/ChartVisualization';

// Import test data
const TEST_CHART_DATA = {
  birthDate: "1990-01-01",
  birthTime: "12:00",
  latitude: 18.5204,
  longitude: 73.8567,
  timezone: "Asia/Kolkata"
};

interface PlanetPosition {
  sign: string;
  degree: number;
  house: number;
  longitude: number;
}

interface Aspect {
  planet1: string;
  planet2: string;
  type: 'conjunction' | 'opposition' | 'trine' | 'square';
  angle: number;
}

interface PlanetData {
  name: string;
  sign: string;
  degree: number;
  house: number;
  longitude: number;
}

interface ChartData {
  planets: PlanetData[];
  houses: Array<{
    number: number;
    degree: number;
    sign: string;
  }>;
  ascendant: {
    degree: number;
    sign: string;
    longitude: number;
  };
  aspects: Array<{
    planet1: string;
    planet2: string;
    type: string;
    angle: number;
  }>;
}

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

interface PlanetName {
  Sun: 'Sun';
  Moon: 'Moon';
  Mercury: 'Mercury';
  Venus: 'Venus';
  Mars: 'Mars';
  Jupiter: 'Jupiter';
  Saturn: 'Saturn';
  Uranus: 'Uranus';
  Neptune: 'Neptune';
  Pluto: 'Pluto';
}

type PlanetKey = keyof PlanetName;

const D1ChartPage: React.FC = () => {
  const router = useRouter();
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [formattedChartData, setFormattedChartData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlanet, setSelectedPlanet] = useState<PlanetData | null>(null);
  const [formData, setFormData] = useState({
    birthDate: TEST_CHART_DATA.birthDate,
    birthTime: TEST_CHART_DATA.birthTime,
    latitude: TEST_CHART_DATA.latitude,
    longitude: TEST_CHART_DATA.longitude,
    timezone: TEST_CHART_DATA.timezone
  });

  const generateMockChartData = (): ChartData => {
    // Define planets with exact angles for testing
    const planetsArray: PlanetData[] = [
      { name: 'Sun', sign: 'Sagittarius', degree: 16.5, house: 5, longitude: 256.5 },
      { name: 'Moon', sign: 'Libra', degree: 23.8, house: 3, longitude: 203.8 },
      { name: 'Mercury', sign: 'Sagittarius', degree: 28.4, house: 5, longitude: 268.4 },
      { name: 'Venus', sign: 'Aquarius', degree: 3.1, house: 7, longitude: 303.1 },
      { name: 'Mars', sign: 'Capricorn', degree: 8.2, house: 6, longitude: 278.2 },
      { name: 'Jupiter', sign: 'Cancer', degree: 12.7, house: 12, longitude: 102.7 },
      { name: 'Saturn', sign: 'Capricorn', degree: 19.5, house: 6, longitude: 289.5 },
      { name: 'Rahu', sign: 'Pisces', degree: 25.3, house: 8, longitude: 355.3 },
      { name: 'Ketu', sign: 'Virgo', degree: 25.3, house: 2, longitude: 175.3 }
    ];

    // Calculate aspects with exact angles
    const aspectDefinitions = [
      { type: 'conjunction', angle: 0, orb: 10 },
      { type: 'opposition', angle: 180, orb: 10 },
      { type: 'trine', angle: 120, orb: 8 },
      { type: 'square', angle: 90, orb: 8 }
    ];

    const aspects: Array<{
      planet1: string;
      planet2: string;
      type: string;
      angle: number;
    }> = [];

    for (let i = 0; i < planetsArray.length; i++) {
      for (let j = i + 1; j < planetsArray.length; j++) {
        const planet1 = planetsArray[i];
        const planet2 = planetsArray[j];

        // Calculate the shortest angular distance between planets
        let distance = Math.abs(planet1.longitude - planet2.longitude);
        if (distance > 180) {
          distance = 360 - distance;
        }

        // Check for aspects with wider orbs for testing
        for (const aspect of aspectDefinitions) {
          const orb = Math.abs(distance - aspect.angle);
          if (orb <= aspect.orb) {
            aspects.push({
              planet1: planet1.name,
              planet2: planet2.name,
              type: aspect.type,
              angle: distance
            });
            break; // Only record the strongest aspect between two planets
          }
        }
      }
    }

    // Update house positions to match planet positions
    const houses = Array.from({ length: 12 }, (_, i) => ({
      number: i + 1,
      degree: i * 30,
      sign: getSignForDegree(i * 30)
    }));

    return {
      planets: planetsArray,
      houses,
      ascendant: { degree: 0, sign: 'Aries', longitude: 0 },
      aspects
    };
  };

  const generateChart = () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = generateMockChartData();
      setChartData(data);
      setFormattedChartData(data);

      // Add a small delay to ensure the DOM is ready
      requestAnimationFrame(() => {
        const chartElement = document.querySelector('.chart-ready');
        if (chartElement) {
          chartElement.dispatchEvent(new Event('chartready'));
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate chart');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Generate chart data when component mounts
    generateChart();
  }, []);

  const handlePlanetClick = (planet: PlanetData) => {
    setSelectedPlanet(planet);
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

  if (!chartData || !formattedChartData) {
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
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Back
          </button>
        </div>

        <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow p-6">
          <div className="mb-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="birthDate" className="block text-sm font-medium text-gray-700">Birth Date</label>
                <input
                  type="date"
                  id="birthDate"
                  value={formData.birthDate}
                  onChange={(e) => setFormData({ ...formData, birthDate: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="birthTime" className="block text-sm font-medium text-gray-700">Birth Time</label>
                <input
                  type="time"
                  id="birthTime"
                  value={formData.birthTime}
                  onChange={(e) => setFormData({ ...formData, birthTime: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  id="generate-chart"
                  onClick={generateChart}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Generate Chart
                </button>
              </div>
            </div>
          </div>

          <div className="chart-visualization">
            {formattedChartData && (
              <>
                <ChartVisualization
                  chartData={formattedChartData}
                  width={600}
                  height={600}
                  onPlanetClick={handlePlanetClick}
                />
                <div data-testid="chart-data" className="chart-data">
                  {JSON.stringify(formattedChartData)}
                </div>
              </>
            )}
          </div>

          {selectedPlanet && (
            <div className="planet-details">
              <h3>{selectedPlanet.name}</h3>
              <p>Sign: {selectedPlanet.sign}</p>
              <p>Degree: {selectedPlanet.degree}°</p>
              <p>House: {selectedPlanet.house}</p>
              <p>Longitude: {selectedPlanet.longitude}°</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default D1ChartPage;

// Helper function to get sign index
function getSignIndex(signName: string): number {
  const signs = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
  ];
  return signs.findIndex(sign => sign === signName) !== -1
    ? signs.findIndex(sign => sign === signName)
    : 0;
}

function getSignForDegree(degree: number): string {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  const signIndex = Math.floor(degree / 30) % 12;
  return signs[signIndex];
}
