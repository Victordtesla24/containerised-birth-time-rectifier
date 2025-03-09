import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CelestialBackground } from '.';
import CosmicDustParticles from '../common/CosmicDustParticles';
import { CelestialVisualizationProps } from '../common/types';

/**
 * CanvasVisualization component
 * Adapter for the Canvas-based celestial visualization
 *
 * @param {CelestialVisualizationProps} props - Component props
 */
const CanvasVisualization: React.FC<CelestialVisualizationProps> = ({
  enableShootingStars = true,
  enableOrbits = true,
  enableNebulaEffects = true,
  mouseInteractive = true,
  quality = 'high',
  particleCount,
  perspectiveDepth = 1000
}) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Handle mouse movement for parallax effect if interactive
  useEffect(() => {
    if (!mouseInteractive) return;

    const handleMouseMove = (e: MouseEvent) => {
      // Convert mouse coordinates to normalized device coordinates (-1 to +1)
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -(e.clientY / window.innerHeight) * 2 + 1;
      setMousePosition({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [mouseInteractive]);

  // Calculate particle count based on quality level
  const calculatedParticleCount = particleCount ||
    quality === 'low' ? 30 :
    quality === 'medium' ? 50 :
    quality === 'high' ? 80 : 100;

  return (
    <div className="canvas-visualization" style={{ position: 'fixed', inset: 0, overflow: 'hidden', zIndex: -10 }}>
      {/* Base background layer */}
      <CelestialBackground />

      {/* Cosmic dust particles */}
      {enableNebulaEffects && (
        <CosmicDustParticles
          count={calculatedParticleCount}
          color="#FFFFFF"
          size="medium"
          speed="medium"
          mouseReactive={mouseInteractive}
        />
      )}

      {/* Shooting stars effect */}
      {enableShootingStars && (
        <motion.div
          className="shooting-stars-container"
          style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
        >
          {/* Shooting stars implementation would go here */}
        </motion.div>
      )}
    </div>
  );
};

export default CanvasVisualization;
