import React from 'react';
import dynamic from 'next/dynamic';

// Define the proper prop types for ChartVisualization
interface ChartVisualizationProps {
  chartData: any;
  isRectified?: boolean;
  originalChart?: any;
}

// Use dynamic import with the correct typing
const ChartVisualization = dynamic<ChartVisualizationProps>(
  () => import('../components/ChartVisualization'),
  { ssr: false }
);

// Sample test data with planets including Ketu and proper Ascendant
const testChartData = {
  chartId: 'test-chart-1',
  birthTime: '14:30:00',
  ascendant: {
    sign: 'Aquarius',
    degree: 15.2,
    longitude: 315.2  // Necessary for drawing ascendant line
  },
  planets: [
    {
      name: 'Sun',
      sign: 'Libra',
      degree: 7.3,
      house: 9,
      longitude: 187.3,
      retrograde: false
    },
    {
      name: 'Moon',
      sign: 'Taurus',
      degree: 22.5,
      house: 4,
      longitude: 52.5,
      retrograde: false
    },
    {
      name: 'Mercury',
      sign: 'Scorpio',
      degree: 3.8,
      house: 10,
      longitude: 213.8,
      retrograde: false
    },
    {
      name: 'Venus',
      sign: 'Virgo',
      degree: 15.7,
      house: 8,
      longitude: 165.7,
      retrograde: false
    },
    {
      name: 'Mars',
      sign: 'Capricorn',
      degree: 9.2,
      house: 12,
      longitude: 279.2,
      retrograde: false
    },
    {
      name: 'Jupiter',
      sign: 'Aquarius',
      degree: 25.6,
      house: 1,
      longitude: 325.6,
      retrograde: false
    },
    {
      name: 'Saturn',
      sign: 'Scorpio',
      degree: 18.3,
      house: 10,
      longitude: 228.3,
      retrograde: true
    },
    {
      name: 'Rahu',
      sign: 'Aries',
      degree: 15.8,
      house: 3,
      longitude: 15.8,
      retrograde: false
    },
    {
      name: 'Ketu',
      sign: 'Libra',
      degree: 15.8,
      house: 9,
      longitude: 195.8,
      retrograde: false
    }
  ],
  houses: [
    {
      number: 1,
      sign: 'Aquarius',
      degree: 15.2,
      cusp: 315.2,
      planets: ['Jupiter']
    },
    {
      number: 2,
      sign: 'Pisces',
      degree: 15.2,
      cusp: 345.2,
      planets: []
    },
    {
      number: 3,
      sign: 'Aries',
      degree: 15.2,
      cusp: 15.2,
      planets: ['Rahu']
    },
    {
      number: 4,
      sign: 'Taurus',
      degree: 15.2,
      cusp: 45.2,
      planets: ['Moon']
    },
    {
      number: 5,
      sign: 'Gemini',
      degree: 15.2,
      cusp: 75.2,
      planets: []
    },
    {
      number: 6,
      sign: 'Cancer',
      degree: 15.2,
      cusp: 105.2,
      planets: []
    },
    {
      number: 7,
      sign: 'Leo',
      degree: 15.2,
      cusp: 135.2,
      planets: []
    },
    {
      number: 8,
      sign: 'Virgo',
      degree: 15.2,
      cusp: 165.2,
      planets: ['Venus']
    },
    {
      number: 9,
      sign: 'Libra',
      degree: 15.2,
      cusp: 195.2,
      planets: ['Sun', 'Ketu']
    },
    {
      number: 10,
      sign: 'Scorpio',
      degree: 15.2,
      cusp: 225.2,
      planets: ['Mercury', 'Saturn']
    },
    {
      number: 11,
      sign: 'Sagittarius',
      degree: 15.2,
      cusp: 255.2,
      planets: []
    },
    {
      number: 12,
      sign: 'Capricorn',
      degree: 15.2,
      cusp: 285.2,
      planets: ['Mars']
    }
  ]
};

// Create a rectified version for comparison test
const rectifiedChartData = {
  ...testChartData,
  chartId: 'test-chart-2',
  birthTime: '14:35:00',
  // Adjust some positions slightly to simulate rectification
  ascendant: {
    ...testChartData.ascendant,
    degree: 16.8,
    longitude: 316.8
  },
  planets: testChartData.planets.map(planet => ({
    ...planet,
    longitude: planet.longitude + 1.5,
    degree: (planet.degree + 1.5) % 30
  }))
};

export default function TestChartElements() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Chart Elements Test Page</h1>

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Single Chart Test</h2>
        <div className="border p-4 rounded-lg">
          <ChartVisualization chartData={testChartData} />
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Chart Comparison Test</h2>
        <div className="border p-4 rounded-lg">
          {/* Props will be passed through dynamic import */}
          <ChartVisualization
            chartData={rectifiedChartData}
            isRectified={true}
            originalChart={testChartData}
          />
        </div>
      </div>

      <div className="mt-8 p-4 bg-gray-100 rounded-lg">
        <h3 className="font-semibold">Chart Debugging Information:</h3>
        <div className="mt-2">
          <p><strong>Planets:</strong> {testChartData.planets.map(p => p.name).join(', ')}</p>
          <p><strong>Has Ketu:</strong> {testChartData.planets.some(p => p.name === 'Ketu') ? 'Yes' : 'No'}</p>
          <p><strong>Has Ascendant:</strong> {testChartData.ascendant ? 'Yes' : 'No'}</p>
        </div>
      </div>
    </div>
  );
}
