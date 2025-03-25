import React, { useState } from 'react';
import { Planet } from '../../types/astrology';
import { PlanetModel } from './PlanetModel';

interface PlanetaryVisualizationProps {
  planets: Planet[];
}

export const PlanetaryVisualization: React.FC<PlanetaryVisualizationProps> = ({ planets }) => {
  // Handle planet selection
  const [selectedPlanet, setSelectedPlanet] = useState<Planet | null>(null);

  const handlePlanetClick = (planet: Planet) => {
    setSelectedPlanet(planet === selectedPlanet ? null : planet);
  };

  // Render a planet with adjustments for specific planets like Saturn
  const renderPlanet = (planet: Planet) => {
    // Apply specific adjustment for Saturn to correct vertical alignment
    const adjustmentY = planet.name === "Saturn" ? -0.15 : 0; // Adjust the value as needed

    return (
      <PlanetModel
        key={planet.id}
        planet={planet}
        position={[
          planet.position.x,
          planet.position.y + adjustmentY, // Apply vertical adjustment for Saturn
          planet.position.z
        ]}
        rotation={planet.rotation}
        scale={planet.scale}
        onClick={handlePlanetClick}
        isSelected={selectedPlanet?.id === planet.id}
      />
    );
  };

  return (
    <div className="planetary-visualization">
      {planets.map(renderPlanet)}
      {selectedPlanet && (
        <div className="planet-info">
          <h3>{selectedPlanet.name}</h3>
        </div>
      )}
    </div>
  );
};
