import React from 'react';

/**
 * NorthIndianChart component - Renders a North Indian style (diamond) Vedic astrology chart
 * 
 * @param {Object} props
 * @param {Object} props.chartData - The chart data containing planets, houses, etc.
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element}
 */
const NorthIndianChart = ({ chartData, className = '' }) => {
  if (!chartData || !chartData.planets || !chartData.planets.length) {
    return (
      <div className={`north-indian-chart-placeholder ${className}`}>
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
    <div className={`north-indian-chart ${className}`}>
      <div className="chart-title text-center text-white text-lg font-medium mb-2">
        Vedic Birth Chart (North Indian Style)
      </div>
      
      <div className="chart-container relative aspect-square w-full max-w-md mx-auto">
        {/* Main outer diamond container */}
        <div className="relative w-full h-full transform rotate-45 border-2 border-indigo-300 border-opacity-50 overflow-hidden">
          {/* Inner diamond */}
          <div className="absolute inset-0 m-auto w-1/2 h-1/2 border border-indigo-300 border-opacity-30 bg-indigo-800 bg-opacity-30">
            {/* Center content */}
            <div className="absolute inset-0 flex items-center justify-center transform -rotate-45">
              <div className="text-center">
                <div className="text-sm text-indigo-200">Lagna: {ascendant}</div>
                <div className="text-xs text-indigo-300">
                  {chartData.ascendant?.degree ? `${chartData.ascendant.degree.toFixed(2)}°` : ''}
                </div>
              </div>
            </div>
          </div>
          
          {/* House dividers */}
          <div className="absolute inset-0 w-full h-full">
            {/* Horizontal divider */}
            <div className="absolute top-1/2 left-0 right-0 h-px bg-indigo-300 bg-opacity-50 transform -translate-y-1/2"></div>
            
            {/* Vertical divider */}
            <div className="absolute top-0 bottom-0 left-1/2 w-px bg-indigo-300 bg-opacity-50 transform -translate-x-1/2"></div>
            
            {/* Diagonal divider top-left to bottom-right */}
            <div className="absolute top-0 left-0 w-full h-full">
              <div className="w-full h-full border-b border-indigo-300 border-opacity-50"></div>
            </div>
            
            {/* Diagonal divider top-right to bottom-left */}
            <div className="absolute top-0 right-0 w-full h-full">
              <div className="w-full h-full border-l border-indigo-300 border-opacity-50"></div>
            </div>
          </div>
          
          {/* House contents */}
          <div className="absolute inset-0 w-full h-full">
            {/* House 1 (top) */}
            <HouseSection 
              houseNum={1} 
              sign={houseSignMap[1]} 
              planets={planetsByHouse[1]} 
              position="absolute top-0 left-1/4 right-1/4 h-1/4"
            />
            
            {/* House 2 (top-right) */}
            <HouseSection 
              houseNum={2} 
              sign={houseSignMap[2]} 
              planets={planetsByHouse[2]} 
              position="absolute top-0 right-0 w-1/4 h-1/4"
            />
            
            {/* House 3 (right) */}
            <HouseSection 
              houseNum={3} 
              sign={houseSignMap[3]} 
              planets={planetsByHouse[3]} 
              position="absolute top-1/4 right-0 w-1/4 bottom-1/4"
            />
            
            {/* House 4 (bottom-right) */}
            <HouseSection 
              houseNum={4} 
              sign={houseSignMap[4]} 
              planets={planetsByHouse[4]} 
              position="absolute bottom-0 right-0 w-1/4 h-1/4"
            />
            
            {/* House 5 (bottom) */}
            <HouseSection 
              houseNum={5} 
              sign={houseSignMap[5]} 
              planets={planetsByHouse[5]} 
              position="absolute bottom-0 left-1/4 right-1/4 h-1/4"
            />
            
            {/* House 6 (bottom-left) */}
            <HouseSection 
              houseNum={6} 
              sign={houseSignMap[6]} 
              planets={planetsByHouse[6]} 
              position="absolute bottom-0 left-0 w-1/4 h-1/4"
            />
            
            {/* House 7 (left) */}
            <HouseSection 
              houseNum={7} 
              sign={houseSignMap[7]} 
              planets={planetsByHouse[7]} 
              position="absolute top-1/4 left-0 w-1/4 bottom-1/4"
            />
            
            {/* House 8 (top-left) */}
            <HouseSection 
              houseNum={8} 
              sign={houseSignMap[8]} 
              planets={planetsByHouse[8]} 
              position="absolute top-0 left-0 w-1/4 h-1/4"
            />
            
            {/* House 9 (inner top-left) */}
            <HouseSection 
              houseNum={9} 
              sign={houseSignMap[9]} 
              planets={planetsByHouse[9]} 
              position="absolute top-1/4 left-1/4 w-1/4 h-1/4"
            />
            
            {/* House 10 (inner top-right) */}
            <HouseSection 
              houseNum={10} 
              sign={houseSignMap[10]} 
              planets={planetsByHouse[10]} 
              position="absolute top-1/4 right-1/4 w-1/4 h-1/4"
            />
            
            {/* House 11 (inner bottom-right) */}
            <HouseSection 
              houseNum={11} 
              sign={houseSignMap[11]} 
              planets={planetsByHouse[11]} 
              position="absolute bottom-1/4 right-1/4 w-1/4 h-1/4"
            />
            
            {/* House 12 (inner bottom-left) */}
            <HouseSection 
              houseNum={12} 
              sign={houseSignMap[12]} 
              planets={planetsByHouse[12]} 
              position="absolute bottom-1/4 left-1/4 w-1/4 h-1/4"
            />
          </div>
        </div>
      </div>
      
      {/* Planet Legend */}
      <div className="chart-legend mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
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

/**
 * HouseSection component - Renders a single house section in the chart
 */
const HouseSection = ({ houseNum, sign, planets = [], position }) => {
  const planetSymbols = {
    'Sun': '☉',
    'Moon': '☽',
    'Mercury': '☿',
    'Venus': '♀',
    'Mars': '♂',
    'Jupiter': '♃',
    'Saturn': '♄',
    'Rahu': '☊',
    'Ketu': '☋',
    'Uranus': '♅',
    'Neptune': '♆',
    'Pluto': '♇'
  };
  
  const zodiacSymbols = {
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
  
  return (
    <div className={`house-section ${position} flex flex-col items-center justify-center transform -rotate-45`}>
      <div className="text-xs text-white mb-1">
        <span className="text-indigo-300">{houseNum}</span> {zodiacSymbols[sign] || sign}
      </div>
      
      {planets && planets.length > 0 && (
        <div className="planets-container flex flex-wrap justify-center">
          {planets.map((planet, index) => (
            <div 
              key={`${planet.name}-${index}`}
              className={`planet-icon text-xs ${planet.retrograde ? 'text-orange-300' : 'text-yellow-300'} mx-0.5`}
              title={`${planet.name} in ${planet.sign} ${planet.degree.toFixed(2)}° ${planet.retrograde ? '(R)' : ''}`}
            >
              {planetSymbols[planet.name] || planet.name.charAt(0)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Get the index of a zodiac sign
 */
const getSignIndex = (sign) => {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 
    'Leo', 'Virgo', 'Libra', 'Scorpio', 
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  return signs.indexOf(sign);
};

/**
 * Get the sign name by index
 */
const getSignByIndex = (index) => {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 
    'Leo', 'Virgo', 'Libra', 'Scorpio', 
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  return signs[index % 12];
};

/**
 * Find the house number for a given sign based on house-sign mapping
 */
const findHouseBySign = (sign, houseSignMap) => {
  for (const [houseNum, houseSign] of Object.entries(houseSignMap)) {
    if (houseSign === sign) {
      return parseInt(houseNum);
    }
  }
  return 1; // Default to 1st house if not found
};

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

export default NorthIndianChart; 