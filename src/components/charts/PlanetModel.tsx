import React from 'react';
import { Planet } from '../../types/astrology';

interface PlanetModelProps {
  planet: Planet;
  position: [number, number, number];
  rotation: { x: number; y: number; z: number };
  scale: number;
  onClick: (planet: Planet) => void;
  isSelected: boolean;
}

export const PlanetModel: React.FC<PlanetModelProps> = ({
  planet,
  position,
  rotation,
  scale,
  onClick,
  isSelected
}: PlanetModelProps) => {
  // This component would normally use Three.js or another 3D library
  // For now, we'll return a simplified div representation
  return (
    <div
      onClick={() => onClick(planet)}
      style={{
        position: 'absolute',
        left: `${position[0] * 100}px`,
        top: `${position[1] * 100}px`,
        zIndex: Math.round(position[2] * 100),
        width: `${scale * 50}px`,
        height: `${scale * 50}px`,
        borderRadius: '50%',
        backgroundColor: planet.color || '#FFF',
        border: isSelected ? '2px solid white' : 'none',
        boxShadow: isSelected ? '0 0 10px white' : 'none',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        cursor: 'pointer',
        transform: `rotate(${rotation.z}rad)`
      }}
    >
      {planet.symbol && (
        <span style={{ fontSize: `${scale * 20}px` }}>
          {planet.symbol}
        </span>
      )}
    </div>
  );
};
