import React, { useState, useEffect, useCallback } from 'react';
import QualityProvider from '../../three-scene/core/QualityContext';
import CelestialCanvas from '../../three-scene/CelestialCanvas';
import { CelestialVisualizationProps } from '../common/types';

/**
 * ThreeJsVisualization component
 * Adapter for the Three.js-based celestial visualization
 *
 * @param {CelestialVisualizationProps} props - Component props
 */
const ThreeJsVisualization = (props) => {
  const {
    enableShootingStars = true,
    enableOrbits = true,
    enableNebulaEffects = true,
    mouseInteractive = true,
    quality = 'high',
    particleCount
  } = props;

  // Pass through the Three.js implementation
  return (
    <div className="threejs-visualization">
      <QualityProvider
        initialQuality={quality}
        setParticleCount={particleCount}
      >
        <CelestialCanvas
          enableShootingStars={enableShootingStars}
          enableOrbits={enableOrbits}
          enableNebulaEffects={enableNebulaEffects}
          mouseInteractive={mouseInteractive}
        />
      </QualityProvider>
    </div>
  );
};

export default ThreeJsVisualization;
