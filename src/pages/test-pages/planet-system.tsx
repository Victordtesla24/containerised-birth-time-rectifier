import React, { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import PlanetSystem from '../../components/three-scene/PlanetSystem';

export default function TestPlanetSystem() {
  // Create state for mouse position and scroll position
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [scrollY, setScrollY] = useState(0);

  // Add event handlers for mouse movement and scroll
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      // Normalize mouse position to range -1 to 1
      const x = (event.clientX / window.innerWidth) * 2 - 1;
      const y = -(event.clientY / window.innerHeight) * 2 + 1;
      setMousePosition({ x, y });
    };

    const handleScroll = () => {
      setScrollY(window.scrollY);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <Canvas camera={{ position: [0, 0, 30], fov: 50 }}>
        <PlanetSystem scrollY={scrollY} mousePosition={mousePosition} />
      </Canvas>
    </div>
  );
}
