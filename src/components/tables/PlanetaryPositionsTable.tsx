import React from 'react';
import { motion } from 'framer-motion';

interface PlanetPosition {
  planet: string;
  sign: string;
  degree: string;
  house: number;
}

interface PlanetaryPositionsTableProps {
  positions: PlanetPosition[];
}

const PlanetaryPositionsTable: React.FC<PlanetaryPositionsTableProps> = ({ positions }) => {
  // Sort planets in a traditional astrological order
  const sortedPositions = [...positions].sort((a, b) => {
    const planetOrder = [
      'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 
      'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto'
    ];
    
    const indexA = planetOrder.indexOf(a.planet);
    const indexB = planetOrder.indexOf(b.planet);
    
    // If both planets are in the order list, sort by that order
    if (indexA !== -1 && indexB !== -1) {
      return indexA - indexB;
    }
    
    // If only one planet is in the order list, prioritize it
    if (indexA !== -1) return -1;
    if (indexB !== -1) return 1;
    
    // Otherwise sort alphabetically
    return a.planet.localeCompare(b.planet);
  });
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-auto">
        <thead>
          <tr className="bg-blue-950/40 border-b border-blue-800/30">
            <th className="px-3 py-2 text-left text-sm font-medium text-blue-300">Planet</th>
            <th className="px-3 py-2 text-left text-sm font-medium text-blue-300">Sign</th>
            <th className="px-3 py-2 text-left text-sm font-medium text-blue-300">Degree</th>
            <th className="px-3 py-2 text-left text-sm font-medium text-blue-300">House</th>
          </tr>
        </thead>
        <tbody>
          {sortedPositions.map((position, index) => (
            <motion.tr
              key={position.planet}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
              className={`${index % 2 === 0 ? 'bg-blue-950/20' : 'bg-blue-950/30'} border-b border-blue-800/20 hover:bg-blue-900/30 transition-colors`}
            >
              <td className="px-3 py-2 text-white font-medium">{position.planet}</td>
              <td className="px-3 py-2 text-blue-200">
                <span className="flex items-center">
                  <span className="mr-1">{getZodiacSymbol(position.sign)}</span>
                  {position.sign}
                </span>
              </td>
              <td className="px-3 py-2 text-blue-200">{position.degree}</td>
              <td className="px-3 py-2 text-blue-200">{position.house}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Helper function to get zodiac symbol
const getZodiacSymbol = (sign: string): string => {
  const symbols: Record<string, string> = {
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
  
  return symbols[sign] || '';
};

export default PlanetaryPositionsTable; 