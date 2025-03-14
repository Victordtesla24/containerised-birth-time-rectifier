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

  // Determine planet relationships with ascendant sign
  // This is used for color-coding planets (red for enemy houses, green for friendly houses)
  const planetRelationships = determinePlanetRelationships(chartData.planets, ascendant);

  return (
    <div className={`north-indian-chart ${className}`}>
      <div className="chart-title text-center text-white text-lg font-medium mb-2">
        Vedic Birth Chart (North Indian Style)
      </div>

      <div className="chart-container relative aspect-square w-full max-w-md mx-auto">
        {/* Chart grid layout */}
        <div className="chart-grid grid grid-cols-4 grid-rows-4 h-full">
          {/* House 1 (Ascendant) */}
          <HouseSection
            houseNum={1}
            sign={houseSignMap[1]}
            planets={planetsByHouse[1] || []}
            position="col-start-3 col-span-1 row-start-3 row-span-1 border-r border-b"
            planetRelationships={planetRelationships}
            isAscendant={true}
          />

          {/* House 2 */}
          <HouseSection
            houseNum={2}
            sign={houseSignMap[2]}
            planets={planetsByHouse[2] || []}
            position="col-start-2 col-span-1 row-start-3 row-span-1 border-r border-b"
            planetRelationships={planetRelationships}
          />

          {/* House 3 */}
          <HouseSection
            houseNum={3}
            sign={houseSignMap[3]}
            planets={planetsByHouse[3] || []}
            position="col-start-2 col-span-1 row-start-2 row-span-1 border-r border-b"
            planetRelationships={planetRelationships}
          />

          {/* House 4 */}
          <HouseSection
            houseNum={4}
            sign={houseSignMap[4]}
            planets={planetsByHouse[4] || []}
            position="col-start-2 col-span-1 row-start-1 row-span-1 border-r border-t"
            planetRelationships={planetRelationships}
          />

          {/* House 5 */}
          <HouseSection
            houseNum={5}
            sign={houseSignMap[5]}
            planets={planetsByHouse[5] || []}
            position="col-start-3 col-span-1 row-start-1 row-span-1 border-r border-t"
            planetRelationships={planetRelationships}
          />

          {/* House 6 */}
          <HouseSection
            houseNum={6}
            sign={houseSignMap[6]}
            planets={planetsByHouse[6] || []}
            position="col-start-4 col-span-1 row-start-1 row-span-1 border-t"
            planetRelationships={planetRelationships}
          />

          {/* House 7 */}
          <HouseSection
            houseNum={7}
            sign={houseSignMap[7]}
            planets={planetsByHouse[7] || []}
            position="col-start-4 col-span-1 row-start-2 row-span-1 border-b"
            planetRelationships={planetRelationships}
          />

          {/* House 8 */}
          <HouseSection
            houseNum={8}
            sign={houseSignMap[8]}
            planets={planetsByHouse[8] || []}
            position="col-start-4 col-span-1 row-start-3 row-span-1 border-b"
            planetRelationships={planetRelationships}
          />

          {/* House 9 */}
          <HouseSection
            houseNum={9}
            sign={houseSignMap[9]}
            planets={planetsByHouse[9] || []}
            position="col-start-4 col-span-1 row-start-4 row-span-1"
            planetRelationships={planetRelationships}
          />

          {/* House 10 */}
          <HouseSection
            houseNum={10}
            sign={houseSignMap[10]}
            planets={planetsByHouse[10] || []}
            position="col-start-3 col-span-1 row-start-4 row-span-1 border-r"
            planetRelationships={planetRelationships}
          />

          {/* House 11 */}
          <HouseSection
            houseNum={11}
            sign={houseSignMap[11]}
            planets={planetsByHouse[11] || []}
            position="col-start-2 col-span-1 row-start-4 row-span-1 border-r"
            planetRelationships={planetRelationships}
          />

          {/* House 12 */}
          <HouseSection
            houseNum={12}
            sign={houseSignMap[12]}
            planets={planetsByHouse[12] || []}
            position="col-start-1 col-span-1 row-start-4 row-span-1"
            planetRelationships={planetRelationships}
          />

          {/* Empty cells to complete the grid */}
          <div className="col-start-1 col-span-1 row-start-3 row-span-1 border-b"></div>
          <div className="col-start-1 col-span-1 row-start-2 row-span-1 border-b"></div>
          <div className="col-start-1 col-span-1 row-start-1 row-span-1"></div>
          <div className="col-start-3 col-span-1 row-start-2 row-span-1 border-r border-b"></div>
        </div>
      </div>

      <div className="chart-legend text-center text-white text-sm mt-2">
        <div className="flex justify-center items-center space-x-4">
          <div className="flex items-center">
            <span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-1"></span>
            <span>Friendly House</span>
          </div>
          <div className="flex items-center">
            <span className="inline-block w-3 h-3 bg-red-500 rounded-full mr-1"></span>
            <span>Enemy House</span>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * HouseSection component - Renders a single house in the North Indian chart
 */
const HouseSection = ({ houseNum, sign, planets = [], position, planetRelationships, isAscendant = false }) => {
  return (
    <div className={`house-section relative ${position} p-1 flex flex-col`}>
      <div className={`house-header text-xs text-center ${isAscendant ? 'text-yellow-300 font-bold' : 'text-blue-200'}`}>
        {houseNum}. {sign}
        {isAscendant && <span className="ml-1">(Asc)</span>}
      </div>

      <div className="planets-container flex flex-wrap justify-center items-center flex-1">
        {planets.map((planet, index) => {
          // Determine planet color based on relationship with ascendant
          const relationship = planetRelationships[planet.name] || 'neutral';
          let planetColor = 'text-white'; // default

          if (relationship === 'friendly') {
            planetColor = 'text-green-500';
          } else if (relationship === 'enemy') {
            planetColor = 'text-red-500';
          }

          return (
            <div
              key={`${planet.name}-${index}`}
              className={`planet-item text-xs ${planetColor} mx-1 my-1 flex flex-col items-center`}
              title={`${planet.name} at ${planet.degree}° ${planet.sign}`}
            >
              <span className="planet-symbol text-sm">{getPlanetSymbol(planet.name)}</span>
              <span className="planet-name text-[0.6rem]">{planet.name}</span>
              {planet.isRetrograde && <span className="retrograde text-[0.5rem] text-orange-300">R</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * Determine planet relationships with the ascendant sign
 * This is a simplified version for demonstration purposes
 */
const determinePlanetRelationships = (planets, ascendantSign) => {
  // Define planet relationships with signs (simplified)
  const relationships = {
    // Format: planetName: { friendlySigns: [], enemySigns: [] }
    Sun: {
      friendlySigns: ['Leo', 'Aries', 'Sagittarius'],
      enemySigns: ['Aquarius', 'Libra', 'Capricorn']
    },
    Moon: {
      friendlySigns: ['Cancer', 'Taurus', 'Pisces'],
      enemySigns: ['Scorpio', 'Capricorn', 'Leo']
    },
    Mercury: {
      friendlySigns: ['Gemini', 'Virgo', 'Libra'],
      enemySigns: ['Pisces', 'Sagittarius']
    },
    Venus: {
      friendlySigns: ['Taurus', 'Libra', 'Pisces'],
      enemySigns: ['Virgo', 'Scorpio', 'Aries']
    },
    Mars: {
      friendlySigns: ['Aries', 'Scorpio', 'Capricorn'],
      enemySigns: ['Libra', 'Cancer', 'Taurus']
    },
    Jupiter: {
      friendlySigns: ['Sagittarius', 'Pisces', 'Cancer'],
      enemySigns: ['Capricorn', 'Virgo']
    },
    Saturn: {
      friendlySigns: ['Capricorn', 'Aquarius', 'Libra'],
      enemySigns: ['Leo', 'Cancer', 'Aries']
    },
    Rahu: {
      friendlySigns: ['Gemini', 'Virgo', 'Aquarius'],
      enemySigns: ['Pisces', 'Leo']
    },
    Ketu: {
      friendlySigns: ['Sagittarius', 'Pisces'],
      enemySigns: ['Gemini', 'Virgo']
    }
  };

  // Calculate relationship for each planet
  const result = {};
  planets.forEach(planet => {
    const planetName = planet.name;
    const planetSign = planet.sign;

    // Skip if we don't have relationship data for this planet
    if (!relationships[planetName]) {
      result[planetName] = 'neutral';
      return;
    }

    // Check if the planet is in a friendly or enemy house from the ascendant
    if (relationships[planetName].friendlySigns.includes(ascendantSign)) {
      result[planetName] = 'friendly';
    } else if (relationships[planetName].enemySigns.includes(ascendantSign)) {
      result[planetName] = 'enemy';
    } else {
      result[planetName] = 'neutral';
    }
  });

  return result;
};

const getSignIndex = (sign) => {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  return signs.indexOf(sign);
};

const getSignByIndex = (index) => {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  return signs[index % 12];
};

const findHouseBySign = (sign, houseSignMap) => {
  for (let house = 1; house <= 12; house++) {
    if (houseSignMap[house] === sign) {
      return house;
    }
  }
  return 1; // Default to 1st house if not found
};

function getPlanetSymbol(planetName) {
  const symbols = {
    Sun: '☉',
    Moon: '☽',
    Mercury: '☿',
    Venus: '♀',
    Mars: '♂',
    Jupiter: '♃',
    Saturn: '♄',
    Uranus: '♅',
    Neptune: '♆',
    Pluto: '♇',
    Rahu: '☊',
    Ketu: '☋'
  };
  return symbols[planetName] || planetName.charAt(0);
}

export default NorthIndianChart;
