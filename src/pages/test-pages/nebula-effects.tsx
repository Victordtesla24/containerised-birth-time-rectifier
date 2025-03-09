import React, { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import Nebula from '../../components/three-scene/nebula/Nebula';
import { OrbitControls } from '@react-three/drei';

export default function NebulaEffects() {
  // Create state for mouse position
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Add mouse move event handler
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      // Normalize mouse position to range -1 to 1
      const x = (event.clientX / window.innerWidth) * 2 - 1;
      const y = -(event.clientY / window.innerHeight) * 2 + 1;
      setMousePosition({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <div style={{ width: '100vw', height: '100vh', background: 'black' }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <Nebula mousePosition={mousePosition} />
        <OrbitControls />
      </Canvas>
    </div>
  );
}
