import React from 'react';

/**
 * VedicChart component - Renders a South Indian style (square grid) Vedic astrology chart
 * 
 * @param {Object} props
 * @param {Object} props.chartData - The chart data containing planets, houses, etc.
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element}
 */
const VedicChart = ({ chartData, className = '' }) => {
  if (!chartData || !chartData.planets || !chartData.planets.length) {
    return (
      <div className={`vedic-chart-placeholder ${className}`}>
        <div className="flex items-center justify-center h-64 bg-indigo-800 bg-opacity-50 rounded-lg border border-indigo-300 border-opacity-30 p-4">
          <p className="text-indigo-200">Chart data unavailable</p>
        </div>
      </div>
    );
  }

  // Get Ascendant (Lagna) sign
  const ascendant = chartData.ascendant?.sign || 'Aries';
  const ascSignIndex = getSignIndex(ascendant);
  
  // Organize houses based on ascendant
  const houseSignMap = {};
  for (let i = 0; i < 12; i++) {
    const houseNum = i + 1;
    const signIndex = (ascSignIndex + i) % 12;
    houseSignMap[houseNum] = getSignByIndex(signIndex);
  }
  
  // Organize planets by house
  const planetsByHouse = {};
  chartData.planets.forEach(planet => {
    const house = planet.house || findHouseBySign(planet.sign, houseSignMap);
    if (!planetsByHouse[house]) {
      planetsByHouse[house] = [];
    }
    planetsByHouse[house].push(planet);
  });

  return (
    <div className={`vedic-chart ${className}`}>
      <div className="chart-title text-center text-white text-lg font-medium mb-2">
        Vedic Birth Chart (South Indian Style)
      </div>
      
      <div className="chart-container aspect-square w-full max-w-md mx-auto">
        <div className="grid grid-cols-4 grid-rows-4 h-full border-2 border-indigo-300 border-opacity-50 rounded-lg overflow-hidden">
          {/* Top row (houses 12, 1, 2, 3) */}
          <ChartCell houseNum={12} sign={houseSignMap[12]} planets={planetsByHouse[12]} />
          <ChartCell houseNum={1} sign={houseSignMap[1]} planets={planetsByHouse[1]} />
          <ChartCell houseNum={2} sign={houseSignMap[2]} planets={planetsByHouse[2]} />
          <ChartCell houseNum={3} sign={houseSignMap[3]} planets={planetsByHouse[3]} />
          
          {/* Second row (houses 11, center top, center top, 4) */}
          <ChartCell houseNum={11} sign={houseSignMap[11]} planets={planetsByHouse[11]} />
          <div className="col-span-2 row-span-2 border border-indigo-300 border-opacity-30 flex items-center justify-center bg-indigo-800 bg-opacity-30">
            <div className="text-center">
              <div className="text-sm text-indigo-200 mb-2">Lagna: {ascendant}</div>
              <div className="text-xs text-indigo-300">
                {chartData.ascendant?.degree ? `${chartData.ascendant.degree.toFixed(2)}°` : ''}
              </div>
            </div>
          </div>
          <ChartCell houseNum={4} sign={houseSignMap[4]} planets={planetsByHouse[4]} />
          
          {/* Third row (houses 10, center bottom, center bottom, 5) */}
          <ChartCell houseNum={10} sign={houseSignMap[10]} planets={planetsByHouse[10]} />
          <ChartCell houseNum={5} sign={houseSignMap[5]} planets={planetsByHouse[5]} />
          
          {/* Bottom row (houses 9, 8, 7, 6) */}
          <ChartCell houseNum={9} sign={houseSignMap[9]} planets={planetsByHouse[9]} />
          <ChartCell houseNum={8} sign={houseSignMap[8]} planets={planetsByHouse[8]} />
          <ChartCell houseNum={7} sign={houseSignMap[7]} planets={planetsByHouse[7]} />
          <ChartCell houseNum={6} sign={houseSignMap[6]} planets={planetsByHouse[6]} />
        </div>
      </div>
      
      {/* Planet Legend */}
      <div className="chart-legend mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {chartData.planets.map(planet => (
          <div key={planet.name} className="text-xs p-2 rounded bg-indigo-700 bg-opacity-40 flex items-center">
            <span className="planet-symbol mr-1">{getPlanetSymbol(planet.name)}</span>
            <span className="text-white">{planet.name}: </span>
            <span className="text-indigo-200 ml-1">
              {planet.sign} {planet.degree && planet.degree.toFixed(1)}°
              {planet.retrograde ? ' (R)' : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Individual cell within the chart grid
const ChartCell = ({ houseNum, sign, planets = [] }) => {
  return (
    <div className="relative border border-indigo-300 border-opacity-30 flex flex-col bg-indigo-800 bg-opacity-20 p-1">
      {/* House number and sign in the corner */}
      <div className="absolute top-1 left-1 text-xs text-indigo-300">
        {houseNum}
      </div>
      <div className="absolute top-1 right-1 text-xs text-white">
        {getSignSymbol(sign)}
      </div>
      
      {/* Planets in this house */}
      <div className="flex-grow flex items-center justify-center">
        <div className="text-xs">
          {planets && planets.map(planet => (
            <div key={planet.name} className="planet-item flex items-center justify-center">
              <span className="planet-symbol text-white">{getPlanetSymbol(planet.name)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Helper function to get sign index (0-11)
function getSignIndex(sign) {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  return signs.indexOf(sign);
}

// Helper function to get sign by index
function getSignByIndex(index) {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  return signs[index % 12];
}

// Find house by sign
function findHouseBySign(sign, houseSignMap) {
  for (let i = 1; i <= 12; i++) {
    if (houseSignMap[i] === sign) {
      return i;
    }
  }
  return 1; // Default to house 1 if not found
}

// Helper function to get planet symbol
function getPlanetSymbol(planetName) {
  const symbols = {
    'Sun': '☉',
    'Moon': '☽',
    'Mercury': '☿',
    'Venus': '♀',
    'Mars': '♂',
    'Jupiter': '♃',
    'Saturn': '♄',
    'Uranus': '♅',
    'Neptune': '♆',
    'Pluto': '♇',
    'Rahu': '☊',
    'Ketu': '☋'
  };
  return symbols[planetName] || planetName.charAt(0);
}

// Helper function to get sign symbol
function getSignSymbol(sign) {
  const symbols = {
    'Aries': '♈',
    'Taurus': '♉',
    'Gemini': '♊',
    'Cancer': '♋',
    'Leo': '♌',
    'Virgo': '♍',
    'Libra': '♎',
    'Scorpio': '♏',
    'Sagittarius': '♐',
    'Capricorn': '♑',
    'Aquarius': '♒',
    'Pisces': '♓'
  };
  return symbols[sign] || sign.substring(0, 3);
}

export default VedicChart; 