import React from 'react';
import { motion } from 'framer-motion';
import { CelestialBody } from '@/components/common/CelestialBody';
import {
  getPlanetImagePath,
  getPlanetFallbackColor,
  getPlanetGlowColor
} from '@/utils/planetImages';

interface PlanetPosition {
  planet: string;
  sign: string;
  degree: string | number;
  house: number;
  id?: string;
  name?: string;
  longitude?: number;
  latitude?: number;
}

interface CelestialChartProps {
  planetPositions: PlanetPosition[];
  birthTime: string;
  birthDate: string;
}

// Convert string intensity to number
const getGlowIntensityValue = (intensity: string): number => {
  switch (intensity) {
    case 'high':
      return 0.8;
    case 'medium':
      return 0.5;
    case 'low':
      return 0.3;
    default:
      return 0.5;
  }
};

const CelestialChart: React.FC<CelestialChartProps> = ({
  planetPositions,
  birthTime,
  birthDate
}) => {
  // Calculate chart center and radius
  const centerX = 150;
  const centerY = 150;
  const radius = 120;

  // For a real implementation, this would calculate actual positions
  // based on astrological calculations. For now, we'll place planets
  // evenly around the chart for visualization purposes
  const calculatePosition = (index: number, total: number) => {
    const angle = (index / total) * 2 * Math.PI;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return { x, y };
  };

  return (
    <div className="relative w-full h-full">
      <svg
        viewBox="0 0 300 300"
        className="w-full h-full"
        style={{
          background: 'radial-gradient(circle, rgba(13,25,42,1) 0%, rgba(8,17,31,1) 100%)'
        }}
      >
        {/* Chart circle */}
        <circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke="rgba(59, 130, 246, 0.3)"
          strokeWidth="1"
        />

        {/* Chart center */}
        <circle
          cx={centerX}
          cy={centerY}
          r={3}
          fill="rgba(59, 130, 246, 0.8)"
        />

        {/* Radial lines for houses */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = (i / 12) * 2 * Math.PI;
          const x2 = centerX + radius * Math.cos(angle);
          const y2 = centerY + radius * Math.sin(angle);

          return (
            <line
              key={`house-line-${i}`}
              x1={centerX}
              y1={centerY}
              x2={x2}
              y2={y2}
              stroke="rgba(59, 130, 246, 0.2)"
              strokeWidth="0.5"
            />
          );
        })}

        {/* House numbers */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = (i / 12) * 2 * Math.PI;
          const radius2 = radius + 15;
          const x = centerX + radius2 * Math.cos(angle);
          const y = centerY + radius2 * Math.sin(angle);

          return (
            <text
              key={`house-number-${i}`}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(255, 255, 255, 0.7)"
              fontSize="8"
              fontFamily="sans-serif"
            >
              {i + 1}
            </text>
          );
        })}

        {/* Zodiac signs on the outer circle */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = (i / 12) * 2 * Math.PI;
          const radius3 = radius - 15;
          const x = centerX + radius3 * Math.cos(angle);
          const y = centerY + radius3 * Math.sin(angle);
          const zodiacSigns = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];

          return (
            <text
              key={`zodiac-sign-${i}`}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(255, 255, 255, 0.9)"
              fontSize="12"
              fontFamily="sans-serif"
            >
              {zodiacSigns[i]}
            </text>
          );
        })}
      </svg>

      {/* Planet symbols */}
      {planetPositions.map((planet, index) => {
        const position = calculatePosition(index, planetPositions.length);

        return (
          <motion.div
            key={planet.planet}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1, duration: 0.5 }}
            className="absolute"
            style={{
              top: `${(position.y / 300) * 100}%`,
              left: `${(position.x / 300) * 100}%`,
              transform: 'translate(-50%, -50%)',
              width: '36px',
              height: '36px',
              zIndex: 10
            }}
          >
            <div className="relative">
              <CelestialBody
                src={getPlanetImagePath(planet.planet)}
                alt={planet.planet}
                className="w-full h-full"
                type={planet.planet.toLowerCase() === 'sun' ? 'sun' :
                     planet.planet.toLowerCase() === 'moon' ? 'moon' : 'planet'}
                rotate={planet.planet.toLowerCase() === 'sun'}
                glow={planet.planet.toLowerCase() === 'moon' || planet.planet.toLowerCase() === 'sun'}
                glowIntensity={getGlowIntensityValue(planet.planet.toLowerCase() === 'sun' ? 'high' : 'medium')}
                glowColor={getPlanetGlowColor(planet.planet)}
                fallbackColor={getPlanetFallbackColor(planet.planet)}
              >
                {planet.planet.charAt(0)}
              </CelestialBody>

              <div
                className="absolute -bottom-5 left-1/2 transform -translate-x-1/2 bg-blue-900/70 rounded-md px-1 text-xs text-white"
                style={{ whiteSpace: 'nowrap' }}
              >
                {planet.planet}
              </div>
            </div>
          </motion.div>
        );
      })}

      {/* Birth info */}
      <div className="absolute bottom-0 left-0 right-0 text-center text-xs text-blue-300 bg-blue-950/50 py-1 rounded">
        <span className="mr-3">Date: {new Date(birthDate).toLocaleDateString()}</span>
        <span>Time: {birthTime}</span>
      </div>
    </div>
  );
};

export default CelestialChart;
