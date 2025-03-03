import React from 'react';
import { ChartData } from '@/types';

interface BirthChartProps {
  data: ChartData;
  width?: number;
  height?: number;
  onPlanetClick?: (planetId: string) => void;
}

// Names for zodiac signs in order (starting with Aries)
const zodiacSigns = [
  "Aries", "Taurus", "Gemini", "Cancer", 
  "Leo", "Virgo", "Libra", "Scorpio", 
  "Sagittarius", "Capricorn", "Aquarius", "Pisces"
];

// Sanskrit names for the zodiac signs (optional for full Vedic representation)
const sanskritNames = [
  "Mesha", "Vrishabha", "Mithuna", "Karka",
  "Simha", "Kanya", "Tula", "Vrishchika",
  "Dhanu", "Makara", "Kumbha", "Meena"
];

// Planet symbols for Vedic chart
const planetSymbols: Record<string, string> = {
  Sun: "Su",
  Moon: "Mo",
  Mercury: "Me",
  Venus: "Ve",
  Mars: "Ma",
  Jupiter: "Ju",
  Saturn: "Sa",
  Rahu: "Ra",
  Ketu: "Ke",
  Uranus: "Ur", // Optional for modern interpretations
  Neptune: "Ne", // Optional for modern interpretations
  Pluto: "Pl"   // Optional for modern interpretations
};

const BirthChart: React.FC<BirthChartProps> = ({
  data,
  width = 500,
  height = 500,
  onPlanetClick
}) => {
  // Get planets from chart data
  const planets = data.planets || [];

  // Function to handle planet click
  const handlePlanetClick = (planetId: string) => {
    if (onPlanetClick) {
      onPlanetClick(planetId);
    }
  };

  // Calculate the ascendant house (1st house)
  const ascendantDegree = typeof data.ascendant === 'number' ? data.ascendant : 0;
  const ascendantSign = Math.floor(ascendantDegree / 30);

  // Calculate house positions (Indian style: fixed square/rectangular houses)
  const houses = Array(12).fill(0).map((_, index) => {
    const houseNumber = (index + 1);
    const signIndex = (ascendantSign + index) % 12;
    return {
      number: houseNumber,
      sign: zodiacSigns[signIndex],
      sanskritName: sanskritNames[signIndex],
      planets: planets.filter(p => p.longitude !== undefined && Math.floor(p.longitude / 30) === signIndex)
    };
  });

  return (
    <div 
      className="birth-chart-container" 
      style={{ width: `${width}px`, height: `${height}px` }}
    >
      <div 
        className="indian-vedic-chart"
        style={{ 
          width: '100%', 
          height: '100%', 
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gridTemplateRows: 'repeat(3, 1fr)',
          border: '2px solid #333',
          backgroundColor: '#f8f8f8'
        }}
      >
        {/* North Indian chart style (12 houses arranged in a square) */}
        {/* Top row (houses 12, 1, 2, 3) */}
        <div style={{ gridArea: '1 / 1 / 2 / 2', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[11])} {/* House 12 */}
        </div>
        <div style={{ gridArea: '1 / 2 / 2 / 3', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[0])} {/* House 1 (Ascendant) */}
        </div>
        <div style={{ gridArea: '1 / 3 / 2 / 4', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[1])} {/* House 2 */}
        </div>
        <div style={{ gridArea: '1 / 4 / 2 / 5', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[2])} {/* House 3 */}
        </div>
        
        {/* Middle row (houses 11, central space, 4) */}
        <div style={{ gridArea: '2 / 1 / 3 / 2', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[10])} {/* House 11 */}
        </div>
        <div style={{ gridArea: '2 / 2 / 3 / 4', border: '1px solid #666', padding: '8px' }}>
          {/* Center area - can display chart details */}
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <div className="text-lg font-bold">Birth Chart</div>
            <div>Ascendant: {houses[0].sign}</div>
          </div>
        </div>
        <div style={{ gridArea: '2 / 4 / 3 / 5', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[3])} {/* House 4 */}
        </div>
        
        {/* Bottom row (houses 10, 9, 8, 5) */}
        <div style={{ gridArea: '3 / 1 / 4 / 2', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[9])} {/* House 10 */}
        </div>
        <div style={{ gridArea: '3 / 2 / 4 / 3', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[8])} {/* House 9 */}
        </div>
        <div style={{ gridArea: '3 / 3 / 4 / 4', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[7])} {/* House 8 */}
        </div>
        <div style={{ gridArea: '3 / 4 / 4 / 5', border: '1px solid #666', padding: '8px' }}>
          {renderHouse(houses[4])} {/* House 5 */}
        </div>
        
        {/* We're missing houses 6 and 7 in the 4x3 grid layout */}
        {/* Let's add them as overlay boxes on the right middle side */}
        <div style={{ 
          position: 'absolute', 
          right: '-100px', 
          top: '33.3%', 
          width: '90px', 
          height: '33.3%', 
          border: '1px solid #666', 
          padding: '8px',
          backgroundColor: '#f8f8f8'
        }}>
          {renderHouse(houses[5])} {/* House 6 */}
        </div>
        <div style={{ 
          position: 'absolute', 
          right: '-100px', 
          top: '66.6%', 
          width: '90px', 
          height: '33.3%', 
          border: '1px solid #666', 
          padding: '8px',
          backgroundColor: '#f8f8f8'
        }}>
          {renderHouse(houses[6])} {/* House 7 */}
        </div>
      </div>
    </div>
  );
};

// Helper function to render a house with its planets
function renderHouse(house: { number: number, sign: string, sanskritName: string, planets: any[] }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ borderBottom: '1px dashed #999', paddingBottom: '4px', marginBottom: '4px' }}>
        <div className="text-sm font-semibold">{house.number}. {house.sign}</div>
        <div className="text-xs text-gray-600">{house.sanskritName}</div>
      </div>
      <div className="flex flex-wrap gap-1">
        {house.planets.map((planet, idx) => (
          <div 
            key={idx}
            className="text-xs bg-blue-100 px-1 rounded"
            title={`${planet.name} at ${(planet.longitude % 30).toFixed(1)}°`}
          >
            {planetSymbols[planet.name] || planet.name.substring(0, 2)}
            {planet.retrograde ? 'R' : ''}
          </div>
        ))}
      </div>
    </div>
  );
}

export default BirthChart; 